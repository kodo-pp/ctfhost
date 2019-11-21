import json
import sqlite3
import time
from contextlib import closing
from datetime import datetime

from loguru import logger

from . import tasks
from . import util
from .configuration import configuration


class TaskAlreadySolved(Exception):
    pass


class Team:
    def __init__(self, team_name, info):
        self.team_name   = team_name
        self.full_name   = info['full_name']
        self.email       = info['email']
        self.solves      = info['solves']
        self.points      = info['points']
        self.submissions = info['submissions']
        self.seed        = info['seed']
        self.is_admin    = info['is_admin']

    def strip_private_data(self):
        self.submissions = []
        self.seed = '0' * 28


def get_submissions(team_name):
    with closing(sqlite3.connect(configuration['db_path'])) as db:
        cur = db.cursor()
        cur.execute('SELECT task_id, flag, correct, points FROM submissions WHERE team_name = ?', (team_name,))
        data = cur.fetchall()
    result = []
    for row in data:
        if not tasks.task_exists(row[0]):
            logger.warning('Unable to load submission: task {} not found', row[0])
            continue
        result.append(row)
    return result


def get_all_submissions():
    with closing(sqlite3.connect(configuration['db_path'], detect_types=sqlite3.PARSE_DECLTYPES)) as db:
        cur = db.cursor()
        cur.execute('SELECT team_name, task_id, flag, correct, points, time FROM submissions')
        data = cur.fetchall()
    result = []
    for i in data:
        row = {'team_name': i[0], 'task_id': i[1], 'flag': i[2], 'is_correct': i[3], 'points': i[4], 'time': i[5]}
        if not tasks.task_exists(row['task_id']):
            logger.warning('Unable to load submission: task {} not found', row['task_id'])
            continue
        result.append(row)
    return result


def get_all_teams():
    with closing(sqlite3.connect(configuration['db_path'], detect_types=sqlite3.PARSE_DECLTYPES)) as db:
        cur = db.cursor()
        cur.execute('SELECT username FROM users')
        team_names = [i[0] for i in cur.fetchall()]
    for i in team_names:
        yield read_team(i)


def get_solves(team_name):
    with closing(sqlite3.connect(configuration['db_path'], detect_types=sqlite3.PARSE_DECLTYPES)) as db:
        cur = db.cursor()
        cur.execute(
            'SELECT task_id, time, points FROM submissions WHERE team_name = ? AND correct = 1',
            (team_name,)
        )
        solves = cur.fetchall()
    result = {}
    for i in solves:
        if not tasks.task_exists(i[0]):
            logger.warning('Unable to load solve information: task {} not found', i[0])
            continue
        result[i[0]] = (i[1], i[2])
    return result


def get_team_basic_info(team_name):
    with closing(sqlite3.connect(configuration['db_path'])) as db:
        cur = db.cursor()
        cur.execute(
            'SELECT full_name, email, token_seed, is_admin FROM users WHERE username = ? LIMIT 1',
            (team_name,)
        )
        result = cur.fetchone()
    return {'full_name': result[0], 'email': result[1], 'seed': result[2], 'is_admin': result[3]}


def read_team(team_name):
    basic_info = get_team_basic_info(team_name)
    solves = get_solves(team_name)
    submissions = get_submissions(team_name)
    hint_purchases = tasks.get_hint_puchases_for_team(team_name)
    points = sum([i[3] for i in submissions]) - sum([i[2] for i in hint_purchases])
    info = {
        **basic_info,
        'solves': solves,
        'submissions': submissions,
        'points': points,
    }
    return Team(team_name, info)


def write_team(team):
    with closing(sqlite3.connect(configuration['db_path'])) as db:
        cur = db.cursor()
        cur.execute('UPDATE users SET full_name = ?, email = ? WHERE username = ?', (
            team.full_name,
            team.email,
            team.team_name
        ))
        db.commit()


def add_submission(team_name, task_id, flag, is_correct, points):
    with closing(sqlite3.connect(configuration['db_path'])) as db:
        cur = db.cursor()
        cur.execute(
            'SELECT rowid FROM submissions WHERE team_name = ? AND task_id = ? and correct = 1',
            (team_name, task_id)
        )
        if len(cur.fetchall()) > 0:
            raise TaskAlreadySolved()
        cur.execute(
            'INSERT INTO submissions VALUES (?, ?, ?, ?, ?, ?)',
            (team_name, task_id, flag, is_correct, points, datetime.now())
        )
        db.commit()

