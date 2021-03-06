import select
import socket
import threading
import traceback
import time
import os

from .utils import build_connect, disconnect, read_until, get_uuid, clean_path
from .logger import callback
from .constant import TCP_BUFF_SIZE, END_PATTERN, END_PATTERN_COMPILE, RETRY_WAIT



WELCOME = "Welcome to BeeDrive NAT Service!"
CONTENT = "<h3>Choose a server to connect!</h3>"
SOURCE_DIR = os.path.split(os.path.split(__file__)[0])[0]
INDEX_PATH = clean_path(os.path.join(SOURCE_DIR, "source/index.html"))
INDEX_PAGE = open(INDEX_PATH, "r", encoding="utf8").read()


class BaseProxyNode(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.daemon = True
        self.node = None
        self.killed = False
        self.registed = set()
        self.routes = {}
        self.histories = {}
        self.connects = {}

    def __enter__(self):
        self.build_server()

    def __exit__(self, *args, **kwrds):
        self.clear_pool()
        self.node = None
        
    @property
    def listen_sock(self):
        return list(filter(lambda s: isinstance(s, socket.socket) and not s._closed,
                           self.routes.values()))

    def read_buff(self, sock):      
        try:
            message = sock.recv(TCP_BUFF_SIZE)
            if len(message) == 0:
                raise ConnectionResetError
            texts = END_PATTERN_COMPILE.split(self.histories[sock] + message)
            self.histories[sock] = texts[-1]
            for element in texts[:-1]:
                yield element + END_PATTERN
        except ConnectionResetError:
            self.remove_connect(sock)
        except ConnectionAbortedError:
            self.remove_connect(sock)
        except OSError:
            self.remove_connect(sock)

    def clear_pool(self):
        for sock in list(self.routes):
            if isinstance(sock, socket.socket):
                self.remove_connect(sock)
        self.routes.clear()
        self.histories.clear()
        self.connects.clear()
        self.registed.clear()

    def remove_connect(self, sock):
        if sock is not None:
            disconnect(sock)
            if sock in self.routes:
                addr = self.routes.pop(sock)
                if addr in self.registed:
                    self.registed.remove(addr)
                del self.routes[addr]
                del self.histories[sock]
                del self.connects[sock]
                callback("Remove connection %s" % addr.decode())

    def process(self):
        try:
            while self.node and not self.node._closed:
                for sock in select.select(self.listen_sock, [], [])[0]:
                    try:
                        self.handle_request(sock)
                    except ConnectionResetError:
                        self.remove_connect(sock)
                    except Exception as e:
                        callback("Uncounter Error: %s" % e, "error")
                        for row in traceback.format_exc().split("\n"):
                            callback(row, "error")  
                        if sock != self.node:
                            self.remove_connect(sock)
        except:
            callback("Proxy will relaunch in short!", "error")
            for row in traceback.format_exc().split("\n"):
                callback(row, "error")            

    def stop(self):
        self.killed = True
        if self.node:
            disconnect(self.node)

    def _register(self, nickname, client, protocol):
        self.routes[nickname] = client
        self.routes[client] = nickname
        self.connects[client] = protocol
        self.histories[client] = b""


class HostProxy(BaseProxyNode):
    def __init__(self, host_port, _):
        BaseProxyNode.__init__(self)
        self.port = host_port

    def run(self):
        while True:
            with self:
                callback("NAT server is working at 0.0.0.0:%d" % self.port)
                self.process()

    def accept(self):
        client, addr = self.node.accept()
        request = read_until(client).strip()
        if request.startswith(b'Proxy'):
            _, target, nickname = request.split(b" ")
            if target in self.routes:
                client.sendall(b'TRUE')
                self.routes[target].sendall(nickname + b"$" + END_PATTERN)
                self._register(nickname, client, 0)
                target = target.decode("utf8").split(":")
                callback("Forward BEE %s:%s to %s:%s" % (addr[0], addr[1], target[0], target[1]))
            else:
                client.sendall(b'FALSE')
                
        elif request.startswith(b'Regist'):
            nickname = request.split(b" ", 1)[1]
            if nickname in self.routes:
                if self.routes[nickname].getsockname() == addr:
                    self.remove_connect(self.routes[nickname])
            if nickname not in self.routes:
                client.sendall(b'TRUE')
                self._register(nickname, client, 0)
                self.registed.add(nickname)
                nickname, real_port = nickname.decode("utf8").split(":")
                callback("Registration %s:%s with Nickname=%s" % (addr[0], real_port, nickname))
            else:
                client.sendall(b"FALSE")

        elif request.lower().startswith(b"get") or \
             request.lower().startswith(b"post"):
            self.handle_http(request, addr, client)

    def build_server(self):
        self.node = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.node.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
        self.node.bind(('0.0.0.0', self.port))
        self.node.listen()
        self.routes["PROXY"] = self.node

    def handle_request(self, sock):
        if sock == self.node:
            return self.accept()

        try:
            if self.connects[sock] == 0:
                for data in self.read_buff(sock):
                    target, data = data.split(b"$", 1)
                    if target.startswith(b"(HTTP)"):
                        data = data[:-len(END_PATTERN)]
                    self.routes[target].sendall(data)
            else:
                # only handle post request
                tgt, pattern = self.connects[sock]
                info = sock.recv(TCP_BUFF_SIZE)
                if len(info) == 0:
                    self.remove_connect(sock)
                else:
                    self.routes[tgt].sendall(pattern % info)
        except KeyError:
            # by some accident, the target was disappeared
            if self.routes[sock] not in self.registed:
                self.remove_connect(sock)

    def handle_http(self, request, addr, src):
        if request.count(b" ") != 2:
            return
        method, target, protocol = request.split(b" ")
        target = target.split(b"/")[1:]
        if target[0] == b"":
            threading.Thread(target=self.render_index, args=(src,)).start()
            
        if target[0] in self.routes:
            target_file = b"/".join(target[1:])
            nickname = b"(HTTP)" + get_uuid().encode("utf8")
            tgt = self.routes[target[0]]
            callback("Forward HTTP %s:%s to %s" % (addr[0], addr[1], target[0].decode("utf8")))
            # Step-1: tell the local proxy to launch a forwarding
            tgt.sendall(nickname + b"$" + END_PATTERN)
            # Step-2: send query line
            tgt.sendall(nickname + b"$" + method + b" /%s/" % target[0] + target_file + b" HTTP-PROXY\n" + END_PATTERN)
            # Step-3: preparing pattern
            pattern = nickname + b"$%s" + END_PATTERN
            # Step-4: let proxy ready to forward
            if method.lower() == b"get":
                self._register(nickname, src, 0)
            if method.lower() == b"post":
                self._register(nickname, src, (target[0], pattern))


    def render_index(self, src):
        content = '<html><head><meta http-equiv="Content-Type" content="text/html; charset=UTF8"><title>BeeDrive NAT Service</title></head><body><h2>Welcome to BeeDrive NAT Service!</h2><hr><h3>Choose a registed server:<h3><ul>'
        for item in self.registed:
            item = item.decode("utf8")
            content += '<li><a href="/%s">%s</a>' % (item, item.split(":")[0])
        content += "</ul><hr></body></html>\r\n\r\n"
        src.sendall(b"HTTP/1.1 200 OK\r\nConnection: Close\r\n\r\n")
        src.sendall(content.encode("utf8"))
        time.sleep(1.0)
        src.close()
        

class LocalRelay(BaseProxyNode):
    def __init__(self, master, host_port, server_port, nick_name, _):
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
                    self.node = route
                    self.routes[self.master] = route
                    self.histories[route] = b""
                    callback("Registed at %s:%d with nickname %s:%d" % (route.getpeername()[0],
                                                                        route.getpeername()[1],
                                                                        self.nickname[0],
                                                                        self.nickname[1]))
            except Exception as e:
                pass

    def run(self):
        while not self.killed:
            with self:
                self.process()
                callback("Retry to reconnect %s in %.0f seconds" % (self.master, RETRY_WAIT))
                time.sleep(RETRY_WAIT)
                
    def handle_request(self, sock):
        # message from master proxy
        if sock == self.node:
            for data in self.read_buff(sock):
                taskid, data = data.split(b"$", 1)
                try:
                    self.routes[taskid].sendall(data)
                except KeyError:
                    conn = build_connect(*self.server)
                    if isinstance(conn, str):
                        continue
                    self._register(taskid, conn, 0)

        # message from the local server   
        else:
            route = self.routes[self.master]
            head = self.routes[sock] + b"$"
            for data in self.read_buff(sock):
                route.sendall(head)
                route.sendall(data)




