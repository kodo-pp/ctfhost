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

class SessionCache:
    def __init__(self):
        self.cache = {}

    def add(self, session):
        self.cache[session.id] = session

    def get(self, session_id):
        if session_id not in self.cache:
            return None
        if self.cache[session_id].expires_at <= time.time():
            self.cache.pop(session_id)
            return None
        return self.cache[session_id]

def load_session(session_id):
    if session_id is None:
        return None
    cached_session = session_cache.get(session_id)
    if cached_session is not None:
        return cached_session

    with closing(sqlite3.connect(configuration['db_path'])) as db:
        cur = db.cursor()
        cur.execute(
            'SELECT username, expires FROM sessions WHERE expires > ? AND session_id = ?',
            (int(time.time()), session_id)
        )

        (username, session_expires_at) = cur.fetchone()
        if session_expires_at is None:
            return None
        else:
            sess = Session(session_id, username, session_expires_at)
            session_cache.add(sess)
            return sess

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
        cur.execute('SELECT rowid FROM sessions WHERE username = ?', (username,))
        if len(cur.fetchall()) > 0:
            print('Session for user "{}" already exists'.format(username))
            print('Deleting it')
            cur.execute('DELETE FROM sessions WHERE username = ?', (username,))
        cur.execute('INSERT INTO sessions VALUES (?, ?, ?)', (session_id, username, expires_at))
        db.commit()
    sess = Session(session_id, username, expires_at)
    session_cache.add(sess)
    return sess

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

session_cache = SessionCache()
