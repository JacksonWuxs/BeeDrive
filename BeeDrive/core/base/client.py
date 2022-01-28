import pickle
import time

from .idcard import IDCard
from .worker import BaseWorker
from ..utils import build_connect
from ..logger import callback_info
from ..encrypt import HAS_AES
from ..constant import END_PATTERN, TCP_BUFF_SIZE
from ..constant import (STAGE_INIT, STAGE_PRE, STAGE_RUN,
                        STAGE_DONE, STAGE_FAIL, STAGE_RETRY)


class BaseClient(BaseWorker):
    def __init__(self, name, psd, target, task, retry, crypto, signature, proxy):
        self.msg = self.stage = STAGE_INIT
        BaseWorker.__init__(self, name, psd, None, crypto, signature)
        self.proxy = [] if proxy is None else proxy
        self.target = target
        self.task = task
        self.max_retry = retry
        self.peer = None
        
 
    def __enter__(self):
        self.msg = "Connecting to cloud"
        self.build_connect()
        self.build_pipeline()
        self.verify_connect()
        if self.peer:
            self.active()

    def prepare(self):
        raise NotImplemented()

    def process(self, **kwrds):
        raise NotImplemented()

    def build_connect(self):
        # connect the server
        for ip, port in [self.target] + self.proxy:
            # try to connect target
            self.socket = build_connect(ip, port)
            if isinstance(self.socket, str):
                continue
            
            # whether connect to the proxy or not
            if (ip, port) != self.target:
                source = self.info.code #str(self.socket.getsockname())
                # makesure the proxy node has target ip
                self.socket.sendall(('Proxy:%s$%s$' % (str(self.target), source)).encode() + END_PATTERN)
                rspn = self.socket.recv(TCP_BUFF_SIZE)
                if rspn != b"TRUE":
                    continue
                callback_info('- using proxy %s:%s to connect target %s:%d' % (ip, port, self.target[0], self.target[1]))
                self.use_proxy = True
            return
        
        self.msg = u"Error: Cannot connect to %s" % (self.target,)
        self.stage = STAGE_FAIL
        raise TimeoutError('cannot find out the target "%s"' % (self.target,))

    def verify_connect(self):
        if self.stage == STAGE_FAIL:
            return STAGE_FAIL
        
        welcome = self.socket.recv(1024).replace(END_PATTERN, b"")
        if not (welcome.startswith(b"Welcome to use BeeDrive-") and \
                welcome.endswith(b', please login !')):
            self.msg = u"Cannot connect to %s" % (self.target,)
            self.stage = STAGE_FAIL
            return STAGE_FAIL
            
        # speak out who am I and what I need
        header = pickle.dumps(self.info.info)
        header = {"user": self.info.name,
                  "task": self.task,
                  "info": self.aescoder.encrypt(header) if HAS_AES else header,
                  "text": not HAS_AES}

        header = pickle.dumps(header)
        if self.use_proxy:
            target = str(self.target).encode("utf8")
            source = self.info.code.encode("utf8")
            header = b"%s$%s$%s%s" % (target, source, header, END_PATTERN)
        self.socket.sendall(header)
        
        # makesure the request is confirmed
        try:
            rspn = self.recv()
            if rspn.startswith(b"Error"):
                raise Exception(rspn.decode().split(" ", 1)[1])

            self.peer = pickle.loads(rspn)
            if self.peer['code'] != IDCard(self.peer['uuid'], self.peer['name'],
                                      self.peer['mac'], self.peer['crypto'],
                                      self.peer['sign']).code:
                self.peer = None           
        except Exception as e:
            self.peer = None

    def run(self, *args, **kwrds):
        self.stage = STAGE_PRE
        kwrds = self.prepare()
        for retry in range(1, 1 + self.max_retry):
            with self:
                try:
                    self.stage = STAGE_RUN
                    self.process(**kwrds)
                    self.stage = STAGE_DONE
                    return
                except ConnectionResetError:
                    pass
                except ConnectionAbortedError:
                    pass
            if retry <= self.max_retry:
                wait = 5 ** retry 
                self.stage = STAGE_RETRY
                self.msg = "Retry connection in %d seconds" % wait
                callback_info("Retry connection in %d seconds" % wait)
                time.sleep(wait)
        self.stage = STAGE_FAIL
