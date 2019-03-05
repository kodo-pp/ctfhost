import json
import os
import time

from api import api, ADMIN
from configuration import configuration


class Competition:
    def __init__(self, start_time, end_time, allow_team_self_registration):
        self.start_time = start_time
        self.end_time = end_time
        self.allow_team_self_registration = allow_team_self_registration


def read_competition_config():
    conf_dir = os.path.dirname(configuration['competition_config_path'])
    os.makedirs(conf_dir, exist_ok=True)
    if not os.access(configuration['competition_config_path'], os.F_OK):
        with open(configuration['competition_config_path'], 'w') as f:
            now = time.mktime(time.gmtime())
            f.write(
                json.dumps({
                    'start_time': now,
                    'end_time': now,
                    'allow_team_self_registration': False,
                })
            )
    with open(configuration['competition_config_path']) as f:
        s = f.read()
    return json.loads(s)


def api_compettion_ctl(api, sess, args):
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

    logger.info('Updating competition configuration: {}', {
        'start_time': start_time,
        'end_time': end_time,
        'allow_team_self_registration': allow_team_self_registration,
    })
    
    competition.start_time = start_time
    competition.end_time = end_time
    competition.allow_team_self_registration = allow_team_self_registration

    http.write(json.dumps({'success': True}))


competition = Competition(**read_competition_config())

api.add('competition_ctl', api_compettion_ctl, access_level=ADMIN)
