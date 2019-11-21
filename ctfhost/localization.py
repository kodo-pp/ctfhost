# -*- coding: utf-8 -*-

import os
from configparser import ConfigParser


class Localization:
    def __init__(self):
        self.languages = {}
        self.selected_languages = []

        for lang_file in os.scandir('locale'):
            if not lang_file.is_file() or not lang_file.name.endswith('.lang'):
                continue
            config = ConfigParser()
            config.read(lang_file, encoding='utf-8')
            lang_info = config['information']
            lang_data = config['data']
            self.languages[lang_info['id']] = {
                'name': lang_info['name'],
                'native_name': lang_info['native_name'],
                'data': dict(lang_data)
            }

        if len(self.languages) == 0:
            raise Exception('No suitable language files found')

    def list_languages(self):
        return self.languages

    def select_languages(self, langs):
        self.selected_languages = langs

    def get(self, key):
        for lang in self.selected_languages:
            if lang in self.languages and key in self.languages[lang]['data']:
                return self.languages[lang]['data'][key]
        return key

    def get_dict(self):
        result = {}
        for lang in self.selected_languages:
            if lang in self.languages:
                for k, v in self.languages[lang]['data'].items():
                    if k not in result:
                        result[k] = v
        return result

lc = Localization()
