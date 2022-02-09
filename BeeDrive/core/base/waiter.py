import pickle
import re

from .worker import BaseWorker
from .idcard import IDCard
from ..utils import disconnect
from ..constant import TCP_BUFF_SIZE, END_PATTERN
from ..encrypt import SUPPORT_AES, AESCoder
from ..logger import callback_info


LOGIN = re.compile("/\?user=(.*)&passwd=(.*)")
DOWNLOAD = re.compile("/?cookie=(.*)&file=(.*)")
UPLOAD = re.compile("/?cookie=(.*)&upload=(.*)")
        
class BaseWaiter(BaseWorker):
    def __init__(self, infos, proto, token, task, conn):
        BaseWorker.__init__(self, conn, False)
        self.userinfo = infos
        self.proto = proto
        self.token = token
        self.task = task
        self.user = None
        self.passwd = None
        self.peer = None

    def __enter__(self):
        self.authorize_connect()
        if self.user is not None:
            self.build_socket()
            if self.proto.startswith("BEE"):
                self.peer = self.verify_connect()
            if self.peer or self.proto.startswith("HTTP"):
                self.active()

    def authorize_connect(self):
        if self.proto.startswith("HTTP"):
            if self.token == "/":
                self.user, self.passwd, self.task = "", "", "index"
                return
            
            login_token =  LOGIN.findall(self.token)
            if login_token:
                self.user, self.passwd = login_token[0]
                self.task = "login"
                return 

            download_token = DOWNLOAD.findall(self.token)
            if download_token:
                self.user, self.passwd = download_token[0]
                self.task = "get"

            upload_token = UPLOAD.findall(self.token)
            if upload_token:
                self.user, self.passwd = upload_token[0]
                self.task = "post"
        
        elif self.proto.startswith("BEE"):
            if self.token not in self.userinfo:
                sock.sendall(b"ERROR: User name is incorrect.")
                return
            self.user, self.passwd = self.token, self.userinfo[self.token]

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
