import importlib
import os
import secrets
import time

from . import configuration as conf


def get_ctfhost_seed():
    path = conf.configuration['ctfhost_seed_path']
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


def make_hash_function(hash_provider):
    return lambda data: hash_provider(read_global_salt() + data)


def read_global_salt():
    salt_path = conf.configuration['global_salt_path']
    os.makedirs(os.path.dirname(salt_path), exist_ok=True)
    if not os.path.exists(salt_path):
        with open(salt_path, 'wb') as f:
            f.write(make_random_salt())

    with open(salt_path, 'rb') as f:
        return f.read()


def make_random_salt():
    return secrets.token_bytes()
