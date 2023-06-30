import pickle
import time
import os
import itertools
import socketserver
import shutil

from .core import BaseWaiter, FileLocker
from .constant import TCP_BUFF_SIZE, END_PATTERN_COMPILE
from .utils import get_uuid, clean_path, safety_sleep
from .logger import callback


COOKIE_DIR = clean_path(os.path.join(os.environ.get("TEMP", ""), ".beedrive/cookies"))
if not os.path.exists(COOKIE_DIR):
    os.makedirs(COOKIE_DIR)
WELCOME = "Welcome to BeeDrive Cloud Service!"
LOGIN = """<h2> Please Login</h2><form action="%s" method="GET" target="_self" autocomplete="on"><p> User Name: <input type="text" name="user"><br></p><p> &nbsp; &nbsp;Password: <input type="password" name="passwd"> <input type="submit" value="Login"> </p></form>"""
SOURCE_DIR = os.path.split(os.path.split(__file__)[0])[0]
INDEX_PATH = clean_path(os.path.join(SOURCE_DIR, "source/index.html"))
ICON_PATH = clean_path(os.path.join(SOURCE_DIR, "source/icon.ico"))
INDEX_PAGE = open(INDEX_PATH, "r", encoding="utf8").read()


class HTTPWaiter(BaseWaiter):
    def __init__(self, infos, proto, token, roots, task, conn):
        BaseWaiter.__init__(self, infos, proto, token, task, conn, roots)
        self.msg = "Preparing to send file"
        self.start()

    def run(self):
        with self:
            if self.is_conn:
                try:
                    if self.task == "index":
                        self.response(INDEX_PAGE % (WELCOME, LOGIN % self.redirect))
                    elif self.task == "login":
                        self.response(self.do_login())
                    elif self.task == "get":
                        if self.token == "/favicon.ico":
                            self.response(open(ICON_PATH, "rb"))
                        else:
                            self.response(self.do_get())
                    elif self.task == "post":
                        self.response(self.do_post())
                    elif self.task == "newdir":
                        self.response(self.do_newdir())

                except RuntimeError as e:
                    callback(str(e))
                        
                except Exception as e:
                    callback("Encounter error: %s" % e, "error")
                    
                finally:
                    time.sleep(3.)
                    self.socket.close()
                    self.clean_local_cookie()

    def response(self, content):
        if isinstance(content, str):
            content = content.encode("utf-8")
        ctype = "text/html; charset=utf-8" if isinstance(content, bytes) else "application/octet-stream"
        clength = len(content) if isinstance(content, bytes) else str(os.fstat(content.fileno())[6])
        cdispos = "inline" if isinstance(content, bytes) else 'attachment; filename="%s"' % os.path.split(content.name)[-1]
        header = ["HTTP/1.1 200 OK",
                  "Connection: Close",
                  "Content-Type: %s" % ctype,
                  "Content-Length: %s" % clength,
                  'Content-Disposition: %s' % cdispos,
                  "Cache-Control: no-cache",
                  "\r\n"]
        header = "\r\n".join(header).encode("utf8")
        self.socket.sendall(header)
        if self.proto.endswith("PROXY"):
            if isinstance(content, bytes):
                for i in range(len(content) // TCP_BUFF_SIZE + 1):
                    seg = content[i * TCP_BUFF_SIZE: (i+1) * TCP_BUFF_SIZE]
                    self.send(seg)
            elif isinstance(content, FileLocker):
                for line in content.open():
                    self.send(line)
                content.close()
        else:
            if isinstance(content, bytes):
                self.socket.sendall(content)                
            else:
                try:
                    writer = socketserver._SocketWriter(self.socket)
                    shutil.copyfileobj(content.open(), writer)
                except BrokenPipeError:
                    # user may stop the downloading
                    pass
                finally:
                    # give time to let the cache flush
                    time.sleep(0.5)
                    content.close()
                    
    def do_login(self):
        socketname = self.socket.getpeername()
        if self.user not in self.userinfo:
            callback("IP=%s login with a wrong user name" % str(socketname))
            return INDEX_PAGE % ("User name is incorrect!", LOGIN % self.redirect)
        if self.passwd != self.userinfo[self.user]:
            callback("User=%s login with a wrong password" % self.user)
            return INDEX_PAGE % ("Password is incorrect!", LOGIN % self.redirect)

        self.token = get_uuid()
        with open(os.path.join(COOKIE_DIR, self.token), "wb") as f:
            pickle.dump({"user": self.user, "deadline": time.time() + 600, "token": self.token}, f)
        callback("User=%s login success!" % self.user)
        page_content = self.render_list_dir(self.user)
        return INDEX_PAGE % ("Hi %s, welcome back!" % self.user, page_content)

    def do_get(self):
        rslt = self.check_cookie()
        target = self.target.replace("%20", " ")
        target = target.encode("utf8")
        query = os.path.join(self.pwd, self.target)
        target = self.check_valid_access(query)
        if os.path.isdir(target):
            callback("User=%s visits dirname: %s" % (self.user, target))
            page_content = self.render_list_dir(query)
            return INDEX_PAGE % ("Hi %s, welcome back!" % self.user, page_content)
        try:
            f = FileLocker(target, "rb")
            callback("User=%s download file: %s" % (self.user, target))
            return f
        except OSError:
            page_content = "<h3>Sorry, cloud has no authorization to access the target file</h3>"
            return INDEX_PAGE % ("Hi %s, welcome back!" % self.user, page_content)

    def do_post(self):
        rslt = self.check_cookie()
        fd = self.socket.makefile("rb", -1)
        headers = self.parse_headers(fd)
        boundary = headers[b"content-type"].split(b"=")[1]
        rest_len = int(headers[b"content-length"])
        line = fd.readline()
        rest_len -= len(line)
        files = 0
        while not line.endswith(b"--\r\n"):
            line = fd.readline()
            rest_len -= len(line)
            fname = line.strip().split(b";")[-1].split(b"=")[-1][1:-1].decode("utf8")
            if len(fname) == 0:
                break
            fpath = self.check_valid_access(os.path.join(self.pwd, fname))
            ffold = os.path.dirname(fpath)
            if not os.path.exists(ffold):
                os.makedirs(ffold)
            line = fd.readline()
            rest_len -= len(line)
            line = fd.readline()
            rest_len -= len(line)
            
            try:
                with FileLocker(fpath, "wb") as fw:
                    callback("User=%s upload file: %s" % (self.user, fpath))
                    while rest_len > 0:
                        line = END_PATTERN_COMPILE.sub(b"", fd.readline())
                        rest_len -= len(line)
                        if boundary in line:
                            files += 1
                            break
                        fw.write(line)
            except IOError:
                break
        page_content = self.render_list_dir(self.pwd)
        callback("Totally uploaded %d files by %s" % (files, self.user))
        return INDEX_PAGE % ("Hi %s, upload %d files success!" % (self.user, files), page_content)

    def do_newdir(self):
        rslt = self.check_cookie()
        query = self.target.replace("+", " ").replace("%2B", "+")
        folder = self.check_valid_access(os.path.join(self.pwd, query))
        os.makedirs(folder, exist_ok=True)
        callback("User=%s create new folder=%s" % (self.user, folder))
        content = self.render_list_dir(self.pwd)
        return INDEX_PAGE % ("Hi %s, create new folder success!" % self.user, content)

    def render_list_dir(self, root):
        root = self.check_valid_access(root).replace(self.roots[0], "")
        if ord(root[0]) == 47:
            root = root[1:]
        cookie = "%s?cookie=%s&root=%s" % (self.redirect, self.token, root)
        content = "<h3>Visiting: /%s</h3>" % root
        content += '<form method="get" action="%s">' % self.redirect
        content += '<input type="hidden" name="cookie" value="%s">' % self.token
        content += '<input type="hidden" name="root" value="%s">' % root
        content += '<input ref="input" type="text" name="newdirname">&nbsp&nbsp'
        content += '<input type="submit" value="New Dir"></form>'

        content += "<h3>Upload</h3>"
        content += '<form method="post" enctype="multipart/form-data" action="%s&upload=%s">' % (cookie, root)
        content += '<input ref="input" multiple="multiple" name="file[]" type="file"/>'
        content += '<input type="submit" value="Upload"/></form><br>'
        
        content += "<h3>Download</h3>"
        content += "<ul>"
        if root != self.user:
            father_root = root[:-1] if root.endswith("/") else root
            father_root = os.path.dirname(father_root)
            content += '<li><a href="%s&file=../">../</a>' % (cookie, )
        dirs, files = [], []
        dir_path = clean_path(os.path.join(self.roots[0], root))
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
        for each in sorted(os.listdir(dir_path)):
            if os.path.split(each)[-1].startswith("."):
                pass
            elif os.path.isdir(os.path.join(dir_path, each)):
                each += r"/"
                dirs.append(each)
            else:
                files.append(each)

        for fname in itertools.chain(dirs, files):
            link = clean_path(os.path.join(dir_path, fname)).replace(self.roots[0], "")
            if ord(link[0]) == 47:
                link = link[1:]
            content += '<li><a href="%s&file=%s">%s</a>' % (cookie, fname.encode("utf8"), fname)
        return content + "</ul>"

    def parse_headers(self, fd):
        headers = {}
        while True:
            line = fd.readline(TCP_BUFF_SIZE)
            if line in (b"\r\n", b"\n", b""):
                break
            key, val = line.rstrip(b"\r\n").split(b":", 1)
            headers[key.strip().lower()] = val.strip()
        return headers

    def check_cookie(self):
        token_path = clean_path(os.path.join(COOKIE_DIR, self.cookie))
        if not os.path.exists(token_path):
            return self.response(INDEX_PAGE % ("Cookie is expired!", LOGIN % self.redirect))
                                       
        info = pickle.load(open(token_path, "rb"))
        if time.time() > info["deadline"]:
            os.remove(token_path)
            return self.response(INDEX_PAGE % ("Cookie is expired!", LOGIN % self.redirect))
        self.user, self.token = info["user"], info["token"]
        self.pwd = self.pwd.replace("\\", "/").replace("%2F", "/").replace("%2B", "/").replace("%20", " ").replace("+", " ")
        self.check_valid_access(self.pwd)
        return True

    def check_valid_access(self, workdir):
        valid_path = clean_path(os.path.join(self.roots[0], workdir))
        if not valid_path.startswith(clean_path(os.path.join(self.roots[0], self.user))):
            cookie = os.path.join(COOKIE_DIR, self.cookie)
            if os.path.exists(cookie):
                os.remove(cookie)
            safety_sleep()
            self.response(INDEX_PAGE % ("Invalid access!", LOGIN % self.redirect))
            raise RuntimeError("User=%s is rejected to access %s!" % (self.user, valid_path))
        return valid_path

    def clean_local_cookie(self):
        for cookie in os.listdir(COOKIE_DIR):
            cookie_path = os.path.join(COOKIE_DIR, cookie)
            cookie = pickle.load(open(cookie_path, "rb"))
            if time.time() > cookie["deadline"]:
                os.remove(cookie_path)
    
