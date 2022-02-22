from os import path
from hashlib import md5

from .constant import IV, BLOCK_SIZE, DISK_BUFF_SIZE

try:
    try:
        from Crypto.Cipher import AES
        from Crypto.Util.Padding import pad, unpad
    except ImportError:
        from crypto.Cipher import AES
        from crypto.Util.Padding import pad, unpad
    USE_CRYPTO = True
except ImportError:
    USE_CRYPTO = False
    import warnings
    warnings.warn("Crypto is not available, we cannot your data privacy!")


__all__ = ['file_md5', 'AESCoder', 'MD5Coder']



def file_md5(fpath, breakpoint=0):
    coder = md5()
    total_size = 0
    if breakpoint <= 0:
        breakpoint = float("inf")  
    with open(fpath, 'rb') as file:
        while True:
            row = file.read(DISK_BUFF_SIZE)
            total_size += len(row)
            if total_size >= breakpoint:
                coder.update(row[:breakpoint - total_size])
                break
            elif len(row) == 0:
                break
            coder.update(row)
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


if __name__ == '__main__':
    aes_coder = AESCoder(passwd=b"mypasswod")
    md5_coder = MD5Coder(passwd=b"mypasswd")
    data = b'{"uuid": "50bebb1a-ca04-11ea-9ae7-00e04c360011", "name": "JacksonWoo", "mac": "e0-4c-36-00-11", "crypto": true, "sign": true, "code": "a846c719a5ad6adc3b3d2fe89f3070ab"}'
    assert md5_coder.decrypt(aes_coder.decrypt(aes_coder.encrypt(md5_coder.encrypt(data)))) == data
    
    data = b'This is a  sentence of test message'
    assert md5_coder.decrypt(aes_coder.decrypt(aes_coder.encrypt(md5_coder.encrypt(data)))) == data

    
