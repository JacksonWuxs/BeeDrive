
import os
import uuid
import time
import socket
import random


def clean_path(root):
    if isinstance(root, (tuple, list)):
        return list(map(clean_path, root))
    return os.path.abspath(root).replace("\\", "/")



def build_connect(host, port):
    conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    conn.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
    conn.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, True)
    try:
        conn.connect((host, port))
        return conn
    except ConnectionRefusedError:
        return "Connection Refused"
    except TimeoutError:
        return "Timeout"
    except Exception:
        return "UnknowError Raised during building connection"


def disconnect(sock):
    if sock:
        try:
            sock.shutdown(2)
        except IOError:
            pass
        except OSError:
            pass
        sock.close()
    return sock


def read_until(sock, seg=b"\n", timeout=1.0):
    sock.settimeout(timeout * 0.01)
    buffer = []
    begin = time.time()
    while time.time() - begin < timeout:
        try:
            buffer.append(sock.recv(1))
            if buffer[-1] in (seg, b""):
                break
        except socket.timeout:
            time.sleep(timeout * 0.01)
    sock.settimeout(None)
    return b"".join(buffer)

def get_mac():
    addr = hex(uuid.getnode())[2:]
    return '-'.join(addr[i:i+2] for i in range(0, len(addr), 2))


def get_uuid():
    return str(uuid.uuid1())


def safety_sleep():
    time.sleep(random.randint(1, 10))


def base_coder(text):
    if isinstance(text, bytes):
        return text
    return text.encode("utf8")


def clean_coder(text):
    return text
