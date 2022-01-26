from os import path
from hashlib import md5

from .constant import IV, BLOCK_SIZE


try:
    try:
        from Crypto.Cipher import AES
        from Crypto.Util.Padding import pad, unpad
    except Exception:
        from crypto.Cipher import AES
        from crypto.Util.Padding import pad, unpad
    HAS_AES = True
except Exception:
    HAS_AES = False
    import warnings
    warnings.warn("Crypto is not available, we cannot keep your data privacy!")


__all__ = ['file_md5', 'AESCoder', 'MD5Coder']



def file_md5(fpath, breakpoint=0):
    coder = md5()
    total_size = 0
    with open(fpath, 'rb') as file:
        for row in file:
            if breakpoint > 0 and total_size + len(row) > breakpoint:
                row = row[:breakpoint - (total_size + len(row))]
                
            coder.update(row)
            total_size += len(row)
            if total_size >= breakpoint:
                break
    return coder.hexdigest()


def md5_encode(text):
    coder = md5()
    coder.update(text)
    return coder.hexdigest()


class MD5Coder:
    def __init__(self, passwd=b""):
        if isinstance(passwd, str):
            passwd = passwd.encode("utf8")
        self.passwd = passwd

    def encrypt(self, text):
        return md5_encode(self.passwd + text).encode() + text


    def decrypt(self, text):
        code, data = text[:32], text[32:]
        verify_code = md5_encode(self.passwd + data)
        if code == verify_code or code == verify_code.encode():
            return data
        raise RuntimeError('Tampered Information: %s' % data)
        

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

