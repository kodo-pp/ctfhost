#!/usr/bin/env python3

import sqlite3
from sys import argv, exit
from contextlib import closing
from hashlib import sha512

username = argv[1]
password = input()

password_hash = sha512(password.encode()).hexdigest()

with closing(sqlite3.connect('./ctfhost.db')) as db:
    cur = db.cursor()
    cur.execute('UPDATE users SET password_hash=? WHERE username = ?', (password_hash, username))
    db.commit()
