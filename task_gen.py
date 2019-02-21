import os
import sys
import hashlib
import traceback
import json
import time

from loguru import logger

import tasks
import util
import team
from configuration import configuration
from api import api, ADMIN, USER, GUEST


class PresetNotFoundError(Exception):
    pass


def get_token(team_name, task_id):
    task = tasks.read_task(task_id)
    
    team_seed = team.read_team(team_name).seed
    task_seed = task.seed
    ctfhost_seed = util.get_ctfhost_seed()

    return hashlib.sha224(
        'team:{},task:{},glob:{};'.format(
            team_seed,
            task_seed,
            ctfhost_seed
        ).encode()
    ).hexdigest()


def read_preset(preset_name):
    presets_dir = configuration['gen_config_presets_path']
    os.makedirs(presets_dir, exist_ok=True)
    preset_filename = os.path.join(presets_dir, preset_name + '.py')
    if not os.access(preset_filename, os.R_OK):
        raise PresetNotFoundError()
    with open(preset_filename) as f:
        return f.read()
    

def make_task_generation_config_from_preset(task_id, preset_name):
    if type(task_id) is not int:
        raise tasks.TaskNotFoundError()
    task_dir = os.path.join(configuration['tasks_path'], str(task_id))
    if not os.access(task_dir, os.R_OK | os.X_OK):
        raise tasks.TaskNotFoundError()

    preset = read_preset(preset_name)
    logger.info('Making task ({}) generation config from preset "{}"', task_id, preset_name)
    task_gen_file = os.path.join(task_dir, 'generate.py')

    with open(task_gen_file, 'w') as f:
        f.write(preset)


def read_task_generation_config(task_id):
    if type(task_id) is not int:
        raise tasks.TaskNotFoundError()
    task_dir = os.path.join(configuration['tasks_path'], str(task_id))
    if not os.access(task_dir, os.R_OK | os.X_OK):
        raise tasks.TaskNotFoundError()
    task_gen_file = os.path.join(task_dir, 'generate.py')
    if not os.access(task_gen_file, os.R_OK):
        make_task_generation_config_from_preset(task_id, 'noop')
    with open(task_gen_file) as f:
        return f.read()


def write_task_generation_config(task_id, config):
    if type(task_id) is not int:
        raise tasks.TaskNotFoundError()
    task_dir = os.path.join(configuration['tasks_path'], str(task_id))
    if not os.access(task_dir, os.R_OK | os.X_OK):
        raise tasks.TaskNotFoundError()
    task_gen_file = os.path.join(task_dir, 'generate.py')
    with open(task_gen_file, 'w') as f:
        f.write(config)


def get_generated_task(task_id, token):
    if not tasks.task_exists(task_id):
        raise tasks.TaskNotFoundError(task_id)
    maybe_generate(task_id, token)
    return read_generated_task(task_id, token)


def read_generated_task(task_id, token):
    if type(task_id) is not int:
        raise tasks.TaskNotFoundError(task_id)
    task_dir = os.path.join(configuration['tasks_path'], str(task_id), 'generated', str(token))
    task_file = os.path.join(task_dir, 'task.json')
    try:
        with open(task_file) as f:
            task_str = f.read()
        task = json.loads(task_str)
        return tasks.Task(task_id, task)
    except FileNotFoundError:
        raise tasks.TaskNotFoundError(task_id)


def write_generated_task(task, token):
    task_id = task.task_id
    if type(task_id) is not int:
        raise TaskNotFoundError(task_id)
    task_dir = os.path.join(configuration['tasks_path'], str(task_id), 'generated', str(token))
    os.makedirs(task_dir, exist_ok=True)
    task_file = os.path.join(task_dir, 'task.json')
    obj = task.to_dict(False)
    with open(task_file, 'w') as f:
        f.write(json.dumps(obj))


def maybe_generate(task_id, token):
    if should_generate(task_id, token):
        generate(task_id, token)


def should_generate(task_id, token):
    task_dir = os.path.join(configuration['tasks_path'], str(task_id), 'generated', str(token))
    if not os.access(task_dir, os.F_OK):
        return True
    try:
        gen_ts = get_generation_timestamp(task_id, token)
    except BaseException:
        return True
    conf_ts = get_config_modification_timestamp(task_id)
    return gen_ts < conf_ts


def get_generation_timestamp(task_id, token):
    task_dir = os.path.join(configuration['tasks_path'], str(task_id), 'generated', str(token))
    with open(os.path.join(task_dir, 'gen_ts')) as f:
        return float(f.read())


def get_config_modification_timestamp(task_id):
    task_dir = os.path.join(configuration['tasks_path'], str(task_id))
    task_gen_file = os.path.join(task_dir, 'generate.py')
    return os.stat(task_gen_file).st_mtime


def generate(task_id, token):
    logger.info('Generating task {} with token {}', task_id, token)
    task_dir = os.path.join(configuration['tasks_path'], str(task_id))
    os.makedirs(task_dir, exist_ok=True)

    mod = util.import_file(os.path.join(task_dir, 'generate.py'))
    raw_task = tasks.read_task(task_id)
    gen_task = mod.generate(raw_task, token)
    write_generated_task(gen_task, token)
    with open(os.path.join(task_dir, 'generated', token, 'gen_ts'), 'w') as f:
        f.write(str(time.time()))


def get_generated_task_list(team_name):
    for task in tasks.get_task_list():
        token = get_token(team_name=team_name, task_id=task.task_id)
        yield get_generated_task(task_id=task.task_id, token=token)


def api_update_gen_config(api, sess, args):
    http = args['http_handler']
    request = json.loads(http.request.body)
    task_id    = request['task_id']
    new_config = request['new_config']

    try:
        task_id = int(task_id)
    except (ValueError, TypeError) as e:
        raise Exception(
            lc.get('api_invalid_data_type').format(
                expected=lc.get('int'),
                param='task_id',
            )
        )
    
    write_task_generation_config(task_id, new_config)
    http.write(json.dumps({'success': True}))

api.add('update_gen_config', api_update_gen_config, access_level=ADMIN)
