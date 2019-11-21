# -*- coding: utf-8 -*-

import hashlib

from . import date_fmt
from . import util


configuration = {
    # CTF name. Displayed in page title and on the homepage
    'ctfname':                 'TestCTF',

    # Welcome message. Displayed on the homepage. {ctfname} is substiruted with the CTF name
    'welcome_message':         'Welcome to <b>{ctf_name}</b>!',

    # Path to the main database
    'db_path':                 'db/ctfhost.db',

    # Session duration, in seconds
    'session_duration':        86400,

    # If True, passwords will be replaced with <hidden> in logs (recommended)
    'hide_password_in_logs':   True,

    # Path to tasks directory
    'tasks_path':              'db/tasks',

    # Path to groups directory
    'groups_path':             'db/groups',

    # Language(s) to use. You can specify any number of fallback languages.
    # e.g. ['ru_RU', 'en_US'] leads to the most of the content being translated
    # to Russian but any strings missing in 'ru_RU' locale being translated to English
    'lang_list':               ['en_US', 'ru_RU'],

    # Path to task max_id file
    'task_maxid_path':         'db/tasks-etc/maxid.txt',

    # Path to group max_id file
    'group_maxid_path':        'db/tasks-etc/maxgroupid.txt',

    # Minimal flag submission interval. Teams won't be able to submit flags more often
    # than one in min_submission_interval seconds
    'min_submission_interval': 30,

    # Function to format date in the admin panel (taking a datetime object, returning a str)
    'date_fmt_func':           date_fmt.default_date_fmt,

    # Path to task generation configuration presets
    'gen_config_presets_path': 'presets/gen',

    # Path to global seed file
    'ctfhost_seed_path':       'db/ctfhost-seed.txt',

    # Path to competition configuration file
    'competition_config_path': 'db/competition-ctl/competition-ctl.json',

    # Hash function used to hash passwords and session IDs
    # Change to util.make_hash_function(hashlib.sha256) or something like that if sha3 functions are not available
    # WARNING: if you change this function, all sessions and passwords in the database will become invalid!
    'secure_hash_function':    util.make_hash_function(hashlib.sha3_256),

    # Path to global hash salt file
    'global_salt_path':        'db/salt.txt',

    # Port to listen on
    'port':                    8899,

    # Address to bind to
    'host':                    '0.0.0.0',

    # Debug mode
    'debug':                   True,
}
