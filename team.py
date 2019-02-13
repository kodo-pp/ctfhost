import sqlite3
import json
import time
from contextlib import closing
from datetime import datetime

from loguru import logger

from configuration import configuration


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

    def strip_private_data(self):
        self.submissions = []


def get_submissions(team_name):
    with closing(sqlite3.connect(configuration['db_path'])) as db:
        cur = db.cursor()
        cur.execute('SELECT task_id, flag, correct, points FROM submissions WHERE team_name = ?', (team_name,))
        return cur.fetchall()


def get_solves(team_name):
    with closing(sqlite3.connect(configuration['db_path'], detect_types=sqlite3.PARSE_DECLTYPES)) as db:
        cur = db.cursor()
        cur.execute(
            'SELECT task_id, time, points FROM submissions WHERE team_name = ? AND correct = 1',
            (team_name,)
        )
        solves = cur.fetchall()
    return {i[0]: (i[1], i[2]) for i in solves}


def get_team_basic_info(team_name):
    with closing(sqlite3.connect(configuration['db_path'])) as db:
        cur = db.cursor()
        cur.execute('SELECT full_name, email FROM users WHERE username = ?', (team_name,))
        result = cur.fetchone()
    return {'full_name': result[0], 'email': result[1]}


def read_team(team_name):
    basic_info = get_team_basic_info(team_name)
    solves = get_solves(team_name)
    submissions = get_submissions(team_name)
    points = sum([i[3] for i in submissions])   # 3 ==> points
    info = {
        **basic_info,
        'solves': solves,
        'submissions': submissions,
        'points': points,
    }
    return Team(team_name, info)


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
