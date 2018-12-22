#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import hashlib
import os
import time

import tornado.ioloop
import tornado.web

from localization import Localization
from configuration import configuration
from template import render_template
import auth

lc = None


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.write(render_template('index.html', lc, session=auth.load_session(self.get_cookie('session_id'))))

class LoginHandler(tornado.web.RequestHandler):
    def get(self):
        session_id = self.get_cookie('session_id')
        if auth.load_session(session_id) is not None:
            self.redirect('/', permanent=True)
            return
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

        try:
            session = auth.authenticate_user(username, password)
        except auth.BaseAuthenticationError as e:
            self.write(render_template('auth_error.html', lc, error=lc.get(e.text)))
            return
        self.set_cookie('session_id', session.id, expires=session.expires_at)

class FaviconHandler(tornado.web.RequestHandler):
    def get(self):
        self.redirect('/static/favicon.png', permanent=True)

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
