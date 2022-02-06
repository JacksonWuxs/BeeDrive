import re
import threading
import socket
import traceback

from .idcard import IDCard
from ..encrypt import AESCoder, MD5Coder, SUPPORT_AES
from ..utils import clean_coder, base_coder, disconnect
from ..logger import callback_info, callback_flush
from ..constant import END_PATTERN, TCP_BUFF_SIZE, STAGE_INIT, DISK_BUFF_SIZE


END_PATTERN_COMPILE = re.compile(END_PATTERN)


class BaseWorker(threading.Thread):
    def __init__(self, sock, encrypt):
        threading.Thread.__init__(self)
        self.socket = sock             # socket instance
        self.info = IDCard.create(encrypt)
        self.use_proxy = False         # we try to connect the target directly
        self.isConn = False            # whether socket is connected
        self.sender = clean_coder      # pipeline for sending data
        self.reciver = clean_coder     # pipeline for reciving data
        self.history = b"" 

    def __enter__(self):
        callback_error("NotImplementedError: Please rewrite BaseWorker.__enter__()", 6, self.info)
        raise NotImplemented("NotImplementedError: Please rewrite BaseWorker.__enter__()")

    def __exit__(self, exc_type, exc_val, exc_tb):
        disconnect(self.socket)
        if exc_type is not None:
            print(traceback.format_exc())
        self.history = b""
        self.isConn = False
        self.socket = None

    def active(self):
        assert self.socket is not None
        assert self.sender and self.reciver
        assert isinstance(self.info, IDCard)
        self.isConn = True

    def build_socket(self):
        if not self.socket:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(None)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, True)

    def build_pipeline(self, password=u""):
        if SUPPORT_AES and self.info.encrypt:
            ase, md5 = AESCoder(password), MD5Coder(password)
            encrypt = lambda x: ase.encrypt(md5.encrypt(x))
            decrypt = lambda x: md5.decrypt(ase.decrypt(x))
            assert decrypt(encrypt(b"ABCD1234")) == b"ABCD1234"
        else:
            encrypt = decrypt = clean_coder
            
        if hasattr(self, 'target') and self.use_proxy:
            head = str(self.target).encode("utf8") + b"$" + self.info.code.encode("utf8") + b"$"
            forward = lambda text: head + text
        else:
            forward = clean_coder
            
        self.sender = lambda text: forward(encrypt(base_coder(text)))
        self.reciver = decrypt

    def send(self, text=''):
        self.socket.sendall(self.sender(text) + END_PATTERN)

    def recv(self):
        msg = []
        text = self.history + self.socket.recv(TCP_BUFF_SIZE)
        while text:
            texts = END_PATTERN_COMPILE.split(text)
            msg.extend(self.reciver(_) for _ in texts[:-1] if _)
            if not texts[-1] or sum(map(len, msg)) >= DISK_BUFF_SIZE:
                self.history = texts[-1]
                break
            text = texts[-1] + self.socket.recv(TCP_BUFF_SIZE)
        return b"".join(msg)
