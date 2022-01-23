from ..crypto import md5_encode

class IDCard:

    __slot__ = ['info']
    
    def __init__(self, uuid, name, mac, crypto, sign):
        src_code = u"".join(map(str, (uuid, name, mac, crypto, sign))).encode()
        self.info = {'uuid': uuid,     # unique id of the current Thread
                     'name': name,     # Who am I
                     'mac': mac,       # MAC address of the current hardware
                     'crypto': crypto, # whether crypto data or not
                     'sign': sign,     # whether sign the document or not
                     'code': md5_encode(src_code)}

    def __repr__(self):
        return str(self.info)
        
    def __getattr__(self, key):
        return self.info[key]

    def __getstate__(self):
        return self.info

    def __setstate__(self, pkl):
        self.info = pkl
        
