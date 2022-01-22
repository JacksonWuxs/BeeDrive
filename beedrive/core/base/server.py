from json import loads, JSONDecodeError
from os import path
from time import sleep

from .idcard import IDCard
from .worker import BaseWorker
from ..logger import callback_error
from ..constant import END_PATTERN, TCP_BUFF_SIZE, __version__
from ..crypto import AESCoder
from ..utils import disconnect


class BaseServer(BaseWorker):
    def __init__(self, users, port, crypto, sign):
        self.host = "0.0.0.0"
        self.port = port
        self.users = dict(users)
        assert all(map(lambda x: isinstance(x, str), self.users.values())), "Users' password must be str"
        assert len(self.users) == len(users), "Users name are duplicated"
        BaseWorker.__init__(self, users[0][0], users[0][1], None, crypto, sign)
        
    def build_server(self, max_connect):
        self.socket.bind((self.host, self.port))
        self.socket.listen(max_connect)

    def accept_connect(self):
        # accept a new connection and welcome
        socket, addr = self.socket.accept()
        socket.sendall(b"Welcome to use BeeDrive-%s, please login !%s" % (__version__.encode(), END_PATTERN))

        # verify user authorization
        header = self.verify_authorize_header(socket)
        if not header:
            sleep(1)
            disconnect(socket)
            return None, None, None, None
        
        # identify ID information of the client
        info = IDCard(header['uuid'], header['name'],
                      header['mac'], header['crypto'],
                      header['sign'])

        # ID information has been modified
        if info.code != header['code']:
            callback_error('You are under attacked', 6)
            disconnect(socket)
            return None, None, None, None
        return socket, self.users[header['name']], info, header['task']

    def verify_authorize_header(self, socket):
        try:
            socket.settimeout(10)
            head = socket.recv(TCP_BUFF_SIZE)
            socket.settimeout(None)
            if head.endswith(END_PATTERN):
                head = head[:-len(END_PATTERN)]
        except ConnectionResetError:
            return

        try:
            head = eval(head.decode())
            assert isinstance(head ,dict)
            for key in ["user", "task", "info"]:
                assert key in head
        except Exception:
            return
        if head["user"] not in self.users:
            socket.sendall(("Error: `%s` is not a legal user name" % head["user"]).encode() + END_PATTERN)
            return
        try:
            head.update(eval(AESCoder(self.users[head["user"]]).decrypt(head["info"])))
            assert isinstance(head, dict)
            for key in ["uuid", "name", "mac", "crypto", "sign"]:
                assert key in head
        except Exception as e:
            socket.sendall(b"Error: Password is incorrect!" + END_PATTERN)
            return
        return head

        
