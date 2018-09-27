#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3

import tornado.ioloop
import tornado.web

from localization import Localization
from template import Template

lc = None


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.write("Hello, world")


class LoginHandler(tornado.web.RequestHandler):
    def get(self):
        self.write(Template('login.html').render(lc))


def make_app():
    return tornado.web.Application([
        (r'/', MainHandler),
        (r'/login', LoginHandler),
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
