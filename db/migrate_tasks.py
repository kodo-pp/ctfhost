#!/usr/bin/env python3

import json
import os
import sys
import secrets

DEFAULTS = {
    'text': '',
    'title': '',
    'value': 0,
    'labels': [],
    'flags': [],
    'group': 0,
    'order': 0,
    'seed': lambda: secrets.token_hex(8),
}


def migrate_task(task_path):
    print('==> Migrating task "{task}"'.format(task=task_path))
    with open(task_path, 'r') as f:
        raw_read = f.read()
    obj = json.loads(raw_read)
    for k, v in DEFAULTS.items():
        if k not in obj:
            print(
                '  -> Setting attribute {key} to {value}'.format(
                    key = repr(k),
                    value = repr(v) if type(v) is not type(lambda:0) else repr(v())
                )
            )
            obj[k] = v if type(v) is not type(lambda:0) else v()
    written = json.dumps(obj)
    with open(task_path, 'w') as f:
        f.write(written)


def main():
    if '--help' in sys.argv or '-h' in sys.argv:
        print('Usage: {prog} [path/to/task.json] ...'.format(prog=sys.argv[0]))
        print('Add missing attributes to tasks')
        sys.exit(0)
    for task_path in sys.argv[1:]:
        try:
            migrate_task(task_path)
        except BaseException as e:
            print('Error while processing task "{task}": {err}'.format(task=task_path, err=repr(e)))
            sys.exit(1)


if __name__ == '__main__':
    main()
