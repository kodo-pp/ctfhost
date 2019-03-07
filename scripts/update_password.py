#!/usr/bin/env python3

import sqlite3
import os
from sys import argv, exit, stderr, path
from contextlib import closing
from hashlib import sha512
from getpass import getpass

path.insert(0, os.path.realpath('.'))

from configuration import configuration


usage_str='''Usage: update_password.py <username>
Update CTFHost password for specified user'''


try:
    username = argv[1]
except IndexError:
    print(usage_str, file=stderr)
    exit(1)


with closing(sqlite3.connect(configuration['db_path'])) as db:
    cur = db.cursor()
    cur.execute('SELECT rowid FROM users WHERE username = ? LIMIT 1', (username,))
    if len(cur.fetchall()) == 0:
        print('This user does not exist', file=stderr)
        exit(1)


password = getpass(prompt='New password: ')
password_c = getpass(prompt='Confirm new password: ')
if password != password_c:
    print('Password and its confirmation do not match', file=stderr)
    exit(1)

password_hash = sha512(password.encode()).hexdigest()

with closing(sqlite3.connect(configuration['db_path'])) as db:
    cur = db.cursor()
    cur.execute('UPDATE users SET password_hash=? WHERE username = ?', (password_hash, username))
    db.commit()

print('Done', file=stderr)
