import pickle
import time
import os
import itertools


from .base import BaseWaiter
from .constant import TCP_BUFF_SIZE
from .utils import get_uuid


WELCOME = "Welcome to BeeDrive Cloud Service!"
LOGIN = """<h2> Please Login</h2><form action="/" method="GET" target="_self" autocomplete="on"><p> User Name: <input type="text" name="user"><br></p><p> &nbsp; &nbsp;Password: <input type="password" name="passwd"> <input type="submit" value="Login"> </p></form>"""
SOURCE_DIR = os.path.split(os.path.split(__file__)[0])[0]
with open(SOURCE_DIR + "/source/index.html", "r", encoding="utf8") as f:
    INDEX_PAGE = f.read()
with open(SOURCE_DIR + "/source/icon.ico", "rb") as f:
    ICON = f.read()


class GetWaiter(BaseWaiter):
    def __init__(self, infos, proto, token, root, task, conn):
        BaseWaiter.__init__(self, infos, proto, token, task, conn)
        self.root = root
        self.percent = 0.0
        self.msg = "Preparing to send file"
        self.start()

    def run(self):
        with self:
            print(self.token, self.task, self.user, self.passwd)
            self.socket.recv(TCP_BUFF_SIZE)
            if self.task == "index":
                status, ctype, content = "200", "text/html; charset=utf-8", INDEX_PAGE % (WELCOME, LOGIN)
            elif self.task == "login":
                status, ctype, content = "200", "text/html; charset=utf-8", self.render_login()
            elif self.task == "get":
                if self.token == "/favicon.ico":
                    status, ctype, content = "200", "application/octet-stream", ICON
                else:
                    status, ctype, content = self.render_get()
       
            self.response(status, ctype, content)

    def response(self, status, ctype, content):
        if not isinstance(content, bytes):
            content = content.encode("utf8")
        header = ["HTTP/1.0 %s OK" % status,
                  "Connection: close",
                  "Content-Type: %s" % ctype,
                  #"Content-Length: %d" % (8 * len(content)),
                  "Cache-Control: no-cache",
                  "\r\n"]
        header = "\r\n".join(header).encode("utf8")
        print((header + content.strip()).decode())
        self.socket.sendall(header + content)

    def render_login(self):
        if self.user not in self.userinfo:
            return INDEX_PAGE % ("User name is incorrect!", LOGIN)
        if self.passwd != self.userinfo[self.user]:
            return INDEX_PAGE % ("Password is incorrect!", LOGIN)

        token = get_uuid()
        with open(os.path.join(self.root, "." + token), "wb") as f:
            pickle.dump({"user": self.user, "deadline": time.time() + 600}, f)
        return INDEX_PAGE % ("Welcome back %s!" % self.user, self.render_list_dir(self.user, token))

    def render_get(self):
        token_path = os.path.join(self.root, "." + self.user)
        if not os.path.exists(token_path):
            return INDEX_PAGE % ("Cookie Token is expired!", LOGIN)
        info = pickle.load(open(token_path, "rb"))
        if time.time() > info["deadline"]:
            return INDEX_PAGE % ("Cookie Token is expired!", LOGIN)
        
        self.user, self.passwd, query, token = info["user"], self.userinfo[info["user"]], self.passwd, self.user
        query = query.replace("%20", " ")
        target = os.path.join(self.root, query)
        if os.path.isdir(target):
            page = INDEX_PAGE % ("Welcome back %s!" % self.user, self.render_list_dir(query, token))
            return "200", "text/html", page
        with open(target, "rb") as f:
            return "200", "application/octet-stream", f.read()

    def render_list_dir(self, root, token):
        content = "<h2>Directory listing for /%s </h2>" % root
        content += "<ul>"
        if root != self.user:
            content += '<li><a href="/?cookie=%s&file=%s">../</a>' % (token, os.path.split(root)[0])

        dirs, files = [], []
        for each in sorted(os.listdir(os.path.join(self.root, root))):
            if os.path.isdir(os.path.join(self.root, each)):
                each += r"/"
                dirs.append(each)
            else:
                files.append(each)

        for each in itertools.chain(dirs, files):
            link = os.path.join(root, each).replace("\\", "/")
            content += '<li><a href="/?cookie=%s&file=%s">%s</a>' % (token, link, each)
        content += "</ul>"
        return content
