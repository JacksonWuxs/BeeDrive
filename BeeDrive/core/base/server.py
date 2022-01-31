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
        task, user, proto = self.parse_line(socket, 128)
        return task, user, proto, socket
    
    def parse_line(self, sock, max_len):
        line = b""
        sock.settimeout(0.01)
        try:
            for i in range(max_len):
                line += sock.recv(1)
                if line.endswith(b"\r\n"):
                    break

            line = line.strip().decode("utf8").split(" ")
            if len(line) != 3:
                disconnect(sock)
                return None, None, None
            if line[1] not in self.users:
                sock.sendall(b"ERROR: User name is incorrect.")
                return None, None, None
            sock.settimeout(None)
            return line
        except Exception:
            disconnect(sock)
            return None, None, None
            
        
