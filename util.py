import os
import secrets

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
