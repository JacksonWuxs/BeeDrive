import pickle
import time
import os
import itertools
import socketserver
import shutil
import re

from .base import BaseWaiter
from .constant import TCP_BUFF_SIZE
from .utils import get_uuid


WELCOME = "Welcome to BeeDrive Cloud Service!"
LOGIN = """<h2> Please Login</h2><form action="/" method="GET" target="_self" autocomplete="on"><p> User Name: <input type="text" name="user"><br></p><p> &nbsp; &nbsp;Password: <input type="password" name="passwd"> <input type="submit" value="Login"> </p></form>"""
SOURCE_DIR = os.path.split(os.path.split(__file__)[0])[0]
INDEX_PATH = os.path.abspath(os.path.join(SOURCE_DIR + "/source/index.html"))
ICON_PATH = os.path.abspath(os.path.join(SOURCE_DIR + "/source/icon.ico"))
INDEX_PAGE = open(INDEX_PATH, "r", encoding="utf8").read()


class HTTPWaiter(BaseWaiter):
    def __init__(self, infos, proto, token, root, task, conn):
        BaseWaiter.__init__(self, infos, proto, token, task, conn)
        self.root = root
        self.percent = 0.0
        self.msg = "Preparing to send file"
        self.start()

    def run(self):
        with self:
            try:
                if self.task == "login":
                    self.response(self.do_login())
                elif self.task == "get":
                    if self.token == "/favicon.ico":
                        self.response(open(ICON_PATH, "rb"))
                    else:
                        self.response(self.do_get())
                elif self.task == "post":
                    self.response(self.do_post())
                else:
                    self.response(INDEX_PAGE % (WELCOME, LOGIN))
            finally:
                self.socket.close()

    def response(self, content):
        if isinstance(content, str):
            content = content.encode("utf-8")
        ctype = "text/html; charset=utf-8" if isinstance(content, bytes) else "application/octet-stream"
        clength = len(content) if isinstance(content, bytes) else str(os.fstat(content.fileno())[6])
        cdispos = "inline" if isinstance(content, bytes) else 'attachment; filename="%s"' % os.path.split(content.name)[-1]
        header = ["HTTP/1.1 200 OK",
                  "Connection: close",
                  "Content-Type: %s" % ctype,
                  "Content-Length: %s" % clength,
                  'Content-Disposition: %s' % cdispos,
                  "Cache-Control: no-cache",
                  "\r\n"]
        header = "\r\n".join(header).encode("utf8")
        self.socket.sendall(header)
        if isinstance(content, bytes):
            self.socket.sendall(content + b"\r\n")
        else:
            try:
                writer = socketserver._SocketWriter(self.socket)
                shutil.copyfileobj(content, writer)
                time.sleep(0.5)
            finally:
                content.close()

    def do_login(self):
        if self.user not in self.userinfo:
            return INDEX_PAGE % ("User name is incorrect!", LOGIN)
        if self.passwd != self.userinfo[self.user]:
            return INDEX_PAGE % ("Password is incorrect!", LOGIN)

        self.token = get_uuid()
        cookie_dir = os.path.abspath(os.path.join(self.root, ".cookies"))
        if not os.path.exists(cookie_dir):
            os.makedirs(cookie_dir)
        with open(os.path.join(cookie_dir, self.token), "wb") as f:
            pickle.dump({"user": self.user, "deadline": time.time() + 600, "token": self.token}, f)
        page_content = self.render_list_dir(self.user)
        return INDEX_PAGE % ("Hi %s, welcome back!" % self.user, page_content)

    def do_get(self):
        rslt = self.check_cookie()
        if isinstance(rslt, str):
            return rslt
        self.passwd, query = self.userinfo[self.user], self.passwd
        query = query.replace("%20", " ")
        target = os.path.abspath(os.path.join(self.root, query))
        if os.path.isdir(target):
            page_content = self.render_list_dir(query)
            return INDEX_PAGE % ("Hi %s, welcome back!" % self.user, page_content)
        try:
            return open(target, "rb")
        except OSError:
            page_content = "<h3>Sorry, cloud has no authorization to access the target file</h3>"
            return INDEX_PAGE % ("Hi %s, welcome back!" % self.user, page_content)

    def do_post(self):
        rslt = self.check_cookie()
        if isinstance(rslt, str):
            return rslt
        fd = self.socket.makefile("rb", -1)
        headers = self.parse_headers(fd)
        boundary = headers[b"content-type"].split(b"=")[1]
        rest_len = int(headers[b"content-length"])
        line = fd.readline()
        rest_len -= len(line)
        while not line.endswith(b"--\r\n"):
            line = fd.readline()
            rest_len -= len(line)
            line = line.decode("utf-8").strip().replace(":", "").replace(";", "")
            fname = line.split(" ")[-1].split("=")[-1][1:-1]
            if len(fname) == 0:
                break
            fpath = os.path.abspath(os.path.join(self.root, self.user, fname))
            ffold = os.path.dirname(fpath)
            if not os.path.exists(ffold):
                os.makedirs(ffold)
            line = fd.readline()
            rest_len -= len(line)
            line = fd.readline()
            rest_len -= len(line)
            try:
                with open(fpath, "wb") as fw:
                    while rest_len > 0:
                        line = fd.readline()
                        rest_len -= len(line)
                        if boundary in line:
                            break
                        fw.write(line)
            except IOError:
                break
        page_content = self.render_list_dir(self.user)
        return INDEX_PAGE % ("Hi %s, welcome back!" % self.user, page_content)


    def render_list_dir(self, root):
        content = "<h3>Visiting: /%s</h3>" % root
        content += "<h3>Upload</h3>"
        content += '<form method="post" enctype="multipart/form-data" action="/?cookie=%s&upload">' % self.token
        content += '<input ref="input" multiple="multiple" name="file[]" type="file"/>'
        content += '<input type="submit" value="Upload"/></form>'
        content += "<br>"
        
        content += "<h3>Download</h3>"
        content += "<ul>"
        if root != self.user:
            father_root = root[:-1] if root.endswith("/") else root
            father_root = os.path.split(father_root)[0]
            content += '<li><a href="/?cookie=%s&file=%s">../</a>' % (self.token, father_root)

        dirs, files = [], []
        dir_path = os.path.abspath(os.path.join(self.root, root))
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
        for each in sorted(os.listdir(dir_path)):
            if os.path.isdir(os.path.join(dir_path, each)):
                each += r"/"
                dirs.append(each)
            else:
                files.append(each)

        for fname in itertools.chain(dirs, files):
            link = os.path.join(dir_path, fname).replace(self.root, "")
            if ord(link[0]) in (92, 47):
                link = link[1:]
            content += '<li><a href="/?cookie=%s&file=%s">%s</a>' % (self.token, link, fname)
        content += "</ul>"
        return content

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
        cookie_dir = os.path.abspath(os.path.join(self.root, ".cookies"))
        token_path = os.path.join(cookie_dir, self.user)
        if not os.path.exists(token_path):
            return INDEX_PAGE % ("Cookie is expired!", LOGIN)
        info = pickle.load(open(token_path, "rb"))
        if time.time() > info["deadline"]:
            os.remove(token_path)
            return INDEX_PAGE % ("Cookie is expired!", LOGIN)
        self.user, self.token = info["user"], info["token"]
        return True
