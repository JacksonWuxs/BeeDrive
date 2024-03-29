import time
import socket
import random
from uuid import getnode, uuid1
from os import path, listdir

from .constant import TCP_BUFF_SIZE
from .core.utils import *


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


def get_ip():
    return socket.gethostbyname(socket.gethostname())


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



