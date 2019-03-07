import json
import os
import time

from loguru import logger

import util
from api import api, ADMIN
from configuration import configuration


class Competition:
    def __init__(self, start_time, end_time, allow_team_self_registration):
        self.start_time = start_time
        self.end_time = end_time
        self.allow_team_self_registration = allow_team_self_registration

    def to_dict(self):
        return {
            'start_time': self.start_time,
            'end_time': self.end_time,
            'allow_team_self_registration': self.allow_team_self_registration,
        }


def read_competition_config():
    conf_dir = os.path.dirname(configuration['competition_config_path'])
    os.makedirs(conf_dir, exist_ok=True)
    if not os.access(configuration['competition_config_path'], os.F_OK):
        now = util.get_current_utc_time()
        write_competition_config({
            'start_time': now,
            'end_time': now,
            'allow_team_self_registration': False,
        })
    with open(configuration['competition_config_path']) as f:
        s = f.read()
    return json.loads(s)


def write_competition_config(config):
    conf_dir = os.path.dirname(configuration['competition_config_path'])
    os.makedirs(conf_dir, exist_ok=True)
    with open(configuration['competition_config_path'], 'w') as f:
        f.write(json.dumps(config))


def api_competition_ctl(api, sess, args):
    http       = args['http_handler']
    request    = json.loads(http.request.body)
    start_time = request['start_time']
    end_time   = request['end_time']
    allow_team_self_registration = request['allow_team_self_registration']

    try:
        start_time = int(start_time)
    except (ValueError, TypeError) as e:
        raise Exception(
            lc.get('api_invalid_data_type').format(
                expected=lc.get('int'),
                param='start_time',
            )
        )

    try:
        end_time = int(end_time)
    except (ValueError, TypeError) as e:
        raise Exception(
            lc.get('api_invalid_data_type').format(
                expected=lc.get('int'),
                param='end_time',
            )
        )

    try:
        allow_team_self_registration = bool(start_time)
    except (ValueError, TypeError) as e:
        raise Exception(
            lc.get('api_invalid_data_type').format(
                expected=lc.get('bool'),
                param='allow_team_self_registration',
            )
        )

    time_fmt = lambda unix_ts: time.strftime("%Y-%m-%d %H:%M:%S (UTC)", time.localtime(unix_ts))
    
    logger.info('Updating competition configuration: {}', {
        'start_time': time_fmt(start_time),
        'end_time': time_fmt(end_time),
        'allow_team_self_registration': allow_team_self_registration,
    })
    
    global competition
    competition.start_time = start_time
    competition.end_time = end_time
    competition.allow_team_self_registration = allow_team_self_registration
    write_competition_config(competition.to_dict())

    http.write(json.dumps({'success': True}))


def is_running():
    now = util.get_current_utc_time()
    start_time = competition.start_time
    end_time = competition.end_time
    return start_time <= now < end_time


competition = Competition(**read_competition_config())

api.add('competition_ctl', api_competition_ctl, access_level=ADMIN)
