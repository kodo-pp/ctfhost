import os
import sys

from loguru import logger

import tasks
import util
from configuration import configuration


class PresetNotFoundError(Exception):
    pass


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
