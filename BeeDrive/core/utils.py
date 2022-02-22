import time
import socket
from uuid import getnode, uuid1
from os import path, listdir

from .constant import TCP_BUFF_SIZE


def clean_path(root):
    if isinstance(root, (tuple, list)):
        return list(map(clean_path, root))
    return path.abspath(root).replace("\\", "/")


def trust_sleep(time_to_sleep, longest_sleep=604800):
    assert isinstance(time_to_sleep, (float, int))
    assert time_to_sleep > 0
    start = time.time()
    stop = start + time_to_sleep
    while time.time() < stop:
        try:
            time.sleep(min(longest_sleep, stop - time.time()))
        except KeyboardInterrupt:
            break
    return time.time() - stop


def resource_path(relative_path=""):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        import sys
        base_path = sys._MEIPASS
    except Exception:
        base_path = path.abspath(".")
    return path.abspath(path.join(base_path, relative_path))


def get_mac():
    addr = hex(getnode())[2:]
    return '-'.join(addr[i:i+2] for i in range(0, len(addr), 2))


def get_uuid():
    return str(uuid1())


def get_ip():
    return socket.gethostbyname(socket.gethostname())


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


def base_coder(text):
    if isinstance(text, bytes):
        return text
    return text.encode()


def clean_coder(text):
    return text


def padding_ip(addr, port):
    addr = '.'.join(_.rjust(3, '0') for _ in addr.split('.'))
    return addr + ':' + str(port).rjust(5, '0')


def list_files(addr):
    if path.isfile(addr):
        return [addr]
    files = []
    for subaddr in listdir(addr):
        files.extend(list_files(path.join(addr, subaddr)))
    return files


def analysis_ip(addr):
    addrs = []
    for item in addr.split(";"):
        if len(item) > 0:
            if ":" not in item:
                item += ":8888"
            ip, port = item.split(":")
            addrs.append((ip, int(port)))
    return addrs


def print_qrcode(text):
    try:
        import qrcode
        qr = qrcode.QRCode()
        qr.add_data(text)
        qr.make()
        qr.print_ascii(invert=True)
    except ImportError:
        pass


def read_until(sock, seg, timeout=1.0):
    cache = []
    sock.settimeout(0.01)
    start = time.time()
    for i in range(TCP_BUFF_SIZE):
        try:
            word = sock.recv(1)
        except socket.timeout:
            time.sleep(timeout * 0.001)
            word = b""
        if word == seg or len(word) == 0:
            cache.append(word)
            break
        if time.time() - start > timeout:
            raise TimeoutError
        cache.append(word)
    sock.settimeout(None)
    return b"".join(cache)
