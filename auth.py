# -*- coding: utf-8 -*-

import sqlite3
import hashlib
import time
import os
from contextlib import closing

from configuration import configuration

class Session:
    def __init__(self, id, username, expires_at):
        self.id = id
        self.username = username
        self.expires_at = expires_at

class BaseAuthenticationError(Exception):
    def __init__(self):
        self.text = 'basic_authentication_error'

class AuthenticationError(BaseAuthenticationError):
    def __init__(self):
        self.text = 'invalid_username_or_password'

class SessionAlreadyExists(BaseAuthenticationError):
    def __init__(self):
        self.text = 'session_already_exists'

def validate_session(session_id, username):
    with closing(sqlite3.connect(configuration['db_path'])) as db:
        cur = db.cursor()
        cur.execute(
            'SELECT expires FROM sessions WHERE session_id = ? AND username = ? AND expires > ?',
            (session_id, username, int(time.time()))
        )
        result = cur.fetchall()
        return len(result) > 0, result

def get_session(session_id, username):
    ok, expires = validate_session(session_id, username)
    return Session(session_id, username, expires) if ok else None

def create_session(username):
    session_id = hashlib.sha512(os.urandom(16)).hexdigest()
    expires_at = int(time.time()) + configuration['session_duration']
    with closing(sqlite3.connect(configuration['db_path'])) as db:
        cur = db.cursor()
        cur.execute('DELETE FROM sessions WHERE expires < ?', (int(time.time(),)))
        cur.execute('INSERT INTO sessions VALUES (?, ?, ?)', (session_id, username, expires_at))
        db.commit()
    return Session(session_id, username, expires_at)

def authenticate_user(username, password):
    password_hash = hashlib.sha512(password.encode()).hexdigest()
    with closing(sqlite3.connect(configuration['db_path'])) as db:
        cur = db.cursor()
        cur.execute(
            'SELECT rowid FROM users WHERE username = ? AND password_hash = ?',
            (username, password_hash)
        )
        if len(cur.fetchall()) == 0:
            print('Failed login attempt: username "{}", password "{}"'.format(
                username,
                '<hidden>' if configuration['hide_password_in_logs'] else password)
            )
            raise AuthenticationError()
        else:
            print('User "{}" logged in'.format(username))
            return create_session(username)
