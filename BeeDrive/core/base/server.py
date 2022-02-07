import pickle

from os import path

from .idcard import IDCard
from .worker import BaseWorker
from ..logger import callback_error
from ..constant import END_PATTERN, TCP_BUFF_SIZE
from ..encrypt import AESCoder, SUPPORT_AES
from ..utils import disconnect



class BaseServer(BaseWorker):
    def __init__(self, users, port):
        self.host = "0.0.0.0"
        self.port = port
        self.users = dict(users)
        assert all(map(lambda x: isinstance(x, str), self.users.values())), "Users' password must be str"
        assert len(self.users) == len(users), "Users name are duplicated."
        assert all(map(lambda x: u" " not in x, self.users)), "User name not allowed ' ' blank inside."
        BaseWorker.__init__(self, None, False)
        
    def build_server(self, max_connect):
        self.socket.bind((self.host, self.port))
        self.socket.listen(max_connect)

    def accept_connect(self):
        # accept a new connection and welcome
        socket = self.socket.accept()[0]
        task, user, proto = self.parse_line(socket, 256)
        return task, user, proto, socket
    
    def parse_line(self, sock, max_len):
        try:
            cache = []
            sock.settimeout(0.1)
            for i in range(TCP_BUFF_SIZE):
                word = sock.recv(1)
                if word == b"\n" or word == b"":
                    break
                cache.append(word)
            sock.settimeout(False)
            line = b"".join(cache[:-1])
            assert line.count(b" ") == 2
        except:
            disconnect(sock)
            return None, None, None

        try:
            check = line.strip().decode("utf8").split(" ")
            assert len(check) == 3
            check[0] = check[0].lower()
            assert check[0] in {"download", "upload", "get", "post", "exit"}
            check[2] = check[2].upper()
            assert check[2].startswith("HTTP") or check[2].startswith("BEE")
            return check
        except Exception:
            disconnect(sock)
            return None, None, None
            
        
