# -*- coding: utf-8 -*-

import os
import re

import configuration as conf
import localization as lc


class Template:
    """Template into which values will be put when the page is loaded"""

    def __init__(self, name):
        super(Template, self).__init__()
        self.name = name
        with open(os.path.join('templates', name)) as f:
            self.content = f.read()

    def render(self, locale, **kwargs):
        def repl(match):
            name = match.group(1)
            if name in kwargs:
                return kwargs[name]
            elif name[:3] == 'lc_':
                return locale.get(name[3:])
            elif name[:5] == 'conf_' and name[5:] in conf.configuration:
                return conf.configuration[name[5:]]
            else:
                return match.group(0)

        return re.sub(r'\$\{\{([a-zA-Z0-9][a-zA-Z0-9_]*)\}\}', repl,
                      self.content)
