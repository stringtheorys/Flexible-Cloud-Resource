"""
Test the model distribution files
"""

import json
import os
import random as rnd
import sys

from extra.io import parse_args
from extra.model import ModelDistribution


def test_model_distribution():
    print()
    files = os.listdir('models/')
    for file in files:
        if file == "caroline.mdl":
            model_dist = ModelDistribution(f'models/caroline.mdl', num_tasks=2)

            tasks, servers = model_dist.generate()
            assert len(tasks) == 2
            assert len(servers) == 8
        else:
            model_dist = ModelDistribution(f'models/{file}', num_tasks=4, num_servers=3)

            tasks, servers = model_dist.generate()
            assert len(tasks) == 4
            assert len(servers) == 3


def test_model_probability():
    print()
    with open('models/basic.mdl') as file:
        file_data = json.load(file)

        task_probabilities = [task_distribution['probability'] for task_distribution in file_data['task distributions']]
        print(f'Task Probabilities: [{" ".join([str(prob) for prob in task_probabilities])}]')
        print(f'Sum probabilities: [{" ".join([str(sum(task_probabilities[:p+1])) for p in range(len(task_probabilities))])}]')

        prob = rnd.random()
        print(f'Probability: {prob}')


def test_args():
    print()

    def eval_args(updated_args, model, tasks, servers, repeat):
        sys.argv = ['location'] + updated_args
        args = parse_args()
        assert args.model == model and args.tasks == tasks and args.servers == servers and args.repeat == repeat

    # Files
    eval_args(['--file', 'test'], 'models/test.mdl', None, None, 0)
    eval_args(['-f', 'test'], 'models/test.mdl', None, None, 0)

    # Tasks
    eval_args(['--file', 'test', '--tasks', '1'], 'models/test.mdl', 1, None, 0)
    eval_args(['-f', 'test', '-t', '2'], 'models/test.mdl', 2, None, 0)

    # Servers
    eval_args(['--file', 'test', '--servers', '3'], 'models/test.mdl', None, 3, 0)
    eval_args(['-f', 'test', '-s', '4'], 'models/test.mdl', None, 4, 0)

    # Repeat
    eval_args(['--file', 'test', '--repeat', '5'], 'models/test.mdl', None, None, 5)
    eval_args(['-f', 'test', '-r', '6'], 'models/test.mdl', None, None, 6)

    # Full
    eval_args(['--file', 'test', '--tasks', '7', '--servers', '8', '--repeat', '9'], 'models/test.mdl', 7, 8, 9)
    eval_args(['-f', 'test', '-t', '10', '-s', '11', '-r', '12'], 'models/test.mdl', 10, 11, 12)
