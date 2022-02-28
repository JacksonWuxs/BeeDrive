import sys
import os
import pickle

from .lib.utils import clean_path
from .lib.logger import callback


def init_config_path(service=None):
    path = os.environ.get("APPDATA", "./")
    if len(path) == 0:
        path = "."
    path = clean_path(os.path.join(path, r"/.BeeDriveConfig"))
    if not os.path.exists(path):
        os.makedirs(path)
    if service:
        return clean_path("%s/%s.bee" % (path, service))
    return path


def save_config(service, **config):
    path = init_config_path(service)
    pickle.dump(config, open(path, mode="wb"))
    callback("Update BeeDrive-%s default config at %s" % (service, path))
    return config


def load_config(service):
    path = init_config_path(service)
    if os.path.exists(path):
        return pickle.load(open(path, 'rb'))
    return {}
