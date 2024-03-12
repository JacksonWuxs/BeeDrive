import os
import sqlite3

from .worker import BaseWorker
from .utils import disconnect, read_until
from .database import UserDatabase


class BaseServer(BaseWorker):
    def __init__(self, database, port):
        assert isinstance(database, UserDatabase)
        self.host = "0.0.0.0"
        self.port = port
        self.users = database
        BaseWorker.__init__(self, None, False)
        
    def build_server(self, max_connect):
        self.socket.bind((self.host, self.port))
        self.socket.listen(max_connect)

    def accept_connect(self):
        # accept a new connection and welcome
        socket = self.socket.accept()[0]
        task, user, proto = self.parse_line(socket)
        return task, user, proto, socket
    
    def parse_line(self, sock):
        try:
            line = read_until(sock)
            check = line.strip().decode("utf8").split(" ")
            assert len(check) == 3
            check[0] = check[0].lower()
            assert check[0] in {"download", "upload", "commander", "get", "post", "exit"}
            check[2] = check[2].upper()
            assert check[2].startswith("HTTP") or check[2].startswith("BEE")
            return check
        except Exception:
            disconnect(sock)
            return None, None, None
            
        
