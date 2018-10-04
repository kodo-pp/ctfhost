#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import hashlib
import os
import time

import tornado.ioloop
import tornado.web

from localization import Localization
from template import render_template

lc = None


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.write(render_template('index.html', lc, user_signed_in=False))

class LoginHandler(tornado.web.RequestHandler):
    def get(self):
        self.write(render_template('login.html', lc))

class AuthHandler(tornado.web.RequestHandler):
    def post(self):
        username = self.get_argument('username', None)
        password = self.get_argument('password', None)
        if username is None:
            self.write(render_template('auth_error.html', lc, error=lc.get('no_username')))
            return
        if password is None:
            self.write(render_template('auth_error.html', lc, error=lc.get('no_passord')))
            return
        if not authenticate_user(username, password):
            self.write(render_template('auth_error.html', lc, error=lc.get('invalid_username_or_password')))
        else:
            self.redirect('/', permanent=True)

class FaviconHandler(tornado.web.RequestHandler):
    def get(self):
        self.redirect('/static/favicon.png', permanent=True)

def create_session(username):
    session_id = hashlib.sha512(os.urandom(16)).hexdigest()
    expires_at = int(time.time()) + 86400
    db = sqlite3.connect('db/users.db')
    cur = db.cursor()
    cur.execute('INSERT INTO sessions VALUES (NULL, ?, ?, ?)', (session_id, username, expires_at))
    db.commit()
    db.close()

def authenticate_user(username, password):
    auth_db = {
        'user': 'pass',
        'root': '12345',
    }
    if username in auth_db and password == auth_db[username]:
        return create_session(username)
    else:
        return None

def make_app():
    return tornado.web.Application([
        (r'/', MainHandler),
        (r'/login', LoginHandler),
        (r'/auth', AuthHandler),
        (r'/', LoginHandler),
        (r'/favicon.ico', FaviconHandler),
        (r'/static/(.*)', tornado.web.StaticFileHandler, {'path': './static'})
    ])


def main():
    global lc
    lc = Localization()
    lc.select_languages(['ru_RU', 'en_US'])

    app = make_app()
    app.listen(8888)
    tornado.ioloop.IOLoop.current().start()


if __name__ == "__main__":
    main()
