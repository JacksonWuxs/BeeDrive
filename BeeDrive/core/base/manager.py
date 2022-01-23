import os
import sys
import multiprocessing


from ..constant import DEATH, IsFull, NewTask, KillTask, Update, Stop, Done, STAGE_DONE


# following code is used to support multiprocessing on Windows .exe format
if sys.platform.startswith("win"):
    try:
        import multiprocessing.popen_spawn_win32 as forking
    except ImportError:
        import multiprocessing.forking as forking
    class _Popen(forking.Popen):
        def __init__(self, *args, **kwrds):
            if hasattr(sys, "frozen"):
                os.putenv("_MEIPASS2", sys._MEIPASS)
            try:
                super(_Popen, self).__init__(*args, **kwrds)
            finally:
                if hasattr(sys, "frozen"):
                    if hasattr(os, "unsetenv"):
                        os.unsetenv("_MEIPASS2")
                    else:
                        os.putenv("_MEIPASS2", "")
    forking.Popen = _Popen



class BaseManager(multiprocessing.Process):

    def __init__(self, pipe, name, pool_size):
        multiprocessing.Process.__init__(self, daemon=True)
        self.name = name
        self.pipe = pipe
        self.pool_size = pool_size
        self.pool = {}
        self.live_workers = 0
        self.alive = False

    @classmethod
    def get_controller(cls, *args, **kwrds):
        pipe_left, pipe_right = multiprocessing.Pipe()
        manager = cls(pipe=pipe_right, *args, **kwrds)
        return ManagerController(pipe_left)

    def kill_task(self):
        uuid = self.recv()
        self.pool[uuid].stop()
        self.send(True)

    def launch(self):
        self.alive = True
        self.start()

    def pool_is_full(self):
        return len(self.pool) == self.pool_size

    def pool_is_empty(self):
        return len(self.pool) == 0
        
    def recv(self):
        try:
            return self.pipe.recv()
        except EOFError:
            return None

    def run(self):
        while self.alive:
            parameters = self.recv()
            if not isinstance(parameters, dict):
                continue
            cmd = parameters.pop("cmd")
            self.update_worker_status()
            if cmd == IsFull:
                self.send(self.pool_is_full())
                
            if cmd == Update:
                self.send(self.update_worker_status())

            if cmd == NewTask:
                self.launch_task(**parameters)

            if cmd == KillTask:
                self.kill_task()

            if cmd == Stop:
                 self.stop()
                 
    def send(self, info):
        try:
            return self.pipe.send(info)
        except BrokenPipeError:
            pass

    def stop(self):
        self.alive = False
        for worker in self.pool.values():
            if worker.alive:
                try:
                    worker.stop()
                except Exception:
                    pass
        self.send(Done)

    def update_worker_status(self):
        subject_status = []
        for uuid, subject in self.pool.items():
            state = 1 if subject.is_alive() else 0            
            subject_status.append((uuid, state, subject.stage, subject.percent, subject.msg))
        for uuid, status, _, _, _ in subject_status:
            if status == DEATH:
                del self.pool[uuid]
        self.live_workers = len(self.pool)
        return subject_status

    def launch_task(self, **kwrds):
        raise NotImplemented("please rewrite this function later")


class ManagerController:
    def __init__(self, pipe):
        self.pipe = pipe

    def echo(self, cmd, **parameters):
        self.relay_do(cmd, **parameters)
        return self.read()

    def join_do(self, cmd, **parameters):
        self.relay_do(cmd, **parameters)
        while True:
            if self.read() == Done:
                break
        
    def relay_do(self, cmd, **parameters):
        assert isinstance(cmd, int) and 0 <= cmd <= 5
        self.pipe.send({"cmd": cmd, **parameters})

    def read(self):
        try:
            info = self.pipe.recv()
            if isinstance(info, bytes):
                info = info.decode()
            return info
        except EOFError:
            return ""



