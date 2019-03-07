import os
import secrets
import importlib
import time

from configuration import configuration

def get_ctfhost_seed():
    path = configuration['ctfhost_seed_path']
    if not os.access(path, os.R_OK):
        seed = secrets.token_hex(16)
        with open(path, 'w') as f:
            f.write(seed)
        return seed
    with open(path) as f:
        return f.read().strip()


def get_current_utc_time():
    return int(time.mktime(time.gmtime()))


def import_file(filename, module_name='imported_file'):
    spec = importlib.util.spec_from_file_location(module_name, filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod 

