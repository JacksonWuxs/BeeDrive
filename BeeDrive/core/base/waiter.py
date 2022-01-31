import pickle

from .worker import BaseWorker
from .idcard import IDCard
from ..utils import disconnect
from ..constant import TCP_BUFF_SIZE, END_PATTERN
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
        self.peer = self.verify_connect()
        if self.peer:
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

        peer = head["info"]
        if not head["text"]:
            if not SUPPORT_AES:
                self.socket.sendall(b"ERROR: Current server doesn't support encryption.")
                return 
            try:
                encoder = AESCoder(self.passwd)
                peer = encoder.decrypt(peer)
                peer = pickle.loads(peer)
                for key in ["uuid", "mac", "encrypt"]:
                    assert key in peer
            except Exception:
                self.socket.sendall(b"ERROR: Password is incorrect.")
                return 
            
        card = IDCard(peer["uuid"], peer["mac"], peer["encrypt"])
        if card.code != peer["code"]:
            disconnect(self.socket)
            return False
        self.info = IDCard(self.info.uuid, self.info.mac, peer["encrypt"])
        self.build_pipeline(self.passwd)
        self.send(pickle.dumps(self.info.info))
        return card      
