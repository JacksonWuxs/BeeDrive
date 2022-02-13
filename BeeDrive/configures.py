import sys
import os
import pickle

from .core.utils import clean_path
from .core.logger import callback_info


def init_config_path(service=None):
    is_window = sys.platform.startswith("win")
    path = clean_path(os.path.join(os.environ["APPDATA"], r"/BeeDrive"))
    if not os.path.exists(path):
        os.makedirs(path)
    if service:
        return clean_path("%s/%s.bee" % (path, service))
    return path


def save_config(service, **config):
    path = init_config_path(service)
    pickle.dump(config, open(path, mode="wb"))
    callback_info("Update BeeDrive-%s default config at %s" % (service, path))
    return config


def load_config(service):
    path = init_config_path(service)
    if os.path.exists(path):
        return pickle.load(open(path, 'rb'))
    return {}
