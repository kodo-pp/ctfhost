# -*- coding: utf-8 -*-

import sqlite3
import hashlib
import time
import os
import json
import secrets
from contextlib import closing

from loguru import logger

from configuration import configuration
from localization import lc
from api import api, GUEST, USER, ADMIN, ApiArgumentError

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

    def remove(self, session_id):
        del self.cache[session_id]

    def remove_for(self, username):
        for k, v in self.cache.items():
            if v.username == username:
                del self.cache[k]

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
    session_cache.remove(session_id)


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
    token_seed = secrets.token_hex(16)
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
            'INSERT INTO users VALUES (?, ?, ?, ?, 0, ?)',
            (username, password_hash, disp_name, email, token_seed)
        )
        db.commit()


def verify_password(user, passwd):
    password_hash = hashlib.sha512(passwd.encode()).hexdigest()
    with closing(sqlite3.connect(configuration['db_path'])) as db:
        cur = db.cursor()
        cur.execute('SELECT rowid FROM users WHERE username = ? AND password_hash = ?', (user, password_hash))
        return len(cur.fetchall()) > 0


def update_password(user, passwd):
    logger.info(
        'Updating password for user {}: {}',
        user,
        '<hidden>' if configuration['hide_password_in_logs'] else passwd
    )
    password_hash = hashlib.sha512(passwd.encode()).hexdigest()
    with closing(sqlite3.connect(configuration['db_path'])) as db:
        cur = db.cursor()
        cur.execute('UPDATE users SET password_hash = ? WHERE username = ?', (password_hash, user))
        db.commit()


def logout_team(team_name):
    logger.info(
        'Terminating all session of team {}',
        team_name,
    )
    with closing(sqlite3.connect(configuration['db_path'])) as db:
        cur = db.cursor()
        cur.execute('DELETE FROM sessions WHERE username = ?', (team_name,))
        db.commit()
    session_cache.remove_for(team_name)


def delete_team(team_name):
    logger.warning(
        'DELETING team {}',
        team_name,
    )
    with closing(sqlite3.connect(configuration['db_path'])) as db:
        cur = db.cursor()
        cur.execute('DELETE FROM sessions WHERE username = ?', (team_name,))
        cur.execute('DELETE FROM users WHERE username = ?', (team_name,))
        cur.execute('DELETE FROM submissions WHERE team_name = ?', (team_name,))
        cur.execute('DELETE FROM hint_purchases WHERE team_name = ?', (team_name,))
        db.commit()
    session_cache.remove_for(team_name)


def api_change_password(api, sess, args):
    http = args['http_handler']
    request = json.loads(http.request.body)
    team_name = request['team_name']
    old_password = request['old_password']
    new_password = request['new_password']

    if type(old_password) is not str:
        raise Exception(
            lc.get('api_invalid_data_type').format(
                expected=lc.get('str'),
                param='old_password',
            )
        )
    if type(new_password) is not str:
        raise Exception(
            lc.get('api_invalid_data_type').format(
                expected=lc.get('str'),
                param='new_password',
            )
        )

    if sess.is_admin:
        update_password(team_name, new_password)
        http.write(json.dumps({'success': True}))
        return
    elif team_name == sess.username and verify_password(team_name, old_password):
        update_password(team_name, new_password)
        http.write(json.dumps({'success': True}))
        return
    else:
        raise Exception(lc.get('api_call_permission_denied'))


def api_logout_team(api, sess, args):
    http = args['http_handler']
    request = json.loads(http.request.body)
    team_name = request['team_name']

    logout_team(team_name)
    http.write(json.dumps({'success': True}))


def api_delete_team(api, sess, args):
    http = args['http_handler']
    request = json.loads(http.request.body)
    team_name = request['team_name']

    delete_team(team_name)
    http.write(json.dumps({'success': True}))


api.add('change_password', api_change_password, access_level=USER)
api.add('logout_team',     api_logout_team,     access_level=ADMIN)
api.add('delete_team',     api_delete_team,     access_level=ADMIN)

session_cache = SessionCache()
