import os
import pickle
import time

from .utils import clean_path
from .core import BaseClient, BaseWaiter, FileAccessLocker
from .encrypt import file_md5
from .constant import DISK_BUFF_SIZE, STAGE_DONE, STAGE_FAIL
from .logger import callback, processbar, flush


class UploadClient(BaseClient):
    def __init__(self, user, psd, cloud, file, retry, encrypt, fold, proxy):
        BaseClient.__init__(self, user, psd, cloud, 'upload', retry, encrypt, proxy)
        self.fold = fold
        self.file = file
        self.percent = 0.0
        self.start()
        
    def prepare(self):
        self.msg = "Collecting file information"
        fname = os.path.split(self.file)[1]
        fsize = os.path.getsize(self.file)
        fcode = file_md5(self.file, fsize)
        return {"fname": fname, "fsize": fsize, "fcode": fcode}

    def process(self, fname, fcode, fsize):
        self.msg = "Verifying task progress"
        self.send(pickle.dumps({'fname': fname, 'fsize': fsize,
                                'fcode': fcode, 'fold': self.fold}))
        info = pickle.loads(self.recv())
        bkpnt = 0
        if file_md5(self.file, info["size"]) == info["code"]:
            bkpnt = info["size"]
        self.send(str(bkpnt).encode())
        
        task = "Upload:%s" % fname
        begin_time = last_time = time.time()
        if self.recv().lower() != b"ready":
            raise ConnectionAbortedError
        with FileAccessLocker(self.file, "rb", DISK_BUFF_SIZE) as f:
            f.seek(bkpnt)
            while self.is_conn:
                row = f.read(DISK_BUFF_SIZE)
                if len(row) == 0:
                    break
                self.send(row)
                if time.time() - last_time >= 0.1:
                    bkpnt = f.tell()
                    self.percent = bkpnt / fsize
                    last_time = time.time()
                    spent_time = max(0.1, last_time - begin_time)
                    self.msg = processbar(self.percent, task,
                                          bkpnt / spent_time, spent_time)
            bkpnt = f.tell()
            spent_time = max(0.001, time.time() - begin_time)
            self.percent = bkpnt / fsize if fsize > 0 else 1.0
            self.msg = processbar(self.percent, task, fsize/spent_time, spent_time)
        return eval(self.recv().decode("utf8"))
            

class UploadWaiter(BaseWaiter):
    def __init__(self, infos, proto, token, roots, task, conn):
        BaseWaiter.__init__(self, infos, proto, token, task, conn, roots)
        self.percent = 0.0
        self.msg = "Preparing to recive file"
        self.start()

    def run(self):
        with self:
            if not self.is_conn:
                self.stage = STAGE_FAIL
                return False
            # detail information of task
            self.msg = "Collecting file information"
            header = pickle.loads(self.recv())
            fsize = header['fsize']
            fpath = header['fold']
            fname = header['fname']
            fcode = header['fcode']
            folder_path = clean_path(os.path.join(self.roots[0], self.user, fpath))

            # create a folder if it doesn't exist
            if not os.path.isdir(folder_path):
                os.makedirs(folder_path, exist_ok=True)
            fpath = os.path.join(folder_path, fname)
            
            # new file or breakpoint continuation
            current_size = os.path.getsize(fpath) if os.path.exists(fpath) else 0
            current_code = file_md5(fpath, current_size) if os.path.exists(fpath) else ""
            self.send(pickle.dumps({"size": current_size, "code": current_code}))
            bkpnt = int(self.recv())
            
            mode = 'wb' if bkpnt == 0 else 'ab+'   
            self.percent = bkpnt / fsize if fsize > 0 else 1.0

            # Now begin to recive file
            task = u"Upload:%s" % fname
            locker = FileAccessLocker(fpath, mode, DISK_BUFF_SIZE)
            with locker as f:
                begin_time = last_time = time.time()
                self.send(b"ready")
                while self.percent < 1.0:
                    text = self.recv()
                    f.write(text)
                    bkpnt += len(text)
                    self.percent = bkpnt / fsize
                    if time.time() - last_time >= 0.1:
                        spent = max(0.001, time.time() - begin_time)
                        self.msg = processbar(self.percent, fname, bkpnt/spent, spent)

                f.flush()
                bkpnt = os.path.getsize(fpath)
                spent = max(0.001, time.time() - begin_time)
                progress = bkpnt/fsize if fsize > 0 else 1.0
                self.msg = processbar(progress, task, bkpnt/spent, spent)
                check = file_md5(fpath, bkpnt) == fcode
                self.stage = STAGE_DONE if check else STAGE_FAIL
                self.send(str(check).encode("utf8"))
                flush()

                if check:
                    # do the copy process
                    f = locker.reopen(mode="rb", buffering=DISK_BUFF_SIZE)
                    for backup_addr in self.roots[1:]:
                        backup_file = clean_path(os.path.join(backup_addr,
                                                              self.user,
                                                              header["fold"],
                                                              header["fname"]))
                        with FileAccessLocker(backup_file, "wb", -1) as fout:
                            f.seek(0)
                            while True:
                                msg = f.read(DISK_BUFF_SIZE)
                                if len(msg) == 0:
                                    break
                                fout.write(msg)

