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

import auth
import tasks
import team
import task_gen
import locks
from competition import competition
from localization import Localization, lc
from configuration import configuration
from template import render_template
from api import api, ApiKeyError


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        with locks.global_lock:
            self.write(render_template('index.html', session=auth.load_session(self.get_cookie('session_id'))))


class ApiHandler(tornado.web.RequestHandler):
    def post(self, *a):
        with locks.global_lock:
            session = auth.load_session(self.get_cookie('session_id'))
            path = self.request.path
            path_parts = list(filter(lambda s: s != '', path.split('/')))
            if len(path_parts) != 2:
                self.write(json.dumps({'success': False, 'error_message': lc.get('invalid_api_call')}))
                return
            api_function = path_parts[-1]
            try:
                api.handle(api_function, session=session, args={'http_handler': self})
            except ApiKeyError:
                self.write(json.dumps({'success': False, 'error_message': lc.get('no_such_api_function')}))
                return
            except BaseException as e:
                self.write(json.dumps({'success': False, 'error_message': lc.get(str(e))}))
                logger.error('Exception occured while serving an API call: {}', repr(e))
                print_exc()
                return

    def get(self, *a):
        self.post(*a)


class AdminHandler(tornado.web.RequestHandler):
    def get(self):
        with locks.global_lock:
            session = auth.load_session(self.get_cookie('session_id'))
            submissions = team.get_all_submissions()
            if session is None or not session.is_admin:
                self.write(render_template('admin_error.html', error=lc.get('not_admin')))
                return
            self.write(render_template(
                'admin.html',
                session          = session,
                tasks            = list(tasks.get_task_list()),
                submissions      = list(submissions),
                teams            = list(team.get_all_teams()),
                groups           = dict(tasks.get_group_dict()),
                read_task        = tasks.read_task,
                build_group_path = tasks.build_group_path,
                task_gen         = task_gen,
            ))


class AdminNewTeamHandler(tornado.web.RequestHandler):
    def get(self):
        with locks.global_lock:
            session_id = self.get_cookie('session_id')
            session = auth.load_session(session_id)
            if session is None or not session.is_admin:
                self.write(render_template('admin_error.html', error=lc.get('not_admin')))
                return

            self.write(render_template('admin_new_team.html', session=session))


class GetAttachmentHandler(tornado.web.RequestHandler):
    def get(self, _):
        with locks.global_lock:
            session_id = self.get_cookie('session_id')
            session = auth.load_session(session_id)
            if session is None:
                raise tornado.web.HTTPError(403)

            task_id = self.get_argument('task', None)
            if task_id is None:
                raise tornado.web.HTTPError(418)

            try:
                task_id = int(task_id)
            except (ValueError, TypeError) as e:
                raise tornado.web.HTTPError(404)

            try:
                tasks.read_task(task_id)
            except tasks.TaskNotFoundError:
                raise tornado.web.HTTPError(404)

            filename = self.get_argument('file', None)
            if filename is None:
                raise tornado.web.HTTPError(404)
            
            try:
                filepath = tasks.get_attachment(task_id=task_id, team_name=session.username, filename=filename)
            except tasks.AttachmentNotFoundError:
                raise tornado.web.HTTPError(404)
        # End lock
        with open(filepath, 'rb') as f:
            self.set_header('Content-Type', 'application/octet-stream')
            while True:
                data = f.read(64 * 1024)
                if len(data) == 0:
                    break
                self.write(data)
            self.finish() 


class ChangePasswordHandler(tornado.web.RequestHandler):
    def get(self):
        with locks.global_lock:
            session_id = self.get_cookie('session_id')
            session = auth.load_session(session_id)
            if session is None:
                self.redirect('/login')
                return

            self.write(render_template('change_password.html', session=session))


class ChangePasswordSubmitHandler(tornado.web.RequestHandler):
    def post(self):
        with locks.global_lock:
            session_id = self.get_cookie('session_id')
            session = auth.load_session(session_id)
            if session is None:
                self.redirect('/login')
                return

            old_password = self.get_argument('old_password', None)
            password = self.get_argument('password', None)
            password_c = self.get_argument('password_c', None)
            if old_password is None or old_password == '':
                self.write(
                    render_template(
                        'change_password_error.html',
                        error_message=lc.get('no_old_password'),
                        session=session,
                    )
                )
                return
            if not auth.verify_password(session.username, old_password):
                self.write(
                    render_template(
                        'change_password_error.html',
                        error_message=lc.get('invalid_old_password'),
                        session=session,
                    )
                )
                return
            if password is None or password == '':
                self.write(
                    render_template(
                        'change_password_error.html',
                        error_message=lc.get('no_password'),
                        session=session,
                    )
                )
                return
            if password != password_c:
                self.write(
                    render_template(
                        'change_password_error.html',
                        error_message=lc.get('password_c_failed'),
                        session=session,
                    )
                )
                return
            
            auth.update_password(session.username, password)
            self.write(render_template('change_password_ok.html', session=session))


class EditTeamInfoHandler(tornado.web.RequestHandler):
    def get(self):
        with locks.global_lock:
            session_id = self.get_cookie('session_id')
            session = auth.load_session(session_id)
            current_team = team.read_team(session.username)
            if session is None:
                self.redirect('/login')
                return

            self.write(render_template('edit_team_info.html', session=session, team=current_team))


class EditTeamInfoSubmitHandler(tornado.web.RequestHandler):
    def post(self):
        with locks.global_lock:
            session_id = self.get_cookie('session_id')
            session = auth.load_session(session_id)
            if session is None:
                self.redirect('/login')
                return

            disp_name = self.get_argument('disp_name', None)
            email = self.get_argument('email', None)
            if disp_name is None or disp_name == '':
                self.write(
                    render_template(
                        'edit_team_info_error.html',
                        error_message=lc.get('no_disp_name'),
                        session=session,
                    )
                )
                return
            tm = team.read_team(session.username)
            tm.full_name = disp_name
            tm.email = email if email != '' else None
            team.write_team(tm)
            self.write(render_template('edit_team_info_ok.html', session=session))


class AdminRegHandler(tornado.web.RequestHandler):
    def post(self):
        with locks.global_lock:
            session_id = self.get_cookie('session_id')
            session = auth.load_session(session_id)
            if session is None or not session.is_admin:
                self.write(render_template('admin_error.html', error=lc.get('not_admin')))
                return
            username = self.get_argument('username', None)
            password = self.get_argument('password', None)
            password_c = self.get_argument('password-c', None)
            disp_name = self.get_argument('disp-name', None)
            email = self.get_argument('email', None)
            is_admin = self.get_argument('is_admin', None)

            if is_admin is not None and is_admin not in ['on', 'off']:
                self.write(render_template('reg_error.html', error=lc.get('api_invalid_data_type').format(
                    param = 'is_admin',
                    expected = lc.get('bool'),
                )))
                return
            if is_admin == 'on':
                is_admin = True
            else:
                is_admin = False
                
            
            if username is None or username == '':
                self.write(render_template('reg_error.html', error=lc.get('no_username')))
                return
            if password is None or password == '':
                self.write(render_template('reg_error.html', error=lc.get('no_password')))
                return
            if disp_name is None or disp_name == '':
                self.write(render_template('reg_error.html', error=lc.get('no_disp_name')))
                return
            if password != password_c:
                self.write(render_template('reg_error.html', error=lc.get('password_c_failed')))
                return
            if username in auth.get_user_list():
                self.write(render_template('reg_error.html', error=lc.get('user_already_exists')))
                return

            try:
                auth.register_user(
                    username = username,
                    password = password,
                    disp_name = disp_name,
                    email = email,
                    is_admin = is_admin,
                )
            except auth.BaseRegistrationError as e:
                self.write(render_template('reg_error.html', error=lc.get(e.text)))
                return
            self.redirect('/admin')


class LoginHandler(tornado.web.RequestHandler):
    def get(self):
        with locks.global_lock:
            session_id = self.get_cookie('session_id')
            if auth.load_session(session_id) is not None:
                self.redirect('/')
                return
            self.write(render_template('login.html'))


class RegisterHandler(tornado.web.RequestHandler):
    def get(self):
        with locks.global_lock:
            session_id = self.get_cookie('session_id')
            if auth.load_session(session_id) is not None:
                self.redirect('/')
                return
            if not competition.allow_team_self_registration:
                self.write(render_template('reg_error.html', error=lc.get('registration_disabled')))
                return
            self.write(render_template('register.html'))


class LogoutHandler(tornado.web.RequestHandler):
    def get(self):
        with locks.global_lock:
            session_id = self.get_cookie('session_id')
            if auth.load_session(session_id) is None:
                self.write(render_template('auth_error.html', error=lc.get('logout_no_session')))
                return
            auth.logout(session_id)
            self.clear_cookie('session_id')
            self.redirect('/')


class AuthHandler(tornado.web.RequestHandler):
    def post(self):
        with locks.global_lock:
            username = self.get_argument('username', None)
            password = self.get_argument('password', None)
            if username is None:
                self.write(render_template('auth_error.html', error=lc.get('no_username')))
                return
            if password is None:
                self.write(render_template('auth_error.html', error=lc.get('no_password')))
                return

            try:
                session = auth.authenticate_user(username, password)
            except auth.BaseAuthenticationError as e:
                self.write(render_template('auth_error.html', error=lc.get(e.text)))
                return
            self.set_cookie('session_id', session.id, expires=session.expires_at)
            self.redirect('/')


class RegHandler(tornado.web.RequestHandler):
    def post(self):
        with locks.global_lock:
            if not competition.allow_team_self_registration:
                self.write(render_template('reg_error.html', error=lc.get('registration_disabled')))
            username = self.get_argument('username', None)
            password = self.get_argument('password', None)
            password_c = self.get_argument('password-c', None)
            disp_name = self.get_argument('disp-name', None)
            email = self.get_argument('email', None)
            
            if username is None or username == '':
                self.write(render_template('reg_error.html', error=lc.get('no_username')))
                return
            if password is None or password == '':
                self.write(render_template('reg_error.html', error=lc.get('no_password')))
                return
            if password != password_c:
                self.write(render_template('reg_error.html', error=lc.get('password_c_failed')))
                return
            if disp_name is None or disp_name == '':
                self.write(render_template('reg_error.html', error=lc.get('no_disp_name')))
                return
            if username in auth.get_user_list():
                self.write(render_template('reg_error.html', error=lc.get('user_already_exists')))
                return

            try:
                auth.register_user(username=username, password=password, disp_name=disp_name, email=email)
            except auth.BaseRegistrationError as e:
                self.write(render_template('reg_error.html', error=lc.get(e.text)))
                return
            self.redirect('/')


class TasksHandler(tornado.web.RequestHandler):
    def get(self):
        with locks.global_lock:
            session_id = self.get_cookie('session_id')
            session = auth.load_session(session_id)
            if session is None:
                self.redirect('/login')
                return
            task_list = list(task_gen.get_generated_task_list(team_name=session.username))
            current_team = team.read_team(session.username)
            hint_purchases = tasks.get_hint_puchases_for_team(session.username)
            self.write(
                render_template(
                    'tasks.html',
                    session        = session,
                    tasks          = task_list,
                    team           = current_team,
                    hint_purchases = hint_purchases,
                )
            )


class TeamProfileHandler(tornado.web.RequestHandler):
    def get(self):
        with locks.global_lock:
            session_id = self.get_cookie('session_id')
            session = auth.load_session(session_id)
            if session is None:
                self.redirect('/login')
                return
            target_team_name = self.get_argument('team', None)
            if target_team_name is None:
                self.clear()
                self.set_status(404)
                self.finish(render_template('team_profile_404.html', session=session))
                return
            try:
                target_team = team.read_team(target_team_name)
            except BaseException:
                self.clear()
                self.set_status(404)
                self.finish(render_template('team_profile_404.html', session=session))
                return

            self.write(render_template('team_profile.html', session=session, team=target_team, tasks_module=tasks))


class ScoreboardHandler(tornado.web.RequestHandler):
    def get(self):
        with locks.global_lock:
            session_id = self.get_cookie('session_id')
            session = auth.load_session(session_id)
            if session is None:
                self.redirect('/login')
                return
            team_list = list(team.get_all_teams())
            task_list = list(tasks.get_task_list())
            self.write(
                render_template('scoreboard.html', session=session, team_list=team_list, task_list=task_list)
            )


class FaviconHandler(tornado.web.RequestHandler):
    def get(self):
        self.redirect('/static/favicon.png')


def make_app():
    return tornado.web.Application([
        (r'/', MainHandler),
        (r'/admin', AdminHandler),
        (r'/admin_new_team', AdminNewTeamHandler),
        (r'/api/(.*)', ApiHandler),
        (r'/login', LoginHandler),
        (r'/signup', RegisterHandler),
        (r'/lout', LogoutHandler), # /logout не работает под firefox за nginx reverse proxy (КАК???)
        (r'/auth', AuthHandler),
        (r'/reg', RegHandler),
        (r'/admin_reg', AdminRegHandler),
        (r'/tasks', TasksHandler),
        (r'/team_profile', TeamProfileHandler),
        (r'/change_password', ChangePasswordHandler),
        (r'/change_password_submit', ChangePasswordSubmitHandler),
        (r'/edit_team_info', EditTeamInfoHandler),
        (r'/edit_team_info_submit', EditTeamInfoSubmitHandler),
        (r'/scoreboard', ScoreboardHandler),
        (r'/get_attachment/(.*)', GetAttachmentHandler),
        (r'/favicon.ico', FaviconHandler),
        (r'/static/(.*)', tornado.web.StaticFileHandler, {'path': './static'})
    ], debug=configuration['debug'])


def main():
    lc.select_languages(configuration['lang_list'])

    app = make_app()
    host = configuration['host']
    port = configuration['port']
    app.listen(port=port, address=host)
    logger.info('Listening on {}:{}', host, port)
    logger.info('Running in {} mode', 'debug' if configuration['debug'] else 'production')
    tornado.ioloop.IOLoop.current().start()


if __name__ == "__main__":
    main()
