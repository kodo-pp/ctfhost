# -*- coding: utf-8 -*-

import os
import re

import configuration as conf
import localization as lc

from tornado.template import Template, Loader

template_loader = None

def render_template(template_name, lc, **kwargs):
    global template_loader
    if template_loader is None or True:
        template_loader = Loader('templates')
    prefixed_lc = dict([('lc_' + k, v) for k, v in lc.get_dict().items()])
    prefixed_conf = dict([('conf_' + k, v) for k, v in conf.configuration.items()])
    return template_loader.load(template_name).generate(**kwargs, **prefixed_lc, **prefixed_conf)
