#!/usr/bin/env python3

import sqlite3
from sys import argv, exit
from contextlib import closing

username = argv[1]

with closing(sqlite3.connect('./ctfhost.db')) as db:
    cur = db.cursor()
    cur.execute('SELECT rowid FROM users WHERE username = ?', (username,))
    if len(cur.fetchall()) > 0:
        exit(0)
    exit(1)
