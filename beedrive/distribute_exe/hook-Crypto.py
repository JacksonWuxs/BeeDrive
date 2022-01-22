
import os
import glob
 
from PyInstaller.compat import EXTENSION_SUFFIXES
from PyInstaller.utils.hooks import get_module_file_attribute
 
binaries = []
binary_module_names = [
    'Crypto.Math',      # First in the list
    'Crypto.Cipher',
    'Crypto.Util',
    'Crypto.Hash',
    'Crypto.Protocol',
]
 
try:
    for module_name in binary_module_names:
        m_dir = os.path.dirname(get_module_file_attribute(module_name))
        for ext in EXTENSION_SUFFIXES:
            module_bin = glob.glob(os.path.join(m_dir, '_*%s' % ext))
            for f in module_bin:
                binaries.append((f, module_name.replace('.', os.sep)))
except ImportError:
    pass
    # Do nothing for PyCrypto (Crypto.Math does not exist there)

