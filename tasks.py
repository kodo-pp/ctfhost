import sqlite3
import json
import os
from contextlib import closing

from loguru import logger

from configuration import configuration
from api import api


class Task:
    def __init__(self, task_id, info):
        self.task_id = task_id
        self.title = info['title']
        self.text = info['text']
        self.value = info['value']


def get_task_list():
    # XXX: stub
    return [
        Task(1, {
            'title': 'Test task 1',
            'text': 'First task text',
            'value': 200,
        }),
        Task(2, {
            'title': 'Test task 2',
            'text': 'Second task text',
            'value': 30,
        }),
        Task(3, {
            'title': 'Test task 3',
            'text': 'Third task text',
            'value': 50000,
        }),
    ]


def api_add_or_update_task(api, args):
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
    except ValueError:
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
    except ValueError:
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


def task_exists(task_id):
    assert type(task_id) is int
    with closing(sqlite3.connect(configuration['db_path'])) as db:
        cur = db.cursor()
        cur.execute('SELECT rowid FROM tasks WHERE task_id = ?', (task_id,))
        return len(cur.fetchall()) > 0


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
    with open(task_file) as f:
        task_str = f.read()
    task = json.loads(task_str)
    return Task(task_id, task)


def write_task(task):
    task_id = task.task_id
    assert type(task_id) is int
    task_dir = os.path.join(configuration['tasks_path'], str(task_id))
    os.makedirs(task_dir, exist_ok=True)
    task_file = os.path.join(task_dir, 'task.json')
    obj = {
        'title': task.title,
        'value': task.value,
        'text': task.text
    }
    with open(task_file, 'w') as f:
        f.write(json.dumps(obj))


api.add('add_or_update_task', api_add_or_update_task)
