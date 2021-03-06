"""
Test the model distribution files
"""

import os
import random as rnd
import sys
from math import ceil

import numpy as np
import pandas as pd
from tqdm import tqdm

from core.task import Task
from src.core.core import reset_model
from src.core.fixed_task import SumSpeedPowFixedAllocationPriority, FixedTask, SumSpeedsFixedAllocationPriority
from src.extra.io import parse_args
from src.extra.model import ModelDistribution
from src.greedy.greedy import greedy_algorithm
from src.greedy.resource_allocation_policy import SumPercentage
from src.greedy.server_selection_policy import SumResources
from src.greedy.task_prioritisation import UtilityDeadlinePerResource
from src.optimal.fixed_optimal import fixed_optimal


def test_model_distribution():
    print()
    files = os.listdir('../models/')
    for file in files:
        print(file)
        if not os.path.isdir(f'../models/{file}'):
            if file == "caroline.mdl":
                model_dist = ModelDistribution('../models/caroline.mdl', num_tasks=2)

                tasks, servers = model_dist.generate()
                assert len(tasks) == 2
                assert len(servers) == 8
            else:
                model_dist = ModelDistribution(f'../models/{file}', num_tasks=4, num_servers=3)

                tasks, servers = model_dist.generate()
                assert len(tasks) == 4
                assert len(servers) == 3


def test_realistic_model():
    print()
    model_dist = ModelDistribution('../models/alibaba.mdl', num_tasks=10, num_servers=4)
    tasks, servers = model_dist.generate()
    fixed_tasks = [FixedTask(task, SumSpeedsFixedAllocationPriority()) for task in tasks]
    foreknowledge_fixed_tasks = [FixedTask(task, SumSpeedsFixedAllocationPriority(), resource_foreknowledge=True)
                                 for task in tasks]
    tasks, servers = model_dist.generate_online(10, 2, 0)

    print(fixed_tasks)
    print(foreknowledge_fixed_tasks)
    print(tasks, servers)


def alibaba_task_generation():
    """
    Tests if the task generation for the alibaba dataset is valid
    """
    print()
    model_dist = ModelDistribution('../models/alibaba.mdl', num_tasks=10, num_servers=4)
    servers = model_dist.generate_servers()
    alibaba = pd.read_csv('../models/alibaba_cluster_tasks.csv')
    storage_scaling, computational_scaling, results_data_scaling = 500, 1, 5
    fixed_task_policy = SumSpeedsFixedAllocationPriority()
    # 74, 2984, 4780, 6602, 10999 failed
    for index, task_row in tqdm(alibaba.iterrows()):
        task = Task(f'realistic {index}',
                    required_storage=ceil(storage_scaling * min(1.2 * task_row['mem_max'], task_row['plan_mem'])),
                    required_computation=ceil(computational_scaling * 1.2 * task_row['total_cpu']),
                    required_results_data=ceil(results_data_scaling * rnd.randint(20, 60) * task_row['mem_max']),
                    value=None, deadline=task_row['time_taken'], servers=servers,
                    planned_storage=ceil(storage_scaling * task_row['plan_mem']),
                    planned_computation=ceil(computational_scaling * task_row['plan_cpu']))
        try:
            FixedTask(task, fixed_task_policy)
        except AssertionError as e:
            print(f'Error for fixed task index {index}', e)
            print(task.required_storage/storage_scaling, task.required_computation/computational_scaling,
                  task.required_results_data/results_data_scaling)
        try:
            FixedTask(task, fixed_task_policy, resource_foreknowledge=True)
        except AssertionError as e:
            print(f'Error for foreknowledge fixed task index {index}', e)
            print(task.required_storage / storage_scaling, task.required_computation / computational_scaling,
                  task.required_results_data / results_data_scaling,
                  task.required_results_data / (results_data_scaling * task_row['mem_max']))


def test_args():
    print()

    def eval_args(updated_args, model, tasks, servers, repeat):
        """
        Evaluates the arguments by updating the arguments and then testing the model, tasks, servers and repeat are
            equalled to the parsed arguments

        :param updated_args: List of updated args
        :param model: Value for the model location
        :param tasks: Value for the number of tasks
        :param servers: Value for the number of servers
        :param repeat: Value for the number of repeats
        """
        sys.argv = ['location'] + updated_args
        args = parse_args()
        assert args.model == model and args.tasks == tasks and args.servers == servers and args.repeat == repeat

    # Files
    eval_args(['--file', 'test'], '../models/synthetic.mdl', None, None, 0)
    eval_args(['-f', 'test'], '../models/synthetic.mdl', None, None, 0)

    # Tasks
    eval_args(['--file', 'test', '--tasks', '1'], '../models/synthetic.mdl', 1, None, 0)
    eval_args(['-f', 'test', '-t', '2'], '../models/synthetic.mdl', 2, None, 0)

    # Servers
    eval_args(['--file', 'test', '--servers', '3'], '../models/synthetic.mdl', None, 3, 0)
    eval_args(['-f', 'test', '-s', '4'], '../models/synthetic.mdl', None, 4, 0)

    # Repeat
    eval_args(['--file', 'test', '--repeat', '5'], '../models/synthetic.mdl', None, None, 5)
    eval_args(['-f', 'test', '-r', '6'], '../models/synthetic.mdl', None, None, 6)

    # Full
    eval_args(['--file', 'test', '--tasks', '7', '--servers', '8', '--repeat', '9'], '../models/synthetic.mdl', 7, 8, 9)
    eval_args(['-f', 'test', '-t', '10', '-s', '11', '-r', '12'], '../models/synthetic.mdl', 10, 11, 12)


def test_model_tasks(model_file: str = '../models/synthetic.mdl', num_servers=8):
    greedy_results = []
    fixed_results = []
    for num_tasks in range(24, 60, 4):
        model = ModelDistribution(model_file, num_tasks=num_tasks, num_servers=num_servers)
        tasks, servers = model.generate()
        fixed_tasks = [FixedTask(task, SumSpeedPowFixedAllocationPriority()) for task in tasks]

        greedy_results.append([num_tasks, greedy_algorithm(tasks, servers, UtilityDeadlinePerResource(),
                                                           SumResources(), SumPercentage())])
        reset_model(tasks, servers)
        fixed_results.append([num_tasks, fixed_optimal(fixed_tasks, servers, 3)])

    def print_results(results):
        """
        Print the results of an algorithm

        :param results: List of results
        """
        print(f'Num of Tasks | Percent Tasks | Percent Social Welfare | Storage usage | Comp usage | Bandwidth usage')
        for task_num, result in results:
            # noinspection PyTypeChecker
            print(f' {task_num:11} | {result.percentage_tasks_allocated:^13} | '
                  f'{result.percentage_social_welfare:^22} | '
                  f'{round(np.mean(list(result.server_storage_used.values())), 3):^13} | '
                  f'{round(np.mean(list(result.server_computation_used.values())), 3):^10} | '
                  f'{round(np.mean(list(result.server_bandwidth_used.values())), 3):10}')

    print('\n\n\tGreedy algorithm')
    print_results(greedy_results)
    print('\n\tFixed Tasks')
    print_results(fixed_results)

    print(f'\nNum of Tasks | Difference | Greedy SW | Fixed SW')
    for (num_tasks, greedy_result), (_, fixed_result) in zip(greedy_results, fixed_results):
        print(f' {num_tasks:11} | {fixed_result.social_welfare - greedy_result.social_welfare:10} | '
              f'{greedy_result.social_welfare:9} | {fixed_result.social_welfare:8}')


def test_iridis_model():
    # PYTHONPATH=./src/ python3 tests/test_models.py -f='caroline' -t='28' -s='', -r='0' -e='test message'
    loaded_args = parse_args()
    print(f'Model file: {loaded_args.file}, tasks: {loaded_args.tasks}, servers: {loaded_args.servers}, '
          f'repeat: {loaded_args.repeat}, extra: "{loaded_args.extra}"')

    ModelDistribution(loaded_args.file, loaded_args.tasks, loaded_args.servers)
    if loaded_args.extra == 'test message':
        print('success')
    else:
        print('failure')


if __name__ == "__main__":
    alibaba_task_generation()
