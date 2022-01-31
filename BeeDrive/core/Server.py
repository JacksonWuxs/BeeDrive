from os import path, makedirs
from time import sleep, time
from json import loads, dumps
from multiprocessing import cpu_count

from .base import BaseServer, BaseClient, BaseManager
from .constant import IsFull, NewTask, KillTask, Update, Stop, ALIVE
from .utils import build_connect
from .uploader import UploadWaiter
from .downloader import DownloadWaiter
from .logger import callback_info, callback_flush


WAITERS = {"upload": UploadWaiter, "download": DownloadWaiter}


class ExistMessager(BaseClient):
    def __init__(self, port):
        BaseClient.__init__(self, 'xuansheng', u"", ('127.0.0.1', port), 'exist',
                            3, False, [])
        self.start()

    def run(self):
        with self:
            pass

            
class WorkerManager(BaseManager):
    def __init__(self, pipe, name, work_dir, pool_size):
        BaseManager.__init__(self, pipe, name, pool_size)
        self.work_dir = work_dir
        self.launch()

    def launch_task(self, user, passwd, task, sock, root):
        worker = WAITERS[task](user, passwd, root, task, sock, False)
        self.pool[worker.info.uuid] = worker
        self.send(worker.info.uuid)



class LocalServer(BaseServer):
    def __init__(self, users, port, save_path, max_manager, max_worker):
        BaseServer.__init__(self, users, port)
        self.target = ("0.0.0.0", port)
        self.max_manager = max_manager
        self.max_worker = max_worker
        self.managers = set()
        self.workdir = path.abspath(save_path)

    def __enter__(self):
        self.build_socket()
        self.build_pipeline()
        self.build_server(self.max_worker * self.max_manager)
        self.active()
        callback_info("Server has been launched at %s" % (self.target,))
        self.add_new_manager()

    def add_new_task(self, user, passwd, task, sock, root):
        while True:
            for manager in self.managers:
                if manager.echo(IsFull) is False:
                    uuid = manager.echo(NewTask,
                                        user=user,
                                        passwd=passwd,
                                        task=task,
                                        sock=sock,
                                        root=root)
                    return
                
            self.add_new_manager()
            if len(self.managers) == self.max_manager:
                sleep(1)

    def add_new_manager(self):
        if len(self.managers) < self.max_manager:
            manager = WorkerManager.get_controller(name=self.name,
                                         work_dir=self.workdir,
                                         pool_size=self.max_worker)
            self.managers.add(manager)

    def run(self):
        with self:
            while self.isConn:
                task, user, protocol, sock = self.accept_connect()
                if task == "exist":
                    break
                elif task is not None:
                    self.add_new_task(user, self.users[user], task, sock, self.workdir)

    def stop(self):
        exits = ExistMessager(self.port)
        for manager in self.managers:
            manager.join_do(Stop)
        exits.join()
        callback_info("Server has been closed successfully")

    def update_schedule_status(self):
        for manager in self.managers:
            for uuid, state, stage, percent, msg in manager.echo(Update):
                pass

                        
