#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tornado.ioloop
import tornado.web
import sqlite3
import os


class TemplateFormatError(Exception):
    pass


def format_template(template, **kwargs):
    formatted = ''
    i = 0

    while i < len(template):
        if i + 2 < len(template) and template[i:i+3] == '${{':
            i += 3
            word = ''
            try:
                while template[i:i+2] != '}}':
                    word += template[i]
                    i += 1
                i += 1
            except IndexError:
                raise TemplateFormatError('Unexpected end of format sequence')
        i += 1


def get_template(name, **kwargs):
    with open(os.path.join('templates', name)) as f:
        return format_template(f.read(), **kwargs)


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.write("Hello, world")


class LoginHandler(tornado.web.RequestHandler):
    def get(self):
        self.write(get_template('login.html', lang='en', ctfname='TestCTF', lc_authorize='Authorize'))


def make_app():
    return tornado.web.Application([
        (r'/', MainHandler),
        (r'/login', LoginHandler),
    ])


def main():
    app = make_app()
    app.listen(8888)
    tornado.ioloop.IOLoop.current().start()


if __name__ == "__main__":
    main()
