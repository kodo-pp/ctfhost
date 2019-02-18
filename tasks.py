import sqlite3
import json
import os
import re
import shutil
import time
from contextlib import closing
from threading import Lock

from loguru import logger

import team
from configuration import configuration
from api import api, GUEST, USER, ADMIN, ApiArgumentError
from localization import lc


last_solves = {}
last_solves_lock = Lock()


class TaskNotFoundError(Exception):
    pass

class GroupNotFoundError(Exception):
    pass

class GroupReparentError(Exception):
    pass

class TooFrequentSubmissions(Exception):
    pass


def check_flag_with_program(prog, flag):
    raise NotImplementedError('Checker program is not yet implemented')


class Task:
    def __init__(self, task_id, info):
        self.task_id = task_id
        self.title   = info['title']
        self.text    = info['text']
        self.value   = info['value']
        self.labels  = info['labels']
        self.flags   = info['flags']
        self.group   = info['group']
        self.order   = info['order']
        self.seed    = info['seed']
        self.validate_flags()

    def validate_flags(self):
        # TODO: maybe generate user-friendly error messages
        if type(self.flags) is not list:
            raise TypeError('flags', type(self.flags))
        for flag_checker in self.flags:
            if type(flag_checker) is not dict:
                raise TypeError('flags[...]', type(flag_checker))
            if 'type' not in flag_checker:
                raise KeyError('flags[...].type')
            if 'data' not in flag_checker:
                raise KeyError('flags[...].data')
            if flag_checker['type'] not in {'string', 'regex', 'program'}:
                raise ValueError('flags[...].type', flag_checker['type'])

    def to_dict(self, complete=True):
        return {
            'task_id': self.task_id,
            **self.to_dict(complete=False),
        } if complete else {
            'title':   self.title,
            'text':    self.text,
            'value':   self.value,
            'labels':  self.labels,
            'flags':   self.flags,
            'group':   self.group,
            'order':   self.order,
            'seed':    self.seed,
        }

    def check_flag(self, flag, team_name):
        now = time.time()
        global last_solves, last_solves_lock
        with last_solves_lock:
            if team_name in last_solves:
                if last_solves[team_name] + configuration['min_submission_interval'] > now:
                    raise TooFrequentSubmissions()
            last_solves[team_name] = now
        for flag_checker in self.flags:
            fc_type = flag_checker['type']
            fc_data = flag_checker['data']
            if fc_type == 'string':
                if flag == fc_data:
                    return True
            elif fc_type == 'regex':
                if re.match(fc_data, flag) is not None:
                    return True
            elif fc_type == 'program':
                if check_flag_with_program(fc_data, flag):
                    return True
        return False

    def strip_private_data(self):
        self.flags = []


def get_task_list():
    tasks_path = configuration['tasks_path']
    os.makedirs(tasks_path, exist_ok=True)
    for task_dir in os.listdir(tasks_path):
        try:
            if not os.path.isdir(os.path.join(tasks_path, task_dir)):
                continue
            if re.match(r'^[1-9][0-9]*$', task_dir) is None:
                continue
            if not os.access(os.path.join(tasks_path, task_dir, 'task.json'), os.R_OK):
                continue
            task_id = int(task_dir)
            yield read_task(task_id)
        except Exception as e:
            logger.warning('Error loading task info: {}', repr(e))


def read_group(group_id):
    assert type(group_id) is int
    group_dir = os.path.join(configuration['groups_path'], str(group_id))
    group_file = os.path.join(group_dir, 'group.json')
    try:
        with open(group_file) as f:
            group_str = f.read()
        group = json.loads(group_str)
        return {'group_id': group_id, 'name': group['name'], 'parent': group['parent']}
    except FileNotFoundError:
        raise GroupNotFoundError(group_id)


def write_group(group):
    group_id = group.group_id
    assert type(group_id) is int
    group_dir = os.path.join(configuration['groups_path'], str(group_id))
    os.makedirs(group_dir, exist_ok=True)
    group_file = os.path.join(group_dir, 'group.json')
    obj = group.to_dict(False)
    with open(group_file, 'w') as f:
        f.write(json.dumps(obj))


def get_group_list():
    groups_path = configuration['groups_path']
    os.makedirs(groups_path, exist_ok=True)
    for group_dir in os.listdir(groups_path):
        try:
            if not os.path.isdir(os.path.join(groups_path, group_dir)):
                continue
            if re.match(r'^[1-9][0-9]*$', group_dir) is None:
                continue
            if not os.access(os.path.join(groups_path, group_dir, 'group.json'), os.R_OK):
                continue
            group_id = int(group_dir)
            yield read_group(group_id)
        except Exception as e:
            logger.warning('Error loading group info: {}', repr(e))

def get_group_dict():
    group_list = get_group_list()
    group_dict = {}
    for i in group_list:
        group_dict[i['group_id']] = i
    return group_dict


def build_group_path(groups, group_id, max_depth=30):
    try:
        path = []
        for i in range(max_depth):
            if group_id == 0:
                return list(reversed(path))
            group = groups[group_id]
            path.append(group['name'])
            group_id = group['parent']
        path.append('...')
        return list(reversed(path))
    except BaseException as e:
        logger.warning('Error building group path: {}', str(e))
        raise


def api_add_or_update_task(api, sess, args):
    http = args['http_handler']
    request = json.loads(http.request.body)
    task_id = request['task_id']
    text    = request['text']
    title   = request['title']
    value   = request['value']
    labels  = request['labels']
    flags   = request['flags']
    group   = request['group']
    order   = request['order']
    seed    = request['seed']

    if task_id is None or task_id == '':
        task_id = allocate_task_id()

    try:
        task_id = int(task_id)
    except (ValueError, TypeError) as e:
        raise Exception(
            lc.get('api_invalid_data_type').format(
                expected=lc.get('int'),
                param='task_id',
            )
        )

    try:
        value = int(value)
    except (ValueError, TypeError) as e:
        raise Exception(
            lc.get('api_invalid_data_type').format(
                expected=lc.get('int'),
                param='value',
            )
        )

    try:
        group = int(group)
    except (ValueError, TypeError) as e:
        raise Exception(
            lc.get('api_invalid_data_type').format(
                expected=lc.get('int'),
                param='group',
            )
        )

    try:
        order = int(order)
    except (ValueError, TypeError) as e:
        raise Exception(
            lc.get('api_invalid_data_type').format(
                expected=lc.get('int'),
                param='order',
            )
        )

    if type(seed) is not str or len(seed) != 16:
        raise Exception(
            lc.get('api_argument_error').format(
                argument='seed',
            )
        )
    
    if task_exists(task_id):
        logger.info('Modifying task {}', task_id)
        task = read_task(task_id)
        task.text = text
        task.title = title
        task.value = value
        task.labels = labels
        task.flags = flags
        task.group = group
        task.order = order
        task.seed = seed
        task.validate_flags()
        write_task(task)
    else:
        logger.info('Creating task {}', task_id)
        try:
            task = Task(
                task_id,
                {
                    'title':  title,
                    'text':   text,
                    'value':  value,
                    'labels': labels,
                    'flags':  flags,
                    'group':  group,
                    'order':  order,
                    'seed':   seed,
                }
            )
        except KeyError as e:
            raise ApiArgumentError(lc.get('api_argument_error').format(argument=str(e)))
        write_task(task)
    http.write(json.dumps({'success': True}))


def api_add_group(api, sess, args):
    http    = args['http_handler']
    request = json.loads(http.request.body)
    name    = request['name']
    parent  = request['parent']
    try:
        parent = int(parent)
    except (ValueError, TypeError) as e:
        raise Exception(
            lc.get('api_invalid_data_type').format(
                expected=lc.get('int'),
                param='parent',
            )
        )
    if name == '':
        raise ApiArgumentError(lc.get('api_argument_error').format(argument='name'))
    if parent != 0:
        read_group(parent)

    group_id = allocate_group_id()

    logger.info('Creating group {} ({})', name, group_id)
    write_group(group_id, {'name': name, 'parent': parent})
    http.write(json.dumps({'success': True}))


def api_rename_group(api, sess, args):
    http     = args['http_handler']
    request  = json.loads(http.request.body)
    group_id = request['group_id']
    new_name = request['new_name']
    try:
        group_id = int(group_id)
    except (ValueError, TypeError) as e:
        raise Exception(
            lc.get('api_invalid_data_type').format(
                expected=lc.get('int'),
                param='group_id',
            )
        )

    if new_name == '':
        raise ApiArgumentError(lc.get('api_argument_error').format(argument='name'))

    logger.info('Renaming group ({}) to {}', group_id, new_name)
    group = read_group(group_id)
    group['name'] = new_name

    write_group(group_id, group)
    http.write(json.dumps({'success': True}))


def api_reparent_group(api, sess, args):
    http     = args['http_handler']
    request  = json.loads(http.request.body)
    group_id = request['group_id']
    new_parent = request['new_parent']
    try:
        new_parent = int(new_parent)
    except (ValueError, TypeError) as e:
        raise Exception(
            lc.get('api_invalid_data_type').format(
                expected=lc.get('int'),
                param='new_parent',
            )
        )

    if may_reparent_group(group_id, new_parent):
        logger.info('Reparenting group ({}): new parent: ({})', group_id, new_parent)
        reparent_group(group_id, new_parent)
    else:
        logger.warning('Cannot reparent group ({}): new parent: ({})', group_id, new_parent)
        raise GroupReparentError(lc.get('parent_loop_detected'))


    http.write(json.dumps({'success': True}))


def may_reparent_group(group_id, new_parent):
    group_ids = set([group_id])
    group = read_group(group_id)
    group['parent'] = new_parent
    while True:
        parent_id = group['parent']
        if parent_id == 0:
            # OK, alternative path to root group
            return True
        elif parent_id in group_ids:
            # Not OK: loop
            return False
        group_ids.add(parent_id)
        group = read_group(parent_id)


def reparent_group(group_id, new_parent):
    group = read_group(group_id)
    group['parent'] = new_parent
    write_group(group_id, group)


def api_get_task(api, sess, args):
    http = args['http_handler']
    request = json.loads(http.request.body)
    task_id = request['task_id']

    try:
        task_id = int(task_id)
    except (ValueError, TypeError) as e:
        raise Exception(
            lc.get('api_invalid_data_type').format(
                expected=lc.get('int'),
                param='task_id',
            )
        )
    try:
        task = read_task(task_id)
    except TaskNotFoundError:
        raise Exception(lc.get('task_does_not_exist').format(task_id=task_id))
    
    http.write(json.dumps({'success': True, 'task': task.to_dict()}))


def api_submit_flag(api, sess, args):
    http = args['http_handler']
    request = json.loads(http.request.body)
    task_id = request['task_id']
    flag_data = request['flag']

    try:
        task_id = int(task_id)
    except (ValueError, TypeError) as e:
        raise Exception(
            lc.get('api_invalid_data_type').format(
                expected=lc.get('int'),
                param='task_id',
            )
        )
    try:
        task = read_task(task_id)
    except TaskNotFoundError:
        raise Exception(lc.get('task_does_not_exist').format(task_id=task_id))

    try:
        correct = bool(task.check_flag(flag_data, team_name=sess.username))
    except TooFrequentSubmissions:
        logger.warning('Too frequent submissions from team {} for task with ID {}', sess.username, task_id)
        http.write(json.dumps({
            'success': False,
            'error_message': lc.get('task_submission_too_frequent').format(
                time=configuration['min_submission_interval']
            )
        }))
        return

    try:
        team.add_submission(
            team_name = sess.username,
            task_id = task_id,
            flag = flag_data,
            is_correct = correct,
            points = task.value if correct else 0,
        )
    except team.TaskAlreadySolved:
        logger.warning('Team {} submitted a flag for already solved task with ID {}', sess.username, task_id)
        http.write(json.dumps({'success': False, 'error_message': lc.get('task_already_solved')}))
        return
        

    logger.info('Flag submission from team {} for task with ID {} - {}'.format(
        sess.username,
        task_id,
        'correct' if correct else 'wrong'
    ))
    http.write(json.dumps({'success': True, 'flag_correct': correct}))


def api_delete_task(api, sess, args):
    http = args['http_handler']
    request = json.loads(http.request.body)
    task_id = request['task_id']

    try:
        task_id = int(task_id)
    except (ValueError, TypeError) as e:
        raise Exception(
            lc.get('api_invalid_data_type').format(
                expected=lc.get('int'),
                param='task_id',
            )
        )
    try:
        logger.info("Deleting task with id {}", task_id)
        delete_task(task_id)
    except TaskNotFoundError:
        raise Exception(lc.get('task_does_not_exist').format(task_id=task_id))
    
    http.write(json.dumps({'success': True}))


def api_delete_group(api, sess, args):
    http = args['http_handler']
    request = json.loads(http.request.body)
    group_id = request['group_id']

    try:
        group_id = int(group_id)
    except (ValueError, TypeError) as e:
        raise Exception(
            lc.get('api_invalid_data_type').format(
                expected=lc.get('int'),
                param='group_id',
            )
        )
    try:
        logger.info("Deleting group ({})", group_id)
        delete_group(group_id)
    except GroupNotFoundError:
        raise Exception(lc.get('group_does_not_exist').format(group_id=group_id))
    
    http.write(json.dumps({'success': True}))


def delete_task(task_id):
    if type(task_id) is not int:
        # Security measure, because this function can potentially do something
        raise TaskNotFoundError()
    if not task_exists(task_id):
        raise TaskNotFoundError()
    shutil.rmtree(os.path.join(configuration['tasks_path'], str(task_id)))


def delete_group(group_id):
    if type(group_id) is not int:
        # Security measure, because this function can potentially do something
        raise GroupNotFoundError()
    if not group_exists(group_id):
        raise GroupNotFoundError()
    shutil.rmtree(os.path.join(configuration['groups_path'], str(group_id)))
    # TODO: deal properly with orphans


def task_exists(task_id):
    if type(task_id) is not int:
        return False
    return os.access(os.path.join(configuration['tasks_path'], str(task_id), 'task.json'), os.R_OK)


def group_exists(group_id):
    if type(group_id) is not int:
        return False
    return os.access(os.path.join(configuration['groups_path'], str(group_id), 'group.json'), os.R_OK)


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


def allocate_group_id():
    path = configuration['group_maxid_path']
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        with open(path) as f:
            s = f.read()
            last_group_id = int(s) if s != '' else 0
        with open(path, 'w') as f:
            f.write(str(last_group_id + 1))
        return last_group_id + 1
    except FileNotFoundError:
        with open(path, 'w') as f:
            f.write('1')
        return 1


def read_task(task_id):
    if type(task_id) is not int:
        raise TaskNotFoundError(task_id)
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
    if type(task_id) is not int:
        raise TaskNotFoundError(task_id)
    task_dir = os.path.join(configuration['tasks_path'], str(task_id))
    os.makedirs(task_dir, exist_ok=True)
    task_file = os.path.join(task_dir, 'task.json')
    obj = task.to_dict(False)
    with open(task_file, 'w') as f:
        f.write(json.dumps(obj))


def read_group(group_id):
    if type(group_id) is not int:
        raise GroupNotFoundError(group_id)
    group_dir = os.path.join(configuration['groups_path'], str(group_id))
    group_file = os.path.join(group_dir, 'group.json')
    try:
        with open(group_file) as f:
            group_str = f.read()
        group = json.loads(group_str)
        group['group_id'] = group_id
        return group
    except FileNotFoundError:
        raise GroupNotFoundError(group_id)


def write_group(group_id, group_dict):
    if type(group_id) is not int:
        raise GroupNotFoundError(group_id)
    group_dir = os.path.join(configuration['groups_path'], str(group_id))
    os.makedirs(group_dir, exist_ok=True)
    group_file = os.path.join(group_dir, 'group.json')
    with open(group_file, 'w') as f:
        f.write(json.dumps(group_dict))


api.add('add_or_update_task', api_add_or_update_task, access_level=ADMIN)
api.add('delete_task',        api_delete_task,        access_level=ADMIN)
api.add('get_task',           api_get_task,           access_level=USER)
api.add('submit_flag',        api_submit_flag,        access_level=USER)
api.add('add_group',          api_add_group,          access_level=ADMIN)
api.add('rename_group',       api_rename_group,       access_level=ADMIN)
api.add('reparent_group',     api_reparent_group,     access_level=ADMIN)
api.add('delete_group',       api_delete_group,       access_level=ADMIN)
