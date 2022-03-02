import pickle
import re
import os
import time
import random

from .worker import BaseWorker
from .idcard import IDCard
from ..utils import disconnect, clean_path, get_uuid, safety_sleep
from ..constant import TCP_BUFF_SIZE, END_PATTERN
from ..encrypt import SUPPORT_AES, AESCoder
from ..logger import callback


LOGIN = re.compile("/\?user=(.*)&passwd=(.*)")
DOWNLOAD = re.compile("/\?cookie=(.*)&root=(.*)&file=(.*)")
UPLOAD = re.compile("/\?cookie=(.*)&root=(.*)&upload=(.*)")
NEWDIR = re.compile("/\?cookie=(.*)&root=(.*)&newdirname=(.*)")

        
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
        if self.task is not None:
            self.build_socket()
            self.verify_connect()
            if self.peer:
                self.active()

    def authorize_connect(self):
        if self.proto.startswith("HTTP"):
            self.redirect = "/"
            if self.proto.endswith("PROXY"):
                tokens = self.token.split("/", 2)
                self.redirect = "/" + tokens[1] + "/"
                self.token = "/" + tokens[2]

            self.user, self.passwd, self.peer, self.task = "", "", "HTTP", None
            if self.token == "/":
                self.task = "index"
            
            login_token =  LOGIN.findall(self.token)
            if login_token:
                self.user, self.passwd = login_token[0]
                self.task = "login"
            
            download_token = DOWNLOAD.findall(self.token)
            if download_token:
                self.cookie, self.pwd, self.target = download_token[0]
                self.task = "get"

            upload_token = UPLOAD.findall(self.token)
            if upload_token:
                self.cookie, self.pwd, self.target = upload_token[0]
                self.task = "post"

            newdir_token = NEWDIR.findall(self.token)
            if newdir_token:
                self.cookie, self.pwd, self.target = newdir_token[0]
                self.task = "newdir"
                
        elif self.proto.startswith("BEE"):
            if self.token not in self.userinfo:
                return self.fail_disconnect(b"User name is incorrect.")
            self.user, self.passwd = self.token, self.userinfo[self.token]
            
        else:
            return self.fail_disconnect(b"Unknow protocol.")

    def verify_connect(self):
        """verify connection is a valid BEE-protocol connection"""
        if not self.proto.startswith("BEE"):
            return self.build_pipeline("", False)

        try:
            # trying to recive information
            head = pickle.loads(self.socket.recv(TCP_BUFF_SIZE))
            assert isinstance(head, dict) and len(head) == 2
            for key in ["info", "text"]:
                assert key in head
        except ConnectionResetError:
            return self.fail_disconnect(b"Unknow protocol.")

        peer = head["info"]
        if not head["text"]:
            if not SUPPORT_AES:
                return self.fail_disconnect(b"Current server doesn't support encryption.")

            try:
                encoder = AESCoder(self.passwd)
                peer = encoder.decrypt(peer)
                peer = pickle.loads(peer)
                for key in ["uuid", "mac", "encrypt"]:
                    assert key in peer
            except Exception:
                return self.fail_disconnect(b"Password is incorrect.")
            
        card = IDCard(peer["uuid"], peer["mac"], peer["encrypt"])
        if card.code != peer["code"]:
            return self.fail_disconnect(b"The message has been tampered with.")
        self.info = IDCard(self.info.uuid, self.info.mac, peer["encrypt"])
        self.build_pipeline(self.passwd, peer["encrypt"])
        self.send(pickle.dumps(self.info.info))
        self.peer = card
        return card

    def fail_disconnect(self, msg):
        if not isinstance(msg, bytes):
            msg = msg.encode("utf8")
        safety_sleep()
        callback("Failed connection: %s" % msg.decode("utf8"))
        self.socket.sendall(b"ERROR: %s%s" % (msg, END_PATTERN))
        time.sleep(3.0)
        disconnect(self.socket)


PROCESS_ID = get_uuid()
class FileAccessLocker:
    def __init__(self, fpath, mode="rb", buffering=-1, encoding=None):
        self.fpath = fpath
        self.ffold = os.path.dirname(fpath)
        self.flock = "." + os.path.split(fpath)[-1] + PROCESS_ID + ".blck"
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
        
