#!/usr/bin/env python3

import sys
import os

sys.path.insert(0, os.path.realpath('.'))

from configuration import configuration

import task_gen
import tasks
import team


def main():
    if '--help' in sys.argv:
        print('Usage: {} [--force]'.format(sys.argv[0]))
        print('Generates all tasks for all teams in advance')
        print()
        print('Options:')
        print('  --force   Regenerate even if generated tasks are up-to-date')
        sys.exit(1)
    generate_func = task_gen.generate if '--force' in sys.argv else task_gen.maybe_generate
    
    team_list = list(team.get_all_teams())
    task_list = list(tasks.get_task_list())

    for tm in team_list:
        for ts in task_list:
            token = task_gen.get_token(team_name=tm.team_name, task_id=ts.task_id)
            generate_func(task_id=ts.task_id, token=token, team=tm)


if __name__ == '__main__':
    main()
