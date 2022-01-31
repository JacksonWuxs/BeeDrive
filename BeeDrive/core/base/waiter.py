import pickle

from .worker import BaseWorker
from .idcard import IDCard
from ..utils import disconnect
from ..constant import TCP_BUFF_SIZE
from ..encrypt import SUPPORT_AES, AESCoder

        
class BaseWaiter(BaseWorker):
    def __init__(self, user, passwd, task, conn, encrypt):
        BaseWorker.__init__(self, conn, encrypt)
        self.user = user
        self.passwd = passwd
        self.task = task
        self.peer = None

    def __enter__(self):
        self.build_socket()
        if self.verify_connect():
            self.active()

    def verify_connect(self):
        try:
            # trying to recive information
            head = pickle.loads(self.socket.recv(TCP_BUFF_SIZE))
            assert isinstance(head, dict) and len(head) == 2
            for key in ["info", "text"]:
                assert key in head
        except ConnectionResetError:
            disconnect(self.socket)
            return False

        self.peer = head["info"]
        if not head["text"]:
            if not SUPPORT_AES:
                self.socket.sendall(b"ERROR: Current server doesn't support encryption.")
                self.socket.close()
                return False
            try:
                encoder = AESCoder(self.passwd)
                self.peer = encoder.decrypt(self.peer)
                self.peer = pickle.loads(self.peer)
                for key in ["uuid", "mac", "encrypt"]:
                    assert key in self.peer
            except Exception:
                self.socket.sendall(b"ERROR: Password is incorrect.")
                self.socket.close()
                return False

        card = IDCard(self.peer["uuid"], self.peer["mac"], self.peer["encrypt"])
        if card.code != self.peer["code"]:
            disconnect(self.socket)
            return False
        self.info = IDCard(self.info.uuid, self.info.mac, self.peer["encrypt"])
        self.build_pipeline(self.passwd)
        self.send(pickle.dumps(self.info.info))
        self.peer = card
        return self.peer
                
                
            

        
