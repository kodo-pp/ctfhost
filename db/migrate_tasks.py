#!/usr/bin/env python3

import json
import os
import sys
import secrets
import re
import traceback as tb

DEFAULTS = {
    'text': '',
    'title': 'Unnamed task',
    'value': 0,
    'labels': [],
    'flags': [],
    'group': 0,
    'order': 0,
    'seed': lambda: secrets.token_hex(8),
    'hints': [],
}

HINT_DEFAULTS = {
    'value': 10,
    'text': 'Hint text',
    'hexid': lambda: secrets.token_hex(16),
}


def migrate_task(task_path):
    print('==> Migrating task "{task}"'.format(task=task_path))
    with open(task_path, 'r') as f:
        raw_read = f.read()
    obj = json.loads(raw_read)
    for k, v in DEFAULTS.items():
        if k not in obj:
            new_value = v if type(v) is not type(lambda:0) else v()
            print(
                '  -> Setting attribute {key} to {value}'.format(
                    key = repr(k),
                    value = repr(new_value),
                )
            )
            obj[k] = new_value

    print('  -> Migrating hints')
    hints_to_drop = []
    for no, hint in enumerate(obj['hints']):
        if type(hint) is not dict:
            print(
                '\x1b[33m  ---> Warning: dropping hint #{number}'.format(
                    number = no,
                )
            )
            hints_to_drop.append(hint)
            continue
        for k, v in HINT_DEFAULTS.items():
            if k not in hint or (k == 'hexid' and re.match(r'^[0-9a-fA-F]{32}$', hint[k]) is None):
                new_value = v if type(v) is not type(lambda:0) else v()
                print(
                    '  ---> Setting attribute {key} to {value}'.format(
                        key = repr(k),
                        value = repr(new_value),
                    )
                )
                hint[k] = new_value
    for hint in hints_to_drop:
        obj['hints'].pop(hint)
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
            tb.print_exc()
            sys.exit(1)


if __name__ == '__main__':
    main()
