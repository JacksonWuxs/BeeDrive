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


class GetWaiter(BaseWaiter):
    def __init__(self, infos, proto, token, root, task, conn):
        BaseWaiter.__init__(self, infos, proto, token, task, conn)
        self.root = root
        self.percent = 0.0
        self.msg = "Preparing to send file"
        self.start()

    def run(self):
        with self:
            self.socket.recv(TCP_BUFF_SIZE)
            if self.task == "index":
                title, content = WELCOME, LOGIN
            elif self.task == "login":
                title, content = self.render_login()
            elif self.task == "download":
                title, content = self.render_download()
            else:
                return
            self.response("200", title, content)
            self.socket.recv(TCP_BUFF_SIZE)

    def response(self, status, title_line, body):
        header = "HTTP/1.0 200 OK\r\n\r\n"
        page = header + INDEX_PAGE % (title_line, body)
        self.socket.sendall(page.encode())

    def render_login(self):
        if self.user not in self.userinfo:
            return "User name is incorrect!", LOGIN
        if self.passwd != self.userinfo[self.user]:
            return "Password is incorrect!", LOGIN

        head = "Welcom back %s!" % self.user
        token = get_uuid()
        with open(os.path.join(self.root, "." + token), "wb") as f:
            pickle.dump({"user": self.user, "deadline": time.time() + 600}, f)
        return head, self.render_list_dir(self.user, token)

    def render_download(self):
        self.socket.recv(TCP_BUFF_SIZE)
        token_path = os.path.join(self.root, "." + self.user)
        if not os.path.exists(token_path):
            return "Cookie Token is expired!", LOGIN
        info = pickle.load(open(token_path, "rb"))
        if time.time() > info["deadline"]:
            return "Cookie Token is expired!", LOGIN
        
        self.user, self.passwd, query, token = info["user"], self.userinfo[info["user"]], self.passwd, self.user
        query = query.replace("%20", " ")
        head = "Welcom back %s!" % self.user
        if os.path.isdir(os.path.join(self.root, query)):
            return head, self.render_list_dir(query, token)
        

    def render_list_dir(self, root, token):
        content = "<h2>Directory listing for /%s </h2>" % root
        content += "<ul>"
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
