#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import hashlib
import os
import time
import json
from traceback import print_exc

import tornado.ioloop
import tornado.web
from loguru import logger

from localization import Localization
from configuration import configuration
from template import render_template
from api import api
import auth
import tasks

lc = None


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.write(render_template('index.html', lc, session=auth.load_session(self.get_cookie('session_id'))))

class ApiHandler(tornado.web.RequestHandler):
    def post(self, *a):
        path = self.request.path
        path_parts = list(filter(lambda s: s != '', path.split('/')))
        if len(path_parts) != 2:
            self.write(json.dumps({'success': False, 'error_message': lc.get('invalid_api_call')}))
            return
        api_function = path_parts[-1]
        try:
            api.handle(api_function, args={'http_handler': self})
        except KeyError:
            self.write(json.dumps({'success': False, 'error_message': lc.get('no_such_api_function')}))
            return
        except BaseException as e:
            self.write(json.dumps({'success': False, 'error_message': lc.get(str(e))}))
            logger.error('Exception occured while serving an API call: {}', str(e))
            print_exc(e)
            return

    def get(self, *a):
        self.post(*a)

class AdminHandler(tornado.web.RequestHandler):
    def get(self):
        session = auth.load_session(self.get_cookie('session_id'))
        if session is None or not session.is_admin:
            self.write(render_template('admin_error.html', lc, error=lc.get('not_admin')))
            return
        self.write(render_template('admin.html', lc, session=session, tasks=tasks))

class LoginHandler(tornado.web.RequestHandler):
    def get(self):
        session_id = self.get_cookie('session_id')
        if auth.load_session(session_id) is not None:
            self.redirect('/', permanent=True)
            return
        self.write(render_template('login.html', lc))

class RegisterHandler(tornado.web.RequestHandler):
    def get(self):
        session_id = self.get_cookie('session_id')
        if auth.load_session(session_id) is not None:
            self.redirect('/', permanent=True)
            return
        self.write(render_template('register.html', lc))

class LogoutHandler(tornado.web.RequestHandler):
    def get(self):
        session_id = self.get_cookie('session_id')
        if auth.load_session(session_id) is None:
            self.write(render_template('auth_error.html', lc, error=lc.get('logout_no_session')))
            return
        auth.logout(session_id)
        self.clear_cookie('session_id')
        self.redirect('/')

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
        self.redirect('/', permanent=True)

class RegHandler(tornado.web.RequestHandler):
    def post(self):
        username = self.get_argument('username', None)
        password = self.get_argument('password', None)
        password_c = self.get_argument('password-c', None)
        disp_name = self.get_argument('disp-name', None)
        email = self.get_argument('email', None)
        
        if username is None or username == '':
            self.write(render_template('reg_error.html', lc, error=lc.get('no_username')))
            return
        if password is None or password == '':
            self.write(render_template('reg_error.html', lc, error=lc.get('no_password')))
            return
        if password != password_c:
            self.write(render_template('reg_error.html', lc, error=lc.get('password_c_failed')))
            return
        if username in auth.get_user_list():
            self.write(render_template('reg_error.html', lc, error=lc.get('user_already_exists')))
            return

        auth.register_user(username=username, password=password, disp_name=disp_name, email=email)
        self.redirect('/', permanent=True)

class TasksHandler(tornado.web.RequestHandler):
    def get(self):
        session_id = self.get_cookie('session_id')
        session = auth.load_session(session_id)
        if session is None:
            self.redirect('/login')
            return
        task_list = tasks.get_task_list()
        self.write(render_template('tasks.html', lc, session=session, tasks=task_list))

class FaviconHandler(tornado.web.RequestHandler):
    def get(self):
        self.redirect('/static/favicon.png', permanent=True)

def make_app():
    return tornado.web.Application([
        (r'/', MainHandler),
        (r'/admin', AdminHandler),
        (r'/api/(.*)', ApiHandler),
        (r'/login', LoginHandler),
        (r'/signup', RegisterHandler),
        (r'/lout', LogoutHandler), # /logout не работает под firefox за nginx reverse proxy (КАК???)
        (r'/auth', AuthHandler),
        (r'/reg', RegHandler),
        (r'/tasks', TasksHandler),
        (r'/favicon.ico', FaviconHandler),
        (r'/static/(.*)', tornado.web.StaticFileHandler, {'path': './static'})
    ], debug=True)


def main():
    global lc
    lc = Localization()
    lc.select_languages(configuration['lang_list'])
    api.set_locale(lc)

    app = make_app()
    app.listen(8888)
    tornado.ioloop.IOLoop.current().start()


if __name__ == "__main__":
    main()
