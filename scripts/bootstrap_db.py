#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
from sys import argv, path
from os import urandom, access, R_OK, _exit as exit, rename
from os.path import realpath
from base64 import b64encode
from secrets import token_hex

path.insert(0, realpath('.'))

from configuration import configuration


db_path = configuration['db_path']
hash_function = configuration['secure_hash_function']
sql_script_path = 'scripts/bootstrap.sql'
password_raw_length = 12

def main():
    if '--help' in argv:
        print('bootstrap_db.py: bootstrap SQLite3 database for CTFHost')
        exit(0)

    if access(db_path, R_OK):
        print('Old CTFHost database found. Your actions?')
        print('  1) Remove it (with backup)')
        print('  2) Abort')
        print('  3) Ignore it (not recommended)')
        n = int(input('Enter selected number: '))
        if n not in [1, 2, 3]:
            print('Error: invalid number selected: {}'.format(n))
            print('Aborting')
            exit(1)
        elif n == 1:
            print('Renaming "{}" -> "{}.backup"'.format(db_path, db_path))
            rename(db_path, db_path + '.backup')
        elif n == 2:
            print('Aborting')
            exit(1)
        elif n == 3:
            pass

    print('Reading bootstrap script')
    with open(sql_script_path) as f:
        sql = f.read()

    print('Generating random password')
    password_raw = urandom(password_raw_length)
    password = b64encode(password_raw).decode()
    print('Your CTFHost root password is "{}". Keep it private!'.format(password))
    password_hash = hash_function(password.encode()).hexdigest()

    token_seed = token_hex(16)
    sql = sql.replace('@@_PASSWORD_HASH_@@', password_hash).replace('@@_TOKEN_SEED_@@', token_seed)

    print('Creating database')
    db = sqlite3.connect(db_path)
    cur = db.cursor()
    cur.executescript(sql)
    db.commit()
    db.close()
    print('Done')

if __name__ == '__main__':
    main()
