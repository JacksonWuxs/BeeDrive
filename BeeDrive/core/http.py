
from os import path
from .base import BaseWaiter
from .constant import TCP_BUFF_SIZE


SUCCESS_HEAD = b"HTTP/1.1 200 OK\r\n\r\n"
SOURCE_DIR = path.split(path.split(__file__)[0])[0]
with open(SOURCE_DIR + "/source/index.html", "rb") as f:
    INDEX_PAGE = f.read()


class GetWaiter(BaseWaiter):
    def __init__(self, user, passwd, root, task, conn, encrypt):
        BaseWaiter.__init__(self, user, passwd, task, conn, encrypt)
        self.root = path.join(path.abspath(root), user)
        self.percent = 0.0
        self.msg = "Preparing to send file"
        self.start()

    def run(self):
        head, content = self.socket.recv(TCP_BUFF_SIZE).decode().split("\r\n\r\n")
        
        if self.user == "/":
            HELLO = b"Welcome to BeeDrive Cloud Service!"
            CONTENT = b"""<h2> Please Login</h2><form action="/" method="GET" target="_self" autocomplete="on"><p> User Name: <input type="text" name="user"><br></p><p> &nbsp; &nbsp;Password: <input type="password" name="passwd"> <input type="submit" value="Login"> </p></form>"""
            PAGE = SUCCESS_HEAD + INDEX_PAGE % (HELLO, CONTENT)
        elif self.user.startswith("/?user="):
            user, passwd = head[2:].split("&")
            self.socket.sendall(PAGE)
            self.socket.close()
        print(self.user)
        print("--" * 10)
        print(head)
        print("--" * 10)
        print(content)
                
