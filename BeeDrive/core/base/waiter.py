import pickle
import re
import os
import time

from .worker import BaseWorker
from .idcard import IDCard
from ..utils import disconnect, clean_path
from ..constant import TCP_BUFF_SIZE, END_PATTERN
from ..encrypt import SUPPORT_AES, AESCoder
from ..logger import callback_info


LOGIN = re.compile("/\?user=(.*)&passwd=(.*)")
DOWNLOAD = re.compile("/\?cookie=(.*)&file=(.*)")
UPLOAD = re.compile("/\?cookie=(.*)&upload=(.*)")

        
class BaseWaiter(BaseWorker):
    def __init__(self, infos, proto, token, task, conn, roots):
        BaseWorker.__init__(self, conn, False)
        self.roots = clean_path(roots)
        self.userinfo = infos
        self.proto = proto
        self.token = token
        self.task = task
        self.user = None
        self.passwd = None
        self.peer = None

    def __enter__(self):
        self.authorize_connect()
        if self.user:
            self.build_socket()
            self.verify_connect()
            if self.peer:
                self.active()

    def authorize_connect(self):
        if self.proto.startswith("HTTP"):
            if self.token == "/":
                self.user, self.passwd = "", ""
                self.task, self.peer = "index", "HTTP"
                return
            
            login_token =  LOGIN.findall(self.token)
            if login_token:
                self.user, self.passwd = login_token[0]
                self.task, self.peer = "login", "HTTP"
                return 

            download_token = DOWNLOAD.findall(self.token)
            if download_token:
                self.user, self.passwd = download_token[0]
                self.task, self.peer = "get", "HTTP"

            upload_token = UPLOAD.findall(self.token)
            if upload_token:
                self.user, self.passwd = upload_token[0]
                self.task, self.peer = "post", "HTTP"
        
        elif self.proto.startswith("BEE"):
            if self.token not in self.userinfo:
                sock.sendall(b"ERROR: User name is incorrect.")
                return
            self.user, self.passwd = self.token, self.userinfo[self.token]

    def verify_connect(self):
        """verify connection is a valid BEE-protocol connection"""
        if not self.proto.startswith("BEE"):
            return
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
            return 
        self.info = IDCard(self.info.uuid, self.info.mac, peer["encrypt"])
        self.build_pipeline(self.passwd)
        self.send(pickle.dumps(self.info.info))
        self.peer = card
        return card      


class FileAccessLocker:
    def __init__(self, fpath, mode="rb", buffering=-1, encoding=None):
        self.fpath = fpath
        self.ffold = os.path.dirname(fpath)
        self.flock = "." + os.path.split(fpath)[-1] + ".blck"
        self.flock = clean_path(os.path.join(self.ffold, self.flock))
        self.file = None
        self.mode = mode
        self.encode = encoding
        self.buffer = buffering

    def __enter__(self):
        if not os.path.exists(self.ffold):
            os.makedirs(self.ffold, exist_ok=True)
        while os.path.exists(self.flock):
            time.sleep(0.1)
        open(self.flock, "wb").close()
        self.file = open(self.fpath, self.mode, self.buffer, self.encode)
        return self.file

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.file.close()
        os.remove(self.flock)
        if exc_type:
            raise exc_type(exc_val)

    def reopen(self, mode="rb", buffering=-1, encoding=None):
        assert os.path.exists(self.flock), "please require the lock for the file at first"
        assert self.file is not None
        self.file.close()
        self.mode, self.buffer, self.encode = mode, buffering, encoding
        self.file = open(self.fpath, self.mode, self.buffer, self.encode)
        return self.file
        
