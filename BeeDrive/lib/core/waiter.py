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
DOWNLOAD = re.compile('/\?cookie=(.*)&root=(.*)&file=b%27(.*)%27')
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
        if self.proto.startswith("HTTP"):
            self.connect_http()
        elif self.proto.startswith("BEE"):
            self.connect_bee()
        else:
            self.fail_disconnect(b"Unknow protocol: %s" % self.proto)
        if self.peer:
            self.active()

    def connect_http(self):
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
        return self.build_pipeline("", False)

    def connect_bee(self):
        """verify connection is a valid BEE-protocol connection"""
        if self.token not in self.userinfo:
            return self.fail_disconnect(b"User name is incorrect.")
        self.user, self.passwd = self.token, self.userinfo[self.token]
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
        self.build_socket()
        return card

    def fail_disconnect(self, msg):
        if not isinstance(msg, bytes):
            msg = msg.encode("utf8")
        safety_sleep()
        callback("Failed connection: %s" % msg.decode("utf8"))
        self.socket.sendall(b"ERROR: %s%s" % (msg, END_PATTERN))
        time.sleep(3.0)
        disconnect(self.socket)

