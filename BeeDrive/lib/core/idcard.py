
from .utils import get_uuid, get_mac
from ..encrypt import md5_encode


class IDCard:

    __slot__ = ['info']
    
    def __init__(self, uuid, mac, encrypt):
        src_code = u"".join(map(str, (uuid, mac, encrypt))).encode()
        self.info = {'uuid': uuid,     # unique id of the current Thread
                     'mac': mac,       # MAC address of the current hardware
                     'encrypt': encrypt,
                     'code': md5_encode(src_code)}

    def __repr__(self):
        return str(self.info)
        
    def __getattr__(self, key):
        return self.info[key]

    def __getstate__(self):
        return self.info

    def __setstate__(self, pkl):
        self.info = pkl

    @classmethod
    def create(cls, encrypt):
        return cls(get_uuid(), get_mac(), encrypt)
        
