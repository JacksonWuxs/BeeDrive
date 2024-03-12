import hashlib
import string
import random

from .constant import IV, BLOCK_SIZE


try:
    try:
        from Crypto.Cipher import AES
        from Crypto.Util.Padding import pad, unpad
    except Exception:
        from crypto.Cipher import AES
        from crypto.Util.Padding import pad, unpad
    SUPPORT_AES = True
except Exception:
    SUPPORT_AES = False
    import warnings
    warnings.warn("Crypto is not available, we cannot keep your data privacy!")


__all__ = ['file_md5', 'AESCoder', 'MD5Coder']


CHARS = string.digits + string.punctuation + string.ascii_letters
def create_salt(size=8):
    assert isinstance(size, int) and size > 0
    return random.choices(CHARS, k=size)


def file_md5(fpath, breakpoint=None):
    coder = hashlib.md5()
    total_size = 0
    if breakpoint is None:
        breakpoint = float("inf")
    with open(fpath, 'rb') as file:
        for row in file:
            total_size += len(row)
            if total_size >= breakpoint:
                coder.update(row[:breakpoint - total_size])
                break
            coder.update(row)
    return coder.hexdigest()


def md5_encode(text):
    return hashlib.md5(text).hexdigest()


def sha256_encode(text):
    if isinstance(text, str):
        text = text.encode("utf8")
    sha = hashlib.sha256()
    sha.update(text)
    return sha.hexdigest()


class MD5Coder:
    def __init__(self, passwd=b"", salt=b""):
        if isinstance(passwd, str):
            passwd = passwd.encode("utf8")
        if isinstance(salt, str):
            salt = salt.encode("utf8")
        self.token = salt + passwd

    def encrypt(self, text):
        return md5_encode(self.token + text).encode() + text


    def decrypt(self, text):
        code, data = text[:32], text[32:]
        verify_code = md5_encode(self.token + data)
        if code == verify_code or code == verify_code.encode():
            return data
        raise RuntimeError('Tampered Data: %s' % data)
        

class AESCoder:
    def __init__(self, passwd):
        self.blocksize = BLOCK_SIZE
        if isinstance(passwd, str):
            passwd = passwd.encode("utf8")
        assert len(passwd) <= 16, "Length of password must be smaller than 16"
        self.passwd = b" " * (16 - len(passwd)) + passwd

    def encrypt(self, text):
        return AES.new(self.passwd, AES.MODE_CBC, IV).encrypt(pad(text, self.blocksize))

    def decrypt(self, text):
        return unpad(AES.new(self.passwd, AES.MODE_CBC, IV).decrypt(text), self.blocksize)

