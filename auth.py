# -*- coding: utf-8 -*-

import sqlite3
import hashlib
import time
import os
from contextlib import closing

from loguru import logger

from configuration import configuration

class Session:
    def __init__(self, id, username, expires_at, is_admin):
        self.id = id
        self.username = username
        self.is_admin = is_admin
        self.expires_at = expires_at

class BaseAuthenticationError(Exception):
    def __init__(self):
        self.text = 'basic_authentication_error'

class AuthenticationError(BaseAuthenticationError):
    def __init__(self):
        self.text = 'invalid_username_or_password'

class BaseRegistrationError(Exception):
    def __init__(self):
        self.text = 'basic_registration_error'


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

        ls = cur.fetchone()
        if ls is None:
            return None
        (username, session_expires_at) = ls
        if session_expires_at is None:
            return None
        else:
            cur.execute('SELECT is_admin FROM users WHERE username = ?', (username,))
            is_admin = bool(cur.fetchone()[0])
            sess = Session(session_id, username, session_expires_at, is_admin)
            session_cache.add(sess)
            return sess


def logout(session_id):
    logger.info('Deleting session {}'.format(session_id))
    with closing(sqlite3.connect(configuration['db_path'])) as db:
        cur = db.cursor()
        cur.execute('DELETE FROM sessions WHERE session_id = ?', (session_id,))


def get_user_info(username):
    with closing(sqlite3.connect(configuration['db_path'])) as db:
        cur = db.cursor()
        cur.execute('SELECT full_name, email, is_admin FROM users WHERE username = ?', (username,))
        full_name, email, is_admin = cur.fetchone()
        return {
            'full_name': full_name,
            'email': email,
            'is_admin': bool(is_admin),
        }


def create_session(username):
    session_id = hashlib.sha512(os.urandom(16)).hexdigest()
    expires_at = int(time.time()) + configuration['session_duration']
    with closing(sqlite3.connect(configuration['db_path'])) as db:
        cur = db.cursor()
        cur.execute('DELETE FROM sessions WHERE expires < ?', (int(time.time()),))
        cur.execute('SELECT rowid FROM sessions WHERE username = ?', (username,))
        if len(cur.fetchall()) > 0:
            logger.info('Session for user "{}" already exists, deleting it'.format(username))
            cur.execute('DELETE FROM sessions WHERE username = ?', (username,))
        cur.execute('INSERT INTO sessions VALUES (?, ?, ?)', (session_id, username, expires_at))
        db.commit()
    is_admin = get_user_info(username)['is_admin']
    sess = Session(session_id, username, expires_at, is_admin)
    session_cache.add(sess)
    return sess


def get_user_list():
    with closing(sqlite3.connect(configuration['db_path'])) as db:
        cur = db.cursor()
        cur.execute('SELECT username FROM users')
        ls = cur.fetchall()
    for i in ls:
        yield i[0]


def authenticate_user(username, password):
    password_hash = hashlib.sha512(password.encode()).hexdigest()
    with closing(sqlite3.connect(configuration['db_path'])) as db:
        cur = db.cursor()
        cur.execute(
            'SELECT rowid FROM users WHERE username = ? AND password_hash = ?',
            (username, password_hash)
        )
        if len(cur.fetchall()) == 0:
            logger.info('Failed login attempt: username "{}", password "{}"'.format(
                username,
                '<hidden>' if configuration['hide_password_in_logs'] else password)
            )
            raise AuthenticationError()
        else:
            logger.info('User "{}" logged in'.format(username))
            return create_session(username)


def register_user(username, password, disp_name=None, email=None):
    if disp_name == '':
        disp_name = None
    if email == '':
        email = None
    password_hash = hashlib.sha512(password.encode()).hexdigest()
    with closing(sqlite3.connect(configuration['db_path'])) as db:
        cur = db.cursor()
        cur.execute(
            'SELECT rowid FROM users WHERE username = ?',
            (username,)
        )
        if len(cur.fetchall()) != 0:
            logger.error('Attempted to register already registered user: "{}"'.format(username))
            raise BaseRegistrationError()
        logger.info('Registering user "{}"'.format(username))
        cur.execute(
            'INSERT INTO users VALUES (?, ?, ?, ?, 0)',
            (username, password_hash, disp_name, email)
        )
        db.commit()

session_cache = SessionCache()
