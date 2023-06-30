# the following code is privded by GPT-4
import os
import time

from .utils import clean_path

if os.name == 'posix':
    import fcntl
    locking = lambda fd: fcntl.flock(fd, fcntl.LOCK_EX)
    releasing = lambda fd: fcntl.flock(fd, fcntl.LOCK_UN)
elif os.name == 'nt':
    import msvcrt
    locking = lambda fd: msvcrt.locking(fd.fileno(), msvcrt.LK_LOCK, 1)
    releasing = lambda fd: msvcrt.locking(fd.fileno(), msvcrt.LK_UNLCK, 1)
else:
    import warnings
    warnings.warn('BeeDrive does not support file locking on your system!' +\
                  'Please do not modify the same file occurantely!')
    locking = releasing = lambda fd: fd


class FileLocker:
    def __init__(self, fpath, mode="rb", buffering=-1, encoding=None):
        self.lock = _SideLocker(fpath)
        self.path = fpath
        self.file = None
        self.mode = mode
        self.encode = encoding
        self.buffer = buffering

    def __enter__(self):
        return self.open()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        if exc_type:
            raise exc_type(exc_val)

    def open(self):
        if self.file is None:
            self.lock.acquire()
            self.file = open(self.path, self.mode, self.buffer, self.encode)
        return self.file

    def close(self):
        if self.file is not None:
            self.file.close()
            self.lock.release()
            self.file = None
        
    def reopen(self, mode="rb", buffering=-1, encoding=None):
        assert self.file is not None and self.lock.is_locked, "please require the lock for the file at first"
        self.file.close()
        self.mode, self.buffer, self.encode = mode, buffering, encoding
        self.file = open(self.path, self.mode, self.buffer, self.encode)
        return self.file
        


class _SideLocker:
    def __init__(self, file_path):
        folder = os.path.dirname(file_path)
        fname = "." + os.path.split(file_path)[-1] + ".bdfl" # bdl = Bee Drive File Lock
        os.makedirs(folder, exist_ok=True)
        self.path = clean_path(os.path.join(folder, fname))
        self.file = None
        self.locked = False

    @property
    def is_locked(self):
        return self.locked

    def acquire(self):
        if self.file is None:
            self.file = open(self.path, "w")
            while True:
                try:
                    locking(self.file)
                    self.locked = True
                    break
                except PermissionError:
                    time.sleep(1.0)
                except OSError:
                    time.sleep(1.0)

    def release(self):
        if self.file is not None:
            releasing(self.file)
            self.file.close()
            os.remove(self.path)
            self.locked = True
            self.file = None
        
