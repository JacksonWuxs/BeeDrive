import os
import time
from json import dumps, loads

from .base import BaseManager
from .constant import Done, NewTask, Stop, STAGE_DONE, STAGE_FAIL
from .utils import list_files, clean_path
from .uploader import UploadClient
from .downloader import DownloadClient



class ClientManager(BaseManager):
    def __init__(self, pipe, name, pool_size):
        BaseManager.__init__(self, pipe, name, pool_size)
        self.launch()

    def launch_task(self, task, **kwrds):
        if task == "download":
            self.download(**kwrds)
        elif task == "upload":
            self.upload(**kwrds)

    def download(self, user, passwd, cloud, source, root, retry, encrypt, proxy, **kwrds):
        if isinstance(source, str):
            source = [source]
        for i, file in enumerate(source):
            self.wait_until_free(i, len(source))
            client = DownloadClient(user, passwd, cloud, file, root, retry, encrypt, proxy)
            self.pool[client.info.uuid] = client
            self.update_worker_status()
        self.wait_until_empty(i, len(source))
        self.send(Done)

    def upload(self, user, passwd, cloud, source, retry, encrypt, proxy, **kwrds):
        source = clean_path(source)
        root = clean_path(os.path.dirname(source))
        files = list_files(source)
        for i, file in enumerate(files, 1):
            self.wait_until_free(i, len(files))
            fold = clean_path(os.path.dirname(file)).replace(root, "")
            if len(fold) > 0 and ord(fold[0]) == 47:
                fold = fold[1:]
            client = UploadClient(user, passwd, cloud, file, retry, encrypt, fold, proxy)
            self.pool[client.info.uuid] = client
            self.update_worker_status()
        self.wait_until_empty(i, len(files))
        self.send(Done)

    def wait_until_free(self, done, total):
        while self.pool_is_full():
            time.sleep(0.01)
            self.update_worker_status()
            running = self.live_workers
            self.send("  Done: %d/%d | Working: %d" % (done - running, total, running))

    def wait_until_empty(self, done, total):
        if len(self.pool) == 1:
            worker = list(self.pool.values())[0]
            while worker.isAlive():
                time.sleep(0.1)
                self.send(worker.msg)
        else:
            while not self.pool_is_empty():
                time.sleep(0.1)
                self.update_worker_status()
                running = self.live_workers
                self.send("  Done: %d/%d | Working: %d" % (done - running, total, running))
