import pickle

from .worker import BaseWorker

        
class BaseWaiter(BaseWorker):
    def __init__(self, peer, task, conn, host_name, passwd):
        BaseWorker.__init__(self, host_name, passwd, conn, peer.crypto, peer.sign)
        self.peer = peer
        self.task = task

    def __enter__(self):
        self.build_socket()
        self.build_pipeline()
        self.send(pickle.dumps(self.info.info))
        self.active()

