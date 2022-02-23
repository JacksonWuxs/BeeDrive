import pickle
import time
import socket

from .idcard import IDCard
from .worker import BaseWorker
from ..utils import build_connect, disconnect
from ..logger import callback, flush
from ..encrypt import SUPPORT_AES, AESCoder
from ..constant import END_PATTERN, TCP_BUFF_SIZE, VERSION
from ..constant import (STAGE_INIT, STAGE_PRE, STAGE_RUN, RETRY_WAIT,
                        STAGE_DONE, STAGE_FAIL, STAGE_RETRY)


class BaseClient(BaseWorker):
    def __init__(self, user, passwd, target, task, retry, encrypt, proxy):
        self.msg = self.stage = STAGE_INIT
        BaseWorker.__init__(self, None, encrypt)
        self.proxy = [] if proxy is None else proxy
        self.user = user
        self.passwd = passwd
        self.target = target
        self.task = task
        self.max_retry = retry
        self.peer = None
        
    def __enter__(self):
        self.msg = "Connecting to cloud"
        self.build_connect()
        if self.socket:
            self.build_pipeline(self.passwd)
            self.verify_connect()
            if self.peer or self.task == "exit":
                self.active()

    def prepare(self):
        raise NotImplemented()

    def process(self, **kwrds):
        raise NotImplemented()

    def build_connect(self):
        # connect the server
        for ip, port in [self.target] + self.proxy:
            # try to connect target
            conn = build_connect(ip, port)
            if isinstance(conn, str):
                continue

            # whether connect to the proxy or not
            if (ip, port) != self.target:
                source = self.info.code #str(self.socket.getsockname())
                # makesure the proxy node has target ip
                conn.sendall(('Proxy %s:%s %s' % (self.target[0], self.target[1], source)).encode())
                rspn = conn.recv(TCP_BUFF_SIZE)
                if rspn != b"TRUE":
                    continue
                callback('Connect to %s:%d using proxy %s:%d' % (self.target[0], self.target[1],
                                                                     ip, port))
                self.use_proxy = True
            self.socket = conn
            return conn
        
        self.msg = u"cannot find out target %s:%s" % self.target
        callback(self.msg, "error")
        return 

    def verify_connect(self):
        # speak out who am I and what I need
        header = ("%s %s BEE/%s\r\n" % (self.task.lower(), self.user, VERSION)).encode("utf8")
        info = pickle.dumps(self.info.info)
        if SUPPORT_AES:
            info = AESCoder(self.passwd).encrypt(info)
        header += pickle.dumps({"info": info, "text": not SUPPORT_AES})
        if self.use_proxy:
            target = (self.target[0] + ":" + str(self.target[1])).encode("utf8")
            source = self.info.code.encode("utf8")
            header = b"%s$%s$%s%s" % (target, source, header, END_PATTERN)
        self.socket.sendall(header)

        # makesure the request is confirmed
        try:
            rspn = self.socket.recv(1024)
            if rspn.startswith(b"ERROR"):
                callback(rspn.decode(), "error")
                disconnect(self.socket)
                return
            rspn = rspn.replace(END_PATTERN, b"")
            self.peer = pickle.loads(self.reciver(rspn))
            if self.peer['code'] != IDCard(self.peer['uuid'], self.peer['mac'], self.peer['encrypt']).code:
                self.peer = None
        except Exception as e:
            self.peer = None

    def run(self, *args, **kwrds):
        self.stage = STAGE_PRE
        kwrds = self.prepare()
        for retry in range(1, 1 + self.max_retry):
            with self:
                if self.peer and not self.is_conn:
                    try:
                        self.stage = STAGE_RUN
                        result = self.process(**kwrds)
                        flush()
                        if result is True:
                            self.stage = STAGE_DONE
                            return
                    except ConnectionResetError:
                        pass
                    except ConnectionAbortedError:
                        pass
                    except EOFError:
                        pass
                    except TimeoutError:
                        pass
                    except socket.timeout:
                        pass
            self.stage = STAGE_RETRY
            self.msg = "Retry connection in %d seconds" % RETRY_WAIT
            callback(self.msg)
            time.sleep(RETRY_WAIT)
        self.stage = STAGE_FAIL
