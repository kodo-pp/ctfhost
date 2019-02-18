# -*- coding: utf-8 -*-

import date_fmt

configuration = {
    'ctfname':                 'TestCTF',
    'welcome_message':         'Welcome to <b>{ctf_name}</b>!',
    'db_path':                 'db/ctfhost.db',
    'session_duration':        86400,
    'hide_password_in_logs':   True,
    'tasks_path':              'db/tasks',
    'groups_path':             'db/groups',
    'lang_list':               ['en_US'],
    'task_maxid_path':         'db/tasks-etc/maxid.txt',
    'group_maxid_path':        'db/tasks-etc/maxgroupid.txt',
    'min_submission_interval': 30,
    'date_fmt_func':           date_fmt.default_date_fmt,
    'gen_config_presets_path': 'presets/gen'
}
