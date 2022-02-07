import pickle
import time
import os
import itertools
import socketserver
import shutil


from .base import BaseWaiter
from .constant import TCP_BUFF_SIZE
from .utils import get_uuid


WELCOME = "Welcome to BeeDrive Cloud Service!"
LOGIN = """<h2> Please Login</h2><form action="/" method="GET" target="_self" autocomplete="on"><p> User Name: <input type="text" name="user"><br></p><p> &nbsp; &nbsp;Password: <input type="password" name="passwd"> <input type="submit" value="Login"> </p></form>"""
SOURCE_DIR = os.path.split(os.path.split(__file__)[0])[0]
INDEX_PATH = os.path.abspath(os.path.join(SOURCE_DIR + "/source/index.html"))
ICON_PATH = os.path.abspath(os.path.join(SOURCE_DIR + "/source/icon.ico"))
INDEX_PAGE = open(INDEX_PATH, "r", encoding="utf8").read()


class GetWaiter(BaseWaiter):
    def __init__(self, infos, proto, token, root, task, conn):
        BaseWaiter.__init__(self, infos, proto, token, task, conn)
        self.root = root
        self.percent = 0.0
        self.msg = "Preparing to send file"
        self.start()

    def run(self):
        with self:
            if self.task == "index":
                self.response(INDEX_PAGE % (WELCOME, LOGIN))
            elif self.task == "login":
                self.response(self.render_login())
            elif self.task == "get":
                if self.token == "/favicon.ico":
                    self.response(open(ICON_PATH, "rb"))
                else:
                    self.response(self.render_get())
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
            self.socket.sendall(content)
        else:
            try:
                writer = socketserver._SocketWriter(self.socket)
                shutil.copyfileobj(content, writer)
                time.sleep(0.5)
            finally:
                content.close()

    def render_login(self):
        if self.user not in self.userinfo:
            return INDEX_PAGE % ("User name is incorrect!", LOGIN)
        if self.passwd != self.userinfo[self.user]:
            return INDEX_PAGE % ("Password is incorrect!", LOGIN)

        token = get_uuid()
        cookie_dir = os.path.abspath(os.path.join(self.root, ".cookies"))
        if not os.path.exists(cookie_dir):
            os.makedirs(cookie_dir)
        with open(os.path.join(cookie_dir, token), "wb") as f:
            pickle.dump({"user": self.user, "deadline": time.time() + 600}, f)
        page_content = self.render_list_dir(self.user, token)
        return INDEX_PAGE % ("Hi %s, welcome back!" % self.user, page_content)

    def render_get(self):
        cookie_dir = os.path.abspath(os.path.join(self.root, ".cookies"))
        token_path = os.path.join(cookie_dir, self.user)
        if not os.path.exists(token_path):
            return INDEX_PAGE % ("Cookie is expired!", LOGIN)
        info = pickle.load(open(token_path, "rb"))
        if time.time() > info["deadline"]:
            os.remove(token_path)
            return INDEX_PAGE % ("Cookie is expired!", LOGIN)
        
        self.user, self.passwd, query, token = info["user"], self.userinfo[info["user"]], self.passwd, self.user
        query = query.replace("%20", " ")
        target = os.path.abspath(os.path.join(self.root, query))
        if os.path.isdir(target):
            page_content = self.render_list_dir(query, token)
            return INDEX_PAGE % ("Hi %s, welcome back!" % self.user, page_content)
        try:
            return open(target, "rb")
        except OSError:
            page_content = "<h3>Sorry, cloud has no authorization to access the target file</h3>"
            return INDEX_PAGE % ("Hi %s, welcome back!" % self.user, page_content)

    def render_list_dir(self, root, token):
        content = "<h3>Visiting: /%s</h3>" % root
        content += "<h3>Upload</h3>"
        content += '<form method="post">'
        content += '<input ref="input" multiple name="file" type="file"/>'
        content += '<input type="submit" value="Upload"/></form>'
        content += "<br>"
        
        content += "<h3>Download</h3>"
        content += "<ul>"
        if root != self.user:
            father_root = root[:-1] if root.endswith("/") else root
            father_root = os.path.split(father_root)[0]
            content += '<li><a href="/?cookie=%s&file=%s">../</a>' % (token, father_root)

        dirs, files = [], []
        dir_path = os.path.abspath(os.path.join(self.root, root))
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
            content += '<li><a href="/?cookie=%s&file=%s">%s</a>' % (token, link, fname)
        content += "</ul>"
        return content
