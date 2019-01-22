import sqlite3
from contextlib import closing

from configuration import configuration


class Task:
    def __init__(self, name, info=None):
        self.name = name
        if info is None:
            info = get_task_info(name)
        self.title = info['title']
        self.text = info['title']
        self.value = info['value']


def get_task_list():
    # XXX: stub
    return [
        Task('test_task1', {
            'title': 'Test task 1',
            'text': 'First task text',
            'value': 200,
        }),
        Task('test_task2', {
            'title': 'Test task 2',
            'text': 'Second task text',
            'value': 30,
        }),
        Task('test_task3', {
            'title': 'Test task 3',
            'text': 'Third task text',
            'value': 50000,
        }),
    ]
