from select import select
from socket import socket, AF_INET, SOCK_STREAM, SOL_SOCKET, SO_REUSEADDR
from threading import Thread
from time import sleep

from .utils import build_connect
from .logger import callback_info
from .constant import TCP_BUFF_SIZE, END_PATTERN


class BaseProxyNode(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.daemon = True
        self.node = None
        self.routes = {}
        self.alive = False

    def __enter__(self):
        self.build_server()
        self.alive = True

    def __exit__(self, *args, **kwrds):
        self.remove_connect(self.node)
        self.node = None
        self.alive = False

    @property
    def listen_sock(self):
        return list(filter(lambda s: isinstance(s, socket) and not s._closed,
                           self.routes.values()))

    def read_buff(self, sock):      
        try:
            history = b""
            while True:
                try:
                    message = sock.recv(TCP_BUFF_SIZE)
                except OSError:
                    message = b""
                    
                if len(message) == 0:
                    self.remove_connect(sock)
                    break
                
                texts = (history + message).split(END_PATTERN)
                for element in texts[:-1]:
                    if len(element) > 0:
                        yield element + END_PATTERN
                if not texts[-1]:
                    break
                history = texts[-1]
        except ConnectionResetError:
            self.remove_connect(sock)

    def remove_connect(self, sock):
        if sock is not None:
            try:
                sock.shutdown(2)
            except EOFError:
                pass
            sock.close()
            if sock in self.routes:
                addr = self.routes.pop(sock)
                del self.routes[addr]
                callback_info("Connection %s has been removed" % addr.decode())

    def stop(self):
        self.alive = False


class HostProxy(BaseProxyNode):
    def __init__(self, host_port):
        BaseProxyNode.__init__(self)
        self.port = host_port

    def run(self):
        with self:
            callback_info("Public Host Proxy is launched at port %d" % self.port)
            while self.alive:
                for sock in select(self.listen_sock, [], [])[0]:
                    try:
                        self.handle_one_request(sock)
                    except:
                        self.remove_connect(sock)

    def accept(self):
        client, addr = self.node.accept()
        try:
            request = client.recv(128)
            if request.startswith(b'Proxy:'):
                target = request.split(b"$", 1)[0][6:]
                
                if target in self.routes:
                    client.sendall(b'TRUE')
                    nickname = request.split(b"$", 1)[1]
                    self.routes[target].sendall(nickname)
                    nickname = nickname.split(b"$", 1)[0]
                    self.routes[nickname] = client
                    self.routes[client] = nickname
                    target = eval(target)
                    callback_info("Forwarding %s:%d to %s:%d" % (addr[0], addr[1], target[0], target[1]))
                else:
                    client.sendall(b'FALSE')
                    
            elif request.startswith(b'Regist:'):
                nickname = request[7:]
                if nickname not in self.routes:
                    client.sendall(b'TRUE')
                    self.routes[nickname] = client
                    self.routes[client] = nickname
                    nickname, real_port = eval(nickname)
                    callback_info("Registration %s:%d with Nickname=%s" % (addr[0], real_port, nickname))
                else:
                    client.sendall(b"FALSE")
        except ConnectionResetError:
            pass

    def build_server(self):
        self.node = socket(AF_INET, SOCK_STREAM)
        self.node.setsockopt(SOL_SOCKET, SO_REUSEADDR, True)
        self.node.bind(('0.0.0.0', self.port))
        self.node.listen()
        self.routes["PROXY"] = self.node

    def handle_one_request(self, sock):
        if sock == self.node:
            self.accept()
            return

        for data in self.read_buff(sock):
            target, data = data.split(b"$", 1)
            if target not in self.routes:
                break
            self.routes[target].sendall(data)


class LocalRelay(BaseProxyNode):
    def __init__(self, master, host_port, server_port, nick_name):
        BaseProxyNode.__init__(self)
        self.server = ("127.0.0.1", int(server_port))
        self.nickname = (nick_name, int(server_port))
        self.master = master

    def build_server(self):
        route = build_connect(*self.master)
        if not isinstance(route, str):
            route.sendall(("Regist:%s" % (self.nickname,)).encode())
            if route.recv(128) == b"TRUE":
                self.routes[self.master] = route
                callback_info("Registed at Proxy %s:%d with nickname %s:%d" % (route.getpeername()[0],
                                                                               route.getpeername()[1],
                                                                               self.nickname[0],
                                                                               self.nickname[1]))

    def run(self):
        with self:
            while self.alive:
                sockets = self.listen_sock
                while len(sockets) == 0 and self.alive:
                    callback_info("Trying to reconnect %s" % (self.master,))
                    for sock in self.routes:
                        if isinstance(sock, socket):
                            self.remove_connect(sock)
                    sleep(30)
                    self.build_server()
                    sockets = self.listen_sock
                if not self.alive:
                    break
                for sock in select(sockets, [], [])[0]:
                    try:
                        self.handle_one_request(sock)
                    except:
                        self.remove_connect(sock)
                    
    def handle_one_request(self, sock):
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

