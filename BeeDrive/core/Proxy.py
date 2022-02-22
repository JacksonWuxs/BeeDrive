import select
from socket import socket, AF_INET, SOCK_STREAM, SOL_SOCKET, SO_REUSEADDR, timeout
from threading import Thread
from time import sleep

from .utils import build_connect, disconnect, read_until, get_uuid
from .logger import callback_info
from .constant import TCP_BUFF_SIZE, END_PATTERN, RETRY_WAIT



class BaseProxyNode(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.daemon = True
        self.node = None
        self.routes = {}
        self.histories = {}
        self.is_conn = False

    def __enter__(self):
        self.build_server()
        self.is_conn = True

    def __exit__(self, *args, **kwrds):
        self.remove_connect(self.node)
        self.node = None
        self.is_conn = False

    @property
    def listen_sock(self):
        return [s for s in self.routes.values() if isinstance(s, socket) and not s._closed]
    
    def read_buff(self, sock):
        history = self.histories.get(sock, b"")
        #while not sock._closed:
        message = sock.recv(TCP_BUFF_SIZE)
        if len(message) == 0:
            raise ConnectionResetError
        texts = (history + message).split(END_PATTERN)
        for element in texts[:-1]:
            yield element + END_PATTERN
        self.histories[sock] = texts[-1]

    def forward(self, sock):
        try:
            self._forward(sock)
        except timeout:
            pass
        except KeyError:
            pass
        except ConnectionResetError:
            self.remove_connect(sock)
        except ConnectionAbortedError:
            self.remove_connect(sock)
        except OSError:
            self.remove_connect(sock)

    def remove_connect(self, sock):
        if sock is not None:
            disconnect(sock)
            if sock in self.histories:
                del self.histories[sock]
            if sock in self.routes:
                addr = self.routes.pop(sock)
                if addr in self.routes:
                    del self.routes[addr]
                callback_info("Remove connection %s" % addr)

    def stop(self):
        self.is_conn = False


class HostProxy(BaseProxyNode):
    def __init__(self, host_port, max_worker):
        BaseProxyNode.__init__(self)
        self.port = host_port
        self.connects = {}

    def build_server(self):
        self.node = socket(AF_INET, SOCK_STREAM)
        self.node.setsockopt(SOL_SOCKET, SO_REUSEADDR, True)
        self.node.bind(('0.0.0.0', self.port))
        self.node.listen()
        self.routes["PROXY"] = self.node

    def run(self):
        with self:
            callback_info("Forwarding Proxy is running at port %d" % self.port)
            while self.is_conn:
                try:
                    for sock in select.select(self.listen_sock, [], [])[0]:
                        if sock == self.node:
                            self.accept()
                            continue
                        Thread(target=self.forward, args=(sock,)).start()
                except OSError:
                    pass

    def accept(self):
        client, addr = self.node.accept()
        request = read_until(client, b"\n").strip()
        if request.startswith(b'Proxy'):
            _, target, nickname = request.split(b" ")
            if target in self.routes:
                client.sendall(b'TRUE')
                self.routes[target].sendall(nickname + b"$" + END_PATTERN)
                self._register(nickname, client, "BEE")
                target = target.decode("utf8").split(":")
                callback_info("Forward BEE %s:%s to %s:%s" % (addr[0], addr[1], target[0], target[1]))
            else:
                client.sendall(b'FALSE')
                
        elif request.startswith(b'Regist'):
            nickname = request.split(b" ", 1)[1]
            if nickname not in self.routes:
                client.sendall(b'TRUE')
                self._register(nickname, client, "BEE")
                nickname, real_port = nickname.decode("utf8").split(":")
                callback_info("Registration %s:%s with Nickname=%s" % (addr[0], real_port, nickname))
            else:
                client.sendall(b"FALSE")

        elif request.split(b" ", 1)[0].lower() in (b"post", b"get"):
            Thread(target=self.handle_http, args=(request, addr, client)).start()
                        
        return client

    def _register(self, nickname, sock, protocol):
        self.routes[nickname] = sock
        self.routes[sock] = nickname
        self.histories[sock] = b""
        self.connects[sock] = protocol

    def _forward(self, sock):
        for data in self.read_buff(sock):
            target, data = data.split(b"$", 1)
            if target.startswith(b"("):
                data = data[:-len(END_PATTERN)]
            self.routes[target].sendall(data)

    def handle_http(self, request, addr, src):
        method, target, protocol = request.split(b" ")
        target = target.split(b"/")[1:]
        if target[0] in self.routes:
            target_file = b"/".join(target[1:])
            nickname = b"(HTTP)" + get_uuid().encode("utf8")
            tgt = self.routes[target[0]]
            callback_info("Forward HTTP %s:%s to %s" % (addr[0], addr[1], target[0].decode("utf8")))
            # Step-1: tell the local proxy to launch a forwarding
            tgt.sendall(nickname + b"$" + END_PATTERN)
            # Step-2: send query line
            tgt.sendall(nickname + b"$" + method + b" /%s/" % target[0] + target_file + b" HTTP-PROXY\n" + END_PATTERN)
            # Step-3: send headers
            pattern = nickname + b"$%s" + END_PATTERN
            while not src._closed:
                head = read_until(client, b"\n")
                tgt.sendall(pattern % head)
                if head == b"\r\n":
                    break
            # Step-4: let proxy ready to forward
            self._register(nickname, client, "HTTP")
            
            src.settimeout(None)
            


class LocalRelay(BaseProxyNode):
    def __init__(self, master, host_port, server_port, nick_name, max_worker):
        BaseProxyNode.__init__(self)
        self.server = ("127.0.0.1", int(server_port))
        self.nickname = (nick_name, int(server_port))
        self.master = master

    def build_server(self):
        route = build_connect(*self.master)
        if not isinstance(route, str):
            try:
                route.sendall(("Regist %s:%s\n" % self.nickname).encode())
                if route.recv(128) == b"TRUE":
                    self.routes[self.master] = route
                    callback_info("Registed at %s:%d with nickname %s:%d" % (route.getpeername()[0],
                                                                           route.getpeername()[1],
                                                                           self.nickname[0],
                                                                           self.nickname[1]))
            except ConnectionResetError:
                pass

    def run(self):
        with self:
            while self.is_conn:
                while len(self.listen_sock) == 0 and self.is_conn:
                    callback_info("Trying to reconnect %s" % (self.master,))
                    disable = [s for s in self.routes if isinstance(s, socket)]
                    for s in disable:
                        self.remove_connect(s)
                    sleep(RETRY_WAIT)
                    self.build_server()
                if not self.is_conn:
                    break
                try:
                    for sock in select.select(self.listen_sock, [], [])[0]:
                        Thread(target=self.forward, args=(sock,)).start()
                except OSError:
                    pass
                    
    def _forward(self, sock):
        peername = sock.getpeername()
        # message from master proxy
        if peername == self.master:
            for data in self.read_buff(sock):
                taskid, data = data.split(b"$", 1)
                if taskid not in self.routes:
                    conn = build_connect(*self.server)
                    if isinstance(conn, str):
                        continue
                    self.routes[taskid] = conn
                    self.routes[conn] = taskid
                else:
                    self.routes[taskid].sendall(data)

        # message from the local server   
        elif peername == self.server:
            route = self.routes[self.master]
            head = self.routes[sock] + b"$"
            for data in self.read_buff(sock):
                route.sendall(head + data)


