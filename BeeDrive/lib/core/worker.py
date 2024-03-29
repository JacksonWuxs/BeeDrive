import re
import threading
import socket
import traceback

from .idcard import IDCard
from .utils import clean_coder, base_coder, disconnect
from ..encrypt import AESCoder, MD5Coder, SUPPORT_AES
from ..logger import callback
from ..constant import END_PATTERN_COMPILE, END_PATTERN, TCP_BUFF_SIZE, DISK_BUFF_SIZE



class BaseWorker(threading.Thread):
    def __init__(self, sock, encrypt):
        threading.Thread.__init__(self)
        self.daemon = True
        self.percent = 0.0
        self.socket = sock             # socket instance
        self.info = IDCard.create(encrypt)
        self.use_proxy = False         # we try to connect the target directly
        self.is_conn = False           # whether socket is connected
        self.sender = clean_coder      # pipeline for sending data
        self.reciver = clean_coder     # pipeline for reciving data
        self.history = b"" 

    def __enter__(self):
        callback("NotImplementedError: Please rewrite BaseWorker.__enter__()", "error")
        raise NotImplemented("NotImplementedError: Please rewrite BaseWorker.__enter__()")

    def __exit__(self, exc_type, exc_val, exc_tb):
        disconnect(self.socket)
        self.history = b""
        self.is_conn = False
        self.socket = None
        if exc_type is not None:
            for row in traceback.format_exc().split("\n"):
                callback(row, "ERROR")

    def active(self):
        assert self.socket is not None
        assert self.sender and self.reciver
        assert isinstance(self.info, IDCard)
        self.is_conn = True

    def build_socket(self):
        if not self.socket:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(None)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, True)

    def build_pipeline(self, password=u"", encrypt=True):
        if SUPPORT_AES and encrypt:
            ase, md5 = AESCoder(password), MD5Coder(password)
            encrypt = lambda x: ase.encrypt(md5.encrypt(x))
            decrypt = lambda x: md5.decrypt(ase.decrypt(x))
            assert decrypt(encrypt(b"ABCD1234")) == b"ABCD1234"
        else:
            encrypt = decrypt = clean_coder
            
        if hasattr(self, 'target') and self.use_proxy:
            head = (self.target[0] + ":" + str(self.target[1]) + "$").encode("utf8")
            head += (self.info.code + "$").encode("utf8")
            forward = lambda text: head + text
        else:
            forward = clean_coder
            
        self.sender = lambda text: forward(encrypt(base_coder(text)))
        self.reciver = decrypt

    def send(self, text=''):
        self.socket.sendall(self.sender(text) + END_PATTERN)

    def recv(self):
        msg = []
        while sum(map(len, msg)) < DISK_BUFF_SIZE:
            texts = END_PATTERN_COMPILE.split(self.history + self.socket.recv(TCP_BUFF_SIZE))
            msg.extend(self.reciver(_) for _ in texts[:-1] if _)
            self.history = texts[-1]
            if len(self.history) == 0:
                break
        return b"".join(msg)
