import re
import threading
import socket

from .idcard import IDCard
from ..encrypt import AESCoder, MD5Coder, HAS_AES
from ..utils import clean_coder, base_coder, disconnect
from ..logger import callback_error, callback_flush
from ..constant import END_PATTERN, TCP_BUFF_SIZE, STAGE_INIT, DISK_BUFF_SIZE


END_PATTERN_COMPILE = re.compile(END_PATTERN)


class BaseWorker(threading.Thread):
    def __init__(self, name, passwd, sock=None, crypto=False, sign=False):
        threading.Thread.__init__(self)
        self.socket = sock             # socket instance
        self.info = IDCard.create(name, crypto, sign)
        self.aescoder = AESCoder(passwd) if HAS_AES else None
        self.md5coder = MD5Coder(passwd) if sign else None
        self.use_proxy = False         # we try to connect the target directly
        self.alive = False             # whether ready for serving
        self.sender = None             # pipeline for sending data
        self.reciver = None            # pipeline for reciving data
        self.history = b"" 
        self.stage = STAGE_INIT
        self.msg = STAGE_INIT
        self._work = threading.Event() # kill the task
        self._work.set()

    def __enter__(self):
        callback_error("NotImplementedError: Please rewrite BaseWorker.__enter__()", 6, self.info)
        raise NotImplemented("NotImplementedError: Please rewrite BaseWorker.__enter__()")

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.handle_error(exc_type, exc_val)
        self.alive = False
        self.disconnect()
        callback_flush()

    def active(self):
        assert self.socket is not None
        assert self.sender and self.reciver
        assert isinstance(self.info, IDCard)
        self.alive = True

    def build_socket(self):
        if not self.socket:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, True)

    def build_pipeline(self):
        ase_encoder = self.aescoder.encrypt if self.aescoder else clean_coder
        ase_decoder = self.aescoder.decrypt if self.aescoder else clean_coder
        md5_encoder = self.md5coder.encrypt if self.md5coder else clean_coder
        md5_decoder = self.md5coder.decrypt if self.md5coder else clean_coder
        if hasattr(self, 'target') and self.use_proxy:
            target = str(self.target).encode("utf8")
            source = self.info.code.encode("utf8")
            proxy_encoder = lambda text: b"$".join([target, source, text])
        else:
            proxy_encoder = clean_coder
            
        self.sender = lambda text: proxy_encoder(ase_encoder(md5_encoder(base_coder(text))))
        self.reciver = lambda text: md5_decoder(ase_decoder(text))
        
    def disconnect(self):
        disconnect(self.socket)
        self.socket = None
        self.alive = False

    def handle_error(self, exc_type, exc_val):
        if exc_type is not None:
            callback_flush()
        if exc_type == KeyboardInterrupt:
            callback_error('Connection Is Stopped by Commander-%s' % exc_val, 5, self.info)
        if exc_type == ConnectionRefusedError:
            callback_error('Connection Is Refused by Host-%s' % exc_val, 1, self.info)
        if exc_type == AssertionError:
            callback_error('Message Has Been Modified-%s' % exc_val, 3, self.info)
        if exc_type == IOError:
            callback_error('Operating File Is Failed-%s' % exc_val, 4, self.info)
        if exc_type == Exception:
            callback_error('Unknow Failed Reason: %s' % exc_val, 0, self.info)

    def settimeout(self, timeout):
        if not isinstance(self.socket, str):
            self.socket.settimeout(timeout)

    def send(self, text=''):
        self.socket.sendall(self.sender(text) + END_PATTERN)

    def recv(self):
        msg = []
        try:
            text = self.history + self.socket.recv(TCP_BUFF_SIZE)
            while text:
                texts = END_PATTERN_COMPILE.split(text)
                msg.extend(self.reciver(_) for _ in texts[:-1] if _)
                if not texts[-1] or sum(map(len, msg)) >= DISK_BUFF_SIZE:
                    self.history = texts[-1]
                    break
                text = texts[-1] + self.socket.recv(TCP_BUFF_SIZE)
        finally:
            return b''.join(msg)

