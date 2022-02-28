import os
import pickle
import time

from .utils import clean_path
from .core import BaseClient, BaseWaiter, FileAccessLocker
from .encrypt import file_md5
from .constant import STAGE_DONE, STAGE_FAIL, TCP_BUFF_SIZE, DISK_BUFF_SIZE
from .logger import callback, processbar, flush


class DownloadClient(BaseClient):
    def __init__(self, user, psd, cloud, file, root, retry, encrypt, proxy):
        BaseClient.__init__(self, user, psd, cloud, 'download', retry, encrypt, proxy)
        self.root = clean_path(root)
        self.fold = os.path.dirname(file)
        self.file = file
        self.percent = 0.0
        self.start()
        
    def prepare(self):
        self.msg = "Collecting file information"
        loc_fold = clean_path(os.path.join(self.root, self.fold))
        loc_file = clean_path(os.path.join(self.root, self.file))
        fsize = os.path.getsize(loc_file) if os.path.isfile(loc_file) else 0
        fcode = file_md5(loc_file, fsize) if os.path.isfile(loc_file) else b""
        return {"fname": os.path.split(self.file)[1],
                "fsize": fsize,
                "local_fold": loc_fold,
                "local_file": loc_file,
                "fcode": fcode}
                

    def process(self, fname, fcode, fsize, local_fold, local_file):
        # update file information
        self.send(pickle.dumps({'fname': fname, 'ffold': self.fold,
                                'fcode': fcode, 'fsize': fsize}))
        self.msg = "Verifying file information"
        file_info = pickle.loads(self.recv())
        if "error" in file_info:
            self.msg = file_info["error"]
            self.stage = STAGE_FAIL
            callback(self.msg)
            return True
        
        fcode = file_info["fcode"]
        fsize = file_info["fsize"]
        bkpnt = file_info["bkpt"]
        mode = "wb" if bkpnt == 0 else "ab"

        # create a folder if it doesn't exist
        if not os.path.isdir(local_fold):
            os.makedirs(local_fold)

        # begin to reciv file
        task = "Download:%s" % os.path.split(self.file)[1]
        begin_time = last_time = time.time()
        self.percent = bkpnt / fsize
        self.send(b"ready")
        with open(local_file, mode, DISK_BUFF_SIZE) as f:
            while self.is_conn and self.percent < 1:
                text = self.recv()
                if not text:
                    break
                
                f.write(text)
                bkpnt += len(text)
                self.percent = bkpnt / fsize
                if time.time() - last_time >= 0.1:
                    spent = max(0.001, time.time() - begin_time)
                    self.msg = processbar(self.percent, fname, bkpnt/spent, spent)

        # check file is correct
        bkpnt = os.path.getsize(local_file)
        spent = max(0.001, time.time() - begin_time)
        self.msg = processbar(bkpnt/fsize, task, bkpnt/spent, spent)
        check = file_md5(local_file, bkpnt) == fcode
        if check:
            self.send(STAGE_DONE)
            self.msg = "File has been received"
        else:
            self.send(STAGE_FAIL)
            self.msg = "Task is failed"
        return check
    

class DownloadWaiter(BaseWaiter):
    def __init__(self, infos, proto, token, root, task, conn):
        BaseWaiter.__init__(self, infos, proto, token, task, conn, root)
        self.percent = 0.0
        self.msg = "Preparing to send file"
        self.start()

    def run(self):
        with self:
            if not self.is_conn:
                self.stage = STAGE_FAIL
                return False
            # detail information of task
            header = pickle.loads(self.recv())
            fname = header['fname']
            fcode = header['fcode']
            fsize = header['fsize']
            ffold = header['ffold']
            local_file = clean_path(os.path.join(self.roots[0], self.user, ffold, fname))

            # check wether the target file is in under other users
            if not local_file.startswith(self.roots[0]):
                self.send(pickle.dumps({"error": "No authorized to download this file!"}))
                self.msg = "%s is trying to visit file %s without authorization!" % (self.info, fname)
                callback(self.msg, "warn")
                self.stage = STAGE_FAIL
                return

            # check wether the target file is exist
            if not os.path.isfile(local_file):
                self.send(pickle.dumps({"error": "File is not found on Cloud!"}))
                self.msg = "%s is trying to visit file %s which is not found!" % (self.info, fname)
                callback(self.msg, "warn")
                self.stage = STAGE_FAIL
                return
            
            local_size = os.path.getsize(local_file)
            local_code = file_md5(local_file, local_size)


            bkpnt = fsize
            if fsize > 0 and file_md5(local_file, fsize) != fcode:
                bkpnt = 0
            self.send(pickle.dumps({"fcode": local_code,
                                    "fsize": local_size,
                                    "bkpt": bkpnt}))

            self.percent = bkpnt / local_size

            task = u"Download:%s" % os.path.split(fname)[1]
            with FileAccessLocker(local_file, "rb") as f:
                begin_time = last_time = time.time()
                f.seek(bkpnt)
                if self.recv().lower() != b"ready":
                    raise ConnectionAbortedError
                
                while self.is_conn:
                    row = f.read(TCP_BUFF_SIZE)
                    if len(row) == 0:
                        break
                    self.send(row)
                    if time.time() - last_time >= 0.1:
                        bkpnt = f.tell()
                        self.percent = bkpnt / local_size
                        last_time = time.time()
                        spent_time = max(0.00001, last_time - begin_time)
                        self.msg = processbar(self.percent, task,
                                              bkpnt / spent_time, spent_time)
                        
                bkpnt = f.tell()
            spent = max(0.001, time.time() - begin_time)
            self.msg = processbar(bkpnt/local_size, task, bkpnt/spent, spent)
            self.stage = self.msg = self.recv().decode()
            flush()
