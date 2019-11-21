# -*- coding: utf-8 -*-

import os
import re

from tornado.template import Template, Loader

from . import configuration as conf
from .competition import competition
from .localization import lc

template_loader = None

def render_template(template_name, **kwargs):
    global template_loader
    if template_loader is None or True:
        # XXX: enable template caching
        template_loader = Loader('templates')
    return template_loader.load(template_name).generate(
        **kwargs,
        lc = lc.get_dict(),
        conf = conf.configuration,
        comp = competition,
    )
