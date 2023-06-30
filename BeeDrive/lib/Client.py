import os
import time

from .core import BaseManager
from .constant import Done
from .utils import list_files, clean_path
from .uploader import UploadClient
from .downloader import DownloadClient
from .commander import CMDClient


class ClientManager(BaseManager):
    def __init__(self, pipe, name, pool_size):
        BaseManager.__init__(self, pipe, name, pool_size)
        self.launch()

    def launch_task(self, task, **kwrds):
        begin = time.time()
        if task == "download":
            self.download(**kwrds)
        elif task == "upload":
            self.upload(**kwrds)
        self.send(b"Finished task in %.0f seconds" % (time.time() - begin))
        self.send(Done)

    def download(self, user, passwd, cloud, source, root, retry, encrypt, proxy, **kwrds):
        if isinstance(source, str):
            source = [source]
        for i, file in enumerate(source):
            self.wait_until_free(i, len(source))
            client = DownloadClient(user, passwd, cloud, file, root, retry, encrypt, proxy)
            self.pool[client.info.uuid] = client
            self.update_worker_status()
        self.wait_until_empty(i, len(source))

    def upload(self, user, passwd, cloud, source, retry, encrypt, proxy, **kwrds):
        source = clean_path(source)
        root = clean_path(os.path.dirname(source))
        files = list_files(source)
        i = 0
        for i, file in enumerate(files, 1):
            self.wait_until_free(i, len(files))
            fold = clean_path(os.path.dirname(file)).replace(root, "")
            if len(fold) > 0 and ord(fold[0]) == 47:
                fold = fold[1:]
            client = UploadClient(user, passwd, cloud, file, retry, encrypt, fold, proxy)
            self.pool[client.info.uuid] = client
            self.update_worker_status()
        self.wait_until_empty(i, len(files))

    def wait_until_free(self, done, total):
        while self.pool_is_full():
            time.sleep(0.01)
            self.update_worker_status()
            running = self.live_workers
            self.send("  Done: %d/%d | Working: %d" % (done - running, total, running))

    def wait_until_empty(self, done, total):
        if len(self.pool) == 1:
            worker = list(self.pool.values())[0]
            while worker.is_alive():
                time.sleep(0.1)
                self.send(worker.msg)
        else:
            while not self.pool_is_empty():
                time.sleep(0.1)
                self.update_worker_status()
                running = self.live_workers
                self.send("  Done: %d/%d | Working: %d" % (done - running, total, running))
