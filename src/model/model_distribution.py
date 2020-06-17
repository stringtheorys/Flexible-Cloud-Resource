"""
Model distribution
"""

from __future__ import annotations

import json
from random import random
from typing import TYPE_CHECKING

from model.server_distribution import ServerDistribution
from model.task_distribution import TaskDistribution

if TYPE_CHECKING:
    from typing import Tuple, List

    from core.server import Server
    from core.task import Task


def load_model_distribution(filename: str) -> Tuple[str, List[TaskDistribution], List[ServerDistribution]]:
    """
    Loads tasks and server distributions from a file

    :param filename: The filename to load from
    :return: A tuple of the list of random task distributions and random server distributions
    """

    with open(filename) as file:
        data = json.load(file)

        task_dists: List[TaskDistribution] = [
            TaskDistribution(dist['name'], dist['probability'],
                             dist['required_storage_mean'], dist['required_storage_std'],
                             dist['required_computation_mean'], dist['required_computation_std'],
                             dist['required_results_data_mean'], dist['required_results_data_std'],
                             dist['value_mean'], dist['value_std'],
                             dist['deadline_mean'], dist['deadline_std'])
            for dist in data['task_dist']
        ]

        server_dists: List[ServerDistribution] = [
            ServerDistribution(dist['name'], dist['probability'],
                               dist['maximum_storage_mean'], dist['maximum_storage_std'],
                               dist['maximum_computation_mean'], dist['maximum_computation_std'],
                               dist['maximum_bandwidth_mean'], dist['maximum_bandwidth_std'])
            for dist in data['server_dist']
        ]

        return data['name'], task_dists, server_dists


class ModelDistribution:
    """Model distributions"""

    num_tasks = 0
    num_servers = 0

    def __init__(self, dist_name: str, task_dists: List[TaskDistribution], num_tasks: int,
                 server_dists: List[ServerDistribution], num_servers: int):
        self.file_name = f'{dist_name}_j{num_tasks}_s{num_servers}'
        self.dist_name = dist_name

        self.task_dists = task_dists
        self.num_tasks = num_tasks
        self.server_dists = server_dists
        self.num_servers = num_servers

    def create(self) -> Tuple[List[Task], List[Server]]:
        """
        Creates a list of tasks and servers from a task and server distribution

        :return: A list of tasks and list of servers
        """
        tasks: List[Task] = []
        for task_pos in range(self.num_tasks):
            prob = random()
            for task_dist in self.task_dists:
                if prob < task_dist.probability:
                    tasks.append(task_dist.create_task(task_pos))
                    break
                else:
                    prob -= task_dist.probability

        servers: List[Server] = []
        for server_pos in range(self.num_servers):
            prob = random()
            for server_dist in self.server_dists:
                if prob < server_dist.probability:
                    servers.append(server_dist.create_server(server_pos))
                    break
                else:
                    prob -= server_dist.probability

        return tasks, servers


def results_filename(test_name: str, model_dist: ModelDistribution, repeat: int = None) -> str:
    """
    Generates the save filename for testing results

    :param test_name: The test name
    :param model_dist: The model distribution
    :param repeat: The repeat number
    :return: The concatenation of the test name, model distribution name and the repeat
    """
    if repeat is None:
        return f'{test_name}_{model_dist}.json'
    else:
        return f'{test_name}_{model_dist}_{repeat}.json'