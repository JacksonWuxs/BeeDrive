import queue
import time
import os
import shutil

from .core import BaseClient, BaseWaiter
from .constant import STAGE_DONE, STAGE_FAIL, TCP_BUFF_SIZE, DISK_BUFF_SIZE
from .logger import callback, flush
from .utils import clean_path


utf8 = "utf8"


def parse_arguments(args):
    args = args.strip()
    if args.count(" ") == 1:
        l, r = args.split(" ")
        return l.strip(), r.strip()

    parsed = []
    while " " in args:
        for key in ["'", '"']:
            if args.startswith(key) and args.count(key) > 1:
                item, args = args[1:].split(key, 1)
                parsed.append(item)
                break
        else:
            item, args = args.split(" ", 1)
            parsed.append(item)
        args = args.strip()
    if len(args) > 0:
        parsed.append(args)
    return parsed
     

class CMDClient(BaseClient):
    def __init__(self, user, passwd, cloud, retry, encrypt, proxy, **kwrds):
        BaseClient.__init__(self, user, passwd, cloud, 'commander', retry, encrypt, proxy)
        self.stdin = queue.Queue()
        self.stdout = queue.Queue()
        self.done = False
        self.start()

    def command(self):
        while True:
            pwd = self.stdout.get().decode(utf8)
            cmd = input("%s/>" % pwd)
            self.stdin.put(cmd)
            while True:
                rsp = self.stdout.get().decode(utf8)
                if rsp == "[:DONE:]":
                    break
                print(rsp)
            if cmd == "exit":
                self.done = True
                break

    def prepare(self):
        self.msg = "Ready to command"
        return {}

    def process(self):
        self.msg = "Connected to command"
        self.stdout.put(self.recv())
        while not self.done:
            self.send(self.stdin.get())
            while True:
                rsp = self.recv()
                self.stdout.put(rsp)
                if rsp == b"[:DONE:]":
                    break
            self.stdout.put(self.recv())
        return True
            


class CMDWaiter(BaseWaiter):
    def __init__(self, infos, proto, token, roots, task, conn):
        BaseWaiter.__init__(self, infos, proto, token, task, conn, roots)
        self.msg = "Preparing to follow command"
        self.start()

    def run(self):
        with self:
            if not self.is_conn:
                self.stage = STAGE_FAIL
                return False
            callback("User=%s login as a commander." % self.user)
            root = pwd = clean_path(self.roots[0] + "/" + self.user)
            self.send(pwd.replace(root, "~").encode(utf8))
            while True:
                cmd = self.recv().decode(utf8)
                callback("User=%s executes: %s" % (self.user, cmd))
                if cmd == "exit":
                    self.send("user logout!")
                    time.sleep(1.0)
                
                elif cmd.startswith("ls"):
                    self.do_ls(root, pwd, cmd)

                elif cmd.startswith("cd "):
                    pwd = self.do_cdrm(root, pwd, cmd)

                elif cmd.startswith("cp "):
                    self.do_cpmv(root, pwd, cmd)

                elif cmd.startswith("find "):
                    pass

                elif cmd.startswith("share "):
                    pass

                elif cmd.startswith("mkdir "):
                    self.do_mkdir(root, pwd, cmd)

                elif cmd.startswith("mv "):
                    self.do_cpmv(root, pwd, cmd)

                elif cmd.startswith("rm "):
                    pwd = self.do_cdrm(root, pwd, cmd)
                    
                self.send("[:DONE:]")
                time.sleep(0.1)
                self.send(pwd.replace(root, "~"))

    def do_mkdir(self, root, pwd, cmd):
        arg = clean_path(pwd + "/" + cmd[6:])
        if not arg.startswith(root):
            arg.send("Error: You don't have access to visit this folder!")
        else:
            os.makedirs(arg, exist_ok=True)

    def do_cdrm(self, root, pwd, cmd):
        arg = clean_path(pwd + "/" + cmd[3:])
        if not arg.startswith(root):
            arg.send("Error: You don't have access to visit this folder!")
        elif not os.path.exists(arg):
            self.send("Error: The file you are visit does not exist!")
        elif cmd[:2] == "cd":
            pwd = arg
        else:
            for src_dir, dirs, files in os.walk(arg):
                for file_ in files:
                    os.remove(os.path.join(src_dir, file_))
            shutil.rmtree(src_dir)
        os.makedirs(root, exist_ok=True)
        return arg

    def do_cpmv(self, root, pwd, cmd):
        args = parse_arguments(cmd[3:])
        if len(args) != 2:
            self.send("Error: cp command only accept two parameters.")
            return
        l = clean_path(pwd + '/' + args[0])
        r = clean_path(pwd + '/' + args[1])
        if l == r:
            return
        if not l.startswith(root):
            self.send("Error: You don't have access to visit the source file/dir.")
            return
        if not r.startswith(root):
            self.send("Error: You don't have access to visit the target file/dir.")
            return
        if not os.path.exists(l):
            self.send("Error: the source file/dir does not exist!")
            return
        op = shutil.copy2 if cmd[:2] == "cp" else shutil.move
        if os.path.isfile(l):
            if args[1].endswith("/"):
                os.makedirs(r, exist_ok=True)
                r += "/" + os.path.split(l)[-1]
            else:
                os.makedirs(os.path.split(r)[0], exist_ok=True)
            op(l, r)
        else:
            for src_dir, dirs, files in os.walk(l):
                dst_dir = src_dir.replace(l, r, 1)
                os.makedirs(dst_dir, exist_ok=True)
                for file_ in files:
                    op(os.path.join(src_dir, file_),
                       os.path.join(dst_dir, file_))
            if cmd[:2] == "mv":
                shutil.rmtree(l)
        return l, r
            
    def do_ls(self, root, pwd, cmd):

        def hum_convert(value):
            units = ["B", "KB", "MB", "GB", "TB", "PB"]
            size = 1024.0
            for i in range(len(units)):
                if (value / size) < 1:
                    return ("%.2f%s" % (value, units[i])).rjust(8, " ")
                value = value / size
                
        args = cmd.split(" ", 1)[1] if " " in cmd else "./"
        args = clean_path(pwd + "/" + args)
        
        info = []
        if not args.startswith(root):
            info.append("Error: You don't have access to visit this folder!")
        elif not os.path.isdir(args):
            info.append("Error: The path you provided is not a valid folder!")
        else:
            files = os.listdir(args)
            for file in os.listdir(args):
                stat = os.stat(clean_path(args + '/' + file))
                info.append(time.ctime(stat.st_mtime) + '  ')
                info.append(hum_convert(stat.st_size) + '  ')
                info.append(file + '\n')
        self.send("".join(info)[:-1])
