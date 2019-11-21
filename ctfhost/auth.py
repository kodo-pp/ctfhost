# -*- coding: utf-8 -*-

import copy
import hashlib
import json
import os
import re
import secrets
import sqlite3
import time
from contextlib import closing

from loguru import logger

from .api import api, GUEST, USER, ADMIN, ApiArgumentError
from .configuration import configuration
from .localization import lc


class TeamNotFoundError(Exception):
    def __str__(self):
        return 'err_team_not_found'


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


class RegValidationFailedError(BaseRegistrationError):
    def __init__(self):
        self.text = 'reg_validation_failed'


class SessionCache:
    def __init__(self):
        self.cache = {}

    def add(self, session):
        self.cache[session.id] = session

    def remove(self, session_id):
        del self.cache[session_id]

    def remove_for(self, username):
        for k, v in copy.deepcopy(self.cache).items():
            if v.username == username:
                del self.cache[k]

    def get(self, session_id):
        if session_id not in self.cache:
            return None
        if self.cache[session_id].expires_at <= time.time():
            self.cache.pop(session_id)
            return None
        return self.cache[session_id]

    def maybe_set_admin(self, username, value):
        for k, v in self.cache.items():
            if v.username == username:
                v.is_admin = value


def hash_session_id(session_id):
    return apply_secure_hash(session_id.encode())


def hash_password(password):
    return apply_secure_hash(password.encode())


def apply_secure_hash(data):
    return configuration['secure_hash_function'](data).hexdigest()


def load_session(session_id):
    if session_id is None:
        return None
    cached_session = session_cache.get(session_id)
    if cached_session is not None:
        return cached_session

    session_id_hash = hash_session_id(session_id)

    with closing(sqlite3.connect(configuration['db_path'])) as db:
        cur = db.cursor()
        cur.execute(
            'SELECT username, expires FROM sessions WHERE expires > ? AND session_id_hash = ? LIMIT 1',
            (int(time.time()), session_id_hash)
        )

        ls = cur.fetchone()
        if ls is None:
            return None
        (username, session_expires_at) = ls
        if session_expires_at is None:
            return None
        else:
            cur.execute('SELECT is_admin FROM users WHERE username = ? LIMIT 1', (username,))
            is_admin = bool(cur.fetchone()[0])
            sess = Session(session_id, username, session_expires_at, is_admin)
            session_cache.add(sess)
            return sess


def logout(session_id):
    logger.info('Deleting session {}'.format(session_id))
    session_cache.remove(session_id)
    session_id_hash = hash_session_id(session_id)
    with closing(sqlite3.connect(configuration['db_path'])) as db:
        cur = db.cursor()
        cur.execute('DELETE FROM sessions WHERE session_id_hash = ?', (session_id_hash,))
        db.commit()


def get_user_info(username):
    with closing(sqlite3.connect(configuration['db_path'])) as db:
        cur = db.cursor()
        cur.execute('SELECT full_name, email, is_admin FROM users WHERE username = ? LIMIT 1', (username,))
        full_name, email, is_admin = cur.fetchone()
        return {
            'full_name': full_name,
            'email': email,
            'is_admin': bool(is_admin),
        }


def create_session(username):
    session_id = secrets.token_hex(32)
    session_id_hash = hash_session_id(session_id)
    expires_at = int(time.time()) + configuration['session_duration']
    with closing(sqlite3.connect(configuration['db_path'])) as db:
        cur = db.cursor()
        cur.execute('DELETE FROM sessions WHERE expires < ?', (int(time.time()),))
        cur.execute('INSERT INTO sessions VALUES (?, ?, ?)', (session_id_hash, username, expires_at))
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
    password_hash = hash_password(password)
    with closing(sqlite3.connect(configuration['db_path'])) as db:
        cur = db.cursor()
        cur.execute(
            'SELECT rowid FROM users WHERE username = ? AND password_hash = ? LIMIT 1',
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


def validate_user_creds(username, disp_name, email):
    if not re.match(r'^[a-zA-Z0-9_.+-]{1,100}$', username):
        return False
    if len(disp_name.encode('utf-8')) >= 1000:
        return False
    if len(email.encode('utf-8')) >= 1000:
        return False
    return True


def register_user(username, password, disp_name, email=None, is_admin=False):
    if not validate_user_creds(username=username, disp_name=disp_name, email=email):
        raise RegValidationFailedError()
    if email == '':
        email = None
    password_hash = hash_password(password)
    token_seed = secrets.token_hex(16)
    with closing(sqlite3.connect(configuration['db_path'])) as db:
        cur = db.cursor()
        cur.execute(
            'SELECT rowid FROM users WHERE username = ? LIMIT 1',
            (username,)
        )
        if len(cur.fetchall()) != 0:
            logger.error('Attempted to register already registered user: "{}"'.format(username))
            raise BaseRegistrationError()
        logger.info('Registering user "{}"'.format(username))
        cur.execute(
            'INSERT INTO users VALUES (?, ?, ?, ?, ?, ?)',
            (username, password_hash, disp_name, email, is_admin, token_seed)
        )
        db.commit()


def verify_password(user, passwd):
    password_hash = hash_password(passwd)
    with closing(sqlite3.connect(configuration['db_path'])) as db:
        cur = db.cursor()
        cur.execute(
            'SELECT rowid FROM users WHERE username = ? AND password_hash = ? LIMIT 1',
            (user, password_hash)
        )
        return len(cur.fetchall()) > 0


def update_password(user, passwd):
    logger.info(
        'Updating password for user {}: {}',
        user,
        '<hidden>' if configuration['hide_password_in_logs'] else passwd
    )
    password_hash = hash_password(passwd)
    with closing(sqlite3.connect(configuration['db_path'])) as db:
        cur = db.cursor()
        cur.execute('UPDATE users SET password_hash = ? WHERE username = ?', (password_hash, user))
        db.commit()


def team_exists(team_name):
    with closing(sqlite3.connect(configuration['db_path'])) as db:
        cur = db.cursor()
        cur.execute('SELECT rowid FROM users WHERE username = ? LIMIT 1', (team_name,))
        return len(cur.fetchall()) > 0


def logout_team(team_name):
    if not team_exists(team_name):
        raise TeamNotFoundError()
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
    if not team_exists(team_name):
        raise TeamNotFoundError()
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


def set_admin(username, value):
    session_cache.maybe_set_admin(username, value)
    with closing(sqlite3.connect(configuration['db_path'])) as db:
        cur = db.cursor()
        cur.execute('UPDATE users SET is_admin = ? WHERE username = ?', (value, username))
        db.commit()


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


def api_set_admin(api, sess, args):
    http = args['http_handler']
    request = json.loads(http.request.body)
    team_name = request['team_name']
    value     = request['value']

    if type(value) is not bool:
        raise Exception(
            lc.get('api_invalid_data_type').format(
                expected = lc.get('bool'),
                param    = 'value',
            )
        )

    set_admin(team_name, value)
    http.write(json.dumps({'success': True}))


api.add('change_password', api_change_password, access_level=USER)
api.add('logout_team',     api_logout_team,     access_level=ADMIN)
api.add('delete_team',     api_delete_team,     access_level=ADMIN)
api.add('set_admin',       api_set_admin,       access_level=ADMIN)

session_cache = SessionCache()
