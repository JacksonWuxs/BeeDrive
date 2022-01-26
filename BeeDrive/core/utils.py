import time

from socket import socket, AF_INET, SOCK_STREAM, SOL_SOCKET, SO_REUSEADDR, SO_KEEPALIVE
from uuid import getnode, uuid1
from os import path, listdir


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


def build_connect(host, port):
    conn = socket(AF_INET, SOCK_STREAM)
    conn.setsockopt(SOL_SOCKET, SO_REUSEADDR, True)
    conn.setsockopt(SOL_SOCKET, SO_KEEPALIVE, True)
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
