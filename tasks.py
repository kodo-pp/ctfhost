import sqlite3
import json
import os
import re
import shutil
from contextlib import closing

from loguru import logger

from configuration import configuration
from api import api, GUEST, USER, ADMIN


class TaskNotFoundError(Exception):
    def __init__(self, *a):
        super().__init__(*a)


class Task:
    def __init__(self, task_id, info):
        self.task_id = task_id
        self.title = info['title']
        self.text = info['text']
        self.value = info['value']

    def to_dict(self, complete=True):
        return {
            'task_id': self.task_id,
            'title': self.title,
            'text': self.text,
            'value': self.value,
        } if complete else {
            'title': self.title,
            'text': self.text,
            'value': self.value,
        }


def get_task_list():
    tasks_path = configuration['tasks_path']
    os.makedirs(tasks_path, exist_ok=True)
    for task_dir in os.listdir(tasks_path):
        if not os.path.isdir(os.path.join(tasks_path, task_dir)):
            continue
        if re.match(r'^[1-9][0-9]*$', task_dir) is None:
            continue
        if not os.access(os.path.join(tasks_path, task_dir, 'task.json'), os.R_OK):
            continue
        task_id = int(task_dir)
        yield read_task(task_id)


def api_add_or_update_task(api, sess, args):
    http = args['http_handler']
    request = json.loads(http.request.body)
    task_id = request['task_id']
    text    = request['text']
    title   = request['title']
    value   = request['value']

    if task_id is None or task_id == '':
        task_id = allocate_task_id()

    try:
        task_id = int(task_id)
    except (ValueError, TypeError) as e:
        http.write(json.dumps({
            'success': False,
            'error_message': api.lc.get('api_invalid_data_type').format(
                expected=api.lc.get('int'),
                param='task_id',
            )
        }))
        return

    try:
        value = int(value)
    except (ValueError, TypeError) as e:
        http.write(json.dumps({
            'success': False,
            'error_message': api.lc.get('api_invalid_data_type').format(
                expected=api.lc.get('int'),
                param='value',
            )
        }))
        return
    
    if task_exists(task_id):
        logger.info('Modifying task {}', task_id)
        task = read_task(task_id)
        task.text = text
        task.title = title
        task.value = value
        write_task(task)
    else:
        logger.info('Creating task {}', task_id)
        task = Task(task_id, {'title': title, 'text': text, 'value': value})
        write_task(task)
    http.write(json.dumps({'success': True}))


def api_get_task(api, sess, args):
    http = args['http_handler']
    request = json.loads(http.request.body)
    task_id = request['task_id']

    try:
        task_id = int(task_id)
    except (ValueError, TypeError) as e:
        http.write(json.dumps({
            'success': False,
            'error_message': api.lc.get('api_invalid_data_type').format(
                expected=api.lc.get('int'),
                param='task_id',
            )
        }))
        return
    try:
        task = read_task(task_id)
    except TaskNotFoundError:
        http.write(json.dumps({
            'success': False,
            'error_message': api.lc.get('task_does_not_exist').format(task_id=task_id)
        }))
        return
    
    http.write(json.dumps({'success': True, 'task': task.to_dict()}))


def api_delete_task(api, sess, args):
    http = args['http_handler']
    request = json.loads(http.request.body)
    task_id = request['task_id']

    try:
        task_id = int(task_id)
    except (ValueError, TypeError) as e:
        http.write(json.dumps({
            'success': False,
            'error_message': api.lc.get('api_invalid_data_type').format(
                expected=api.lc.get('int'),
                param='task_id',
            )
        }))
        return
    try:
        delete_task(task_id)
    except TaskNotFoundError:
        http.write(json.dumps({
            'success': False,
            'error_message': api.lc.get('task_does_not_exist').format(task_id=task_id)
        }))
        return
    
    http.write(json.dumps({'success': True}))


def delete_task(task_id):
    if type(task_id) is not int:
        # Security measure, because this function can potentially do something
        raise TaskNotFoundError()
    if not task_exists(task_id):
        raise TaskNotFoundError()
    shutil.rmtree(os.path.join(configuration['tasks_path'], str(task_id)))


def task_exists(task_id):
    assert type(task_id) is int
    return os.access(os.path.join(configuration['tasks_path'], str(task_id), 'task.json'), os.R_OK)


def allocate_task_id():
    path = configuration['task_maxid_path']
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        with open(path) as f:
            s = f.read()
            last_task_id = int(s) if s != '' else 0
        with open(path, 'w') as f:
            f.write(str(last_task_id + 1))
        return last_task_id + 1
    except FileNotFoundError:
        with open(path, 'w') as f:
            f.write('1')
        return 1


def read_task(task_id):
    assert type(task_id) is int
    task_dir = os.path.join(configuration['tasks_path'], str(task_id))
    task_file = os.path.join(task_dir, 'task.json')
    try:
        with open(task_file) as f:
            task_str = f.read()
        task = json.loads(task_str)
        return Task(task_id, task)
    except FileNotFoundError:
        raise TaskNotFoundError(task_id)


def write_task(task):
    task_id = task.task_id
    assert type(task_id) is int
    task_dir = os.path.join(configuration['tasks_path'], str(task_id))
    os.makedirs(task_dir, exist_ok=True)
    task_file = os.path.join(task_dir, 'task.json')
    obj = task.to_dict(False)
    with open(task_file, 'w') as f:
        f.write(json.dumps(obj))


api.add('add_or_update_task', api_add_or_update_task, access_level=ADMIN)
api.add('delete_task',        api_delete_task,        access_level=ADMIN)
api.add('get_task',           api_get_task,           access_level=USER)
