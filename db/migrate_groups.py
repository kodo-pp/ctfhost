#!/usr/bin/env python3

import json
import os
import sys
import secrets

DEFAULTS = {
    'name':   'Unnamed group',
    'parent': 0,
    'seed': lambda: secrets.token_hex(8),
}


def migrate_group(group_path):
    print('==> Migrating group "{group}"'.format(group=group_path))
    with open(group_path, 'r') as f:
        raw_read = f.read()
    obj = json.loads(raw_read)
    for k, v in DEFAULTS.items():
        if k not in obj:
            new_value = v if type(v) is not type(lambda:0) else v()
            print(
                '  -> Setting attribute {key} to {value}'.format(
                    key = repr(k),
                    value = repr(new_value)
                )
            )
            obj[k] = new_value
    written = json.dumps(obj)
    with open(group_path, 'w') as f:
        f.write(written)


def main():
    if '--help' in sys.argv or '-h' in sys.argv:
        print('Usage: {prog} [path/to/group.json] ...'.format(prog=sys.argv[0]))
        print('Add missing attributes to groups')
        sys.exit(0)
    for group_path in sys.argv[1:]:
        try:
            migrate_group(group_path)
        except BaseException as e:
            print('Error while processing group "{group}": {err}'.format(group=group_path, err=repr(e)))
            sys.exit(1)


if __name__ == '__main__':
    main()
