from os import path, makedirs
from pickle import dumps, loads
from time import time, sleep
from traceback import format_exc

from .base import BaseClient, BaseWaiter
from .encrypt import file_md5
from .constant import TCP_BUFF_SIZE, DISK_BUFF_SIZE, STAGE_DONE, STAGE_FAIL
from .logger import callback_info, callback_processbar, callback_flush, callback_error


class UploadClient(BaseClient):
    def __init__(self, user, psd, cloud, file, retry, encrypt, fold, proxy):
        BaseClient.__init__(self, user, psd, cloud, 'upload', retry, encrypt, proxy)
        self.fold = fold
        self.file = file
        self.percent = 0.0
        self.start()
        
    def prepare(self):
        self.msg = "Collecting file information"
        fname = path.split(self.file)[1]
        fsize = path.getsize(self.file)
        fcode = file_md5(self.file, fsize)
        return {"fname": fname, "fsize": fsize, "fcode": fcode}

    def process(self, fname, fcode, fsize):
        self.msg = "Verifying task progress"
        self.send(dumps({'fname': fname, 'fsize': fsize,
                         'fcode': fcode, 'fold': self.fold}))
        info = loads(self.recv())
        bkpnt = 0
        if file_md5(self.file, info["size"]) == info["code"]:
            bkpnt = info["size"]
        self.send(str(bkpnt).encode())
        
        task = "Upload:%s" % fname
        begin_time = last_time = time()
        if self.recv().lower() != b"ready":
            raise ConnectionAbortedError
            
        with open(self.file, 'rb') as f:
            f.seek(bkpnt)
            while self.isConn:
                row = f.read(TCP_BUFF_SIZE)
                if len(row) == 0:
                    break
                self.send(row)
                if time() - last_time >= 0.1:
                    bkpnt = f.tell()
                    self.percent = bkpnt / fsize
                    spent_time = max(0.1, time() - begin_time)
                    self.msg = callback_processbar(
                                    self.percent, task,
                                    bkpnt / spent_time,
                                    spent_time)
                    last_time = time()
            bkpnt = f.tell()
            spent_time = max(0.001, time() - begin_time)
            self.percent = bkpnt / fsize if fsize > 0 else 1.0
            self.msg = callback_processbar(self.percent, task, fsize/spent_time, spent_time)
        return eval(self.recv().decode())
            

class UploadWaiter(BaseWaiter):
    def __init__(self, user, passwd, root, task, conn, encrypt):
        BaseWaiter.__init__(self, user, passwd, task, conn, encrypt)
        self.root = path.abspath(root)
        self.percent = 0.0
        self.msg = "Preparing to recive file"
        self.start()

    def run(self):
        with self:
            # detail information of task
            self.msg = "Collecting file information"
            header = loads(self.recv())
            fsize = header['fsize']
            fpath = header['fold']
            fname = header['fname']
            fcode = header['fcode']
            folder_path = path.abspath(path.join(self.root, self.user, fpath))

            # create a folder if it doesn't exist
            if not path.isdir(folder_path):
                makedirs(folder_path)
            fpath = path.join(folder_path, fname)
            
            # new file or breakpoint continuation
            current_size = path.getsize(fpath) if path.exists(fpath) else 0
            current_code = file_md5(fpath, current_size) if path.exists(fpath) else ""
            self.send(dumps({"size": current_size, "code": current_code}))
            bkpnt = int(self.recv())
            
            mode = 'wb' if bkpnt == 0 else 'ab+'   
            self.percent = bkpnt / fsize if fsize > 0 else 1.0

            # Now begin to recive file
            begin_time = last_time = time()
            task = u"Upload:%s" % fname
            self.send(b"ready")
            with open(fpath, mode, DISK_BUFF_SIZE) as f:
                while self.percent < 1.0:
                    text = self.recv()
                    if not text:
                        callback_info("Connection is broken.")
                        break
                    f.write(text)
                    bkpnt += len(text)
                    self.percent = bkpnt / fsize
                    if time() - last_time >= 0.1:
                        spent = max(0.001, time() - begin_time)
                        self.msg = callback_processbar(self.percent, fname, bkpnt/spent, spent)

            bkpnt = path.getsize(fpath)
            spent = max(0.001, time() - begin_time)
            progress = bkpnt/fsize if fsize > 0 else 1.0
            self.msg = callback_processbar(progress, task, bkpnt/spent, spent)
            check = file_md5(fpath, bkpnt) == fcode
            self.stage = STAGE_DONE if check else STAGE_FAIL
            self.send(str(check))
