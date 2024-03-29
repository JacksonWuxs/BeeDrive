import time

from .core import BaseServer, BaseClient, BaseManager
from .constant import IsFull, NewTask, Stop
from .utils import get_uuid, clean_path
from .uploader import UploadWaiter
from .downloader import DownloadWaiter
from .commander import CMDWaiter
from .browser import HTTPWaiter
from .logger import callback, flush


WAITERS = {"upload": UploadWaiter, "download": DownloadWaiter,
           "commander": CMDWaiter, 
           "get": HTTPWaiter, "post": HTTPWaiter}


class ExistMessager(BaseClient):
    def __init__(self, exit_code, port):
        BaseClient.__init__(self, exit_code, "", ('127.0.0.1', port), 'exit',
                            3, True, None)
        self.start()

    def run(self):
        with self:
            pass

            
class WorkerManager(BaseManager):
    def __init__(self, pipe, name, work_dir, pool_size):
        BaseManager.__init__(self, pipe, name, pool_size)
        self.work_dir = work_dir
        self.launch()

    def launch_task(self, users, proto, token, task, sock, root):
        worker = WAITERS[task](users, proto, token, root, task, sock)
        self.pool[worker.info.uuid] = worker
        self.send(worker.info.uuid)



class LocalServer(BaseServer):
    def __init__(self, database, port, save_path, max_manager, max_worker):
        BaseServer.__init__(self, database, port)
        self.target = ("0.0.0.0", port)
        self.max_manager = max_manager
        self.max_worker = max_worker
        self.managers = set()
        self.workdir = clean_path(save_path)
        self.exit_code = get_uuid()

    def __enter__(self):
        self.build_socket()
        self.build_pipeline()
        self.build_server(self.max_worker * self.max_manager)
        self.active()
        self.add_new_manager()
        
    def add_new_task(self, proto, token, task, sock):
        while True:
            for manager in self.managers:
                if manager.echo(IsFull) is False:
                    manager.echo(NewTask,
                                 users=self.users,
                                 root=self.workdir,
                                 proto=proto,
                                 token=token,
                                 task=task,
                                 sock=sock)
                    return
            self.add_new_manager()
            time.sleep(1.0)

    def add_new_manager(self):
        if len(self.managers) < self.max_manager:
            manager = WorkerManager.get_controller(name=self.name,
                                     work_dir=self.workdir,
                                     pool_size=self.max_worker)
            self.managers.add(manager)

    def run(self):
        with self:
            callback("Server has been launched at %s:%s" % self.target)
            while self.is_conn:
                task, token, protocol, sock = self.accept_connect()
                if task == "exit" and token == self.exit_code:
                    break
                elif task and protocol:
                    self.add_new_task(protocol, token, task, sock)
        callback("Server has been closed successfully")

    def stop(self):
        exits = ExistMessager(self.exit_code, self.port)
        for manager in self.managers:
            manager.join_do(Stop)
        exits.join()

                        
