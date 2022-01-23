from os import path, makedirs
from json import dumps, loads, JSONDecodeError
from time import time, sleep
from traceback import format_exc

from .base import BaseClient, BaseWaiter
from .crypto import file_md5
from .constant import (STAGE_PRE, STAGE_RUN, STAGE_DONE,
                       STAGE_FAIL, TCP_BUFF_SIZE, DISK_BUFF_SIZE)
from .logger import callback_info, callback_processbar, callback_flush, callback_error


class UploadClient(BaseClient):
    def __init__(self, user, psd, cloud, file, crypto, sign, fold, proxy):
        BaseClient.__init__(self, user, psd, cloud, 'upload', crypto, sign, proxy)
        self.fold = fold
        self.file = file
        self.percent = 0.0
        self.start()
        
    def run(self):
        self.stage = STAGE_PRE
        self.msg = "Collecting file information"
        fname = path.split(self.file)[1]
        fsize = path.getsize(self.file)
        fcode = file_md5(self.file, fsize)

        with self:
            self.send(dumps({'fname': fname, 'fsize': fsize,
                             'fcode': fcode, 'fold': self.fold}))
            try:
                self.msg = "Verifying task progress"
                info = loads(self.recv())
                bkpnt = 0
                if file_md5(self.file, info["size"]) == info["code"]:
                    bkpnt = info["size"]
                self.send(str(bkpnt).encode())
                
                task = "Upload:%s" % fname
                begin_time = last_time = time()
                update_time = 0.0
                with open(self.file, 'rb') as f:
                    f.seek(bkpnt)
                    while True:
                        row = f.read(TCP_BUFF_SIZE)
                        if len(row) == 0:
                            break
                        self.send(row)
                        if time() - last_time >= update_time:
                            bkpnt = f.tell()
                            self.percent = bkpnt / fsize
                            update_time = 0.1
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
                callback_flush()
                self.msg = self.stage = self.recv().decode()
            except Exception:
                callback_error(format_exc(), 0)
                self.msg = self.stage = STAGE_FAIL
            sleep(1)
            

class UploadWaiter(BaseWaiter):
    def __init__(self, peer, conn, root, passwd):
        BaseWaiter.__init__(self, peer, 'file', conn, peer.name, passwd)
        self.root = path.abspath(root)
        self.percent = 0.0
        self.stage = STAGE_PRE
        self.msg = ""
        self.start()

    def run(self):
        with self:
            try:
                # detail information of task
                self.msg = "Collecting file information"
                header = loads(self.recv())
                fsize = header['fsize']
                fpath = header['fold']
                fname = header['fname']
                fcode = header['fcode']
                folder_path = path.abspath(path.join(self.root, self.peer.name, fpath))

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
                self.stage = STAGE_RUN
                self.percent = bkpnt / fsize if fsize > 0 else 1.0

                # Now begin to recive file
                begin_time = last_time = time()
                update_time = 0.0
                task = u"Upload:%s" % fname
                with open(fpath, mode, DISK_BUFF_SIZE) as f:
                    while self.percent < 1.0:
                        text = self.recv()
                        if not text:
                            callback_info("Breakout with timeout ERROR")
                            break
                        f.write(text)
                        bkpnt += len(text)
                        if time() - last_time >= update_time:
                            self.percent = bkpnt / fsize
                            update_time = 0.1
                            spent = max(0.001, time() - begin_time)
                            self.msg = callback_processbar(self.percent, fname, bkpnt/spent, spent)

                bkpnt = path.getsize(fpath)
                spent = max(0.001, time() - begin_time)
                progress = bkpnt/fsize if fsize > 0 else 1.0
                self.msg = callback_processbar(progress, task, bkpnt/spent, spent)
                self.stage = STAGE_DONE if file_md5(fpath, bkpnt) == fcode else STAGE_FAIL
                self.send(self.stage)
            except JSONDecodeError:
                self.msg = self.stage = STAGE_FAIL
            except ValueError:
                self.msg = self.stage = STAGE_FAIL
            except Exception:
                self.msg = self.stage = STAGE_FAIL
        sleep(0.1)
