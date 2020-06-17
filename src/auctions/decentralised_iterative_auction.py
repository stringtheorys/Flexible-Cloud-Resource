"""
Todo add general explanation for decentralised iterative auction
"""

from __future__ import annotations

import functools
import math
import random as rnd
from abc import ABC, abstractmethod
from time import time
from typing import TYPE_CHECKING, Tuple

from docplex.cp.model import CpoModel, SOLVE_STATUS_FEASIBLE, SOLVE_STATUS_OPTIMAL

from core.core import reset_model, allocate, debug
from core.result import Result
from greedy.value_density import ResourceSum

if TYPE_CHECKING:
    from typing import List

    from greedy.resource_allocation_policy import ResourceAllocationPolicy
    from core.server import Server
    from core.task import Task
    from greedy.value_density import ValueDensity


class PriceDensity(ABC):
    """Price density function class that is inherited with each option"""

    def __init__(self, name):
        self.name = name

    @abstractmethod
    def evaluate(self, task: Task) -> float:
        """Price density function"""
        pass


class PriceResourcePerDeadline(PriceDensity):
    """The product of utility and deadline divided by required resources"""

    def __init__(self, resource_func: ValueDensity = ResourceSum()):
        PriceDensity.__init__(self, f'Price * {resource_func.name} / deadline')
        self.resource_func = resource_func

    def evaluate(self, task: Task) -> float:
        """Value density function"""
        return task.price * self.resource_func.evaluate(task) / task.deadline


def allocate_task(new_task, task_price, server, unallocated_tasks, task_speeds):
    """
    Allocates a task to a server

    :param new_task: The new task to allocate to the server
    :param task_price: The price for the task
    :param server: The server to be allocated to the server
    :param unallocated_tasks: List of unallocated tasks
    :param task_speeds: Dictionary of task speeds
    """
    server.reset_allocations()

    # For each of the task, if the task is allocated then allocate the task or reset the task
    new_task.price = task_price
    for task, (loading, compute, sending, allocated) in task_speeds.items():
        task.reset_allocation(forgot_price=False)
        if allocated:
            allocate(task, loading, compute, sending, server)
        else:
            task.price = 0
            unallocated_tasks.append(task)


def greedy_task_price(new_task: Task, server: Server, price_density: PriceDensity,
                      resource_allocation_policy: ResourceAllocationPolicy):
    """
    Calculates the task price using greedy algorithm

    :param new_task: The new task
    :param server: Server
    :param price_density: Price density function
    :param resource_allocation_policy: Resource allocation policy
    :return: Tuple of task price and possible speeds
    """
    current_speeds = {task: (task.loading_speed, task.compute_speed, task.sending_speed)
                      for task in server.allocated_tasks}
    tasks = server.allocated_tasks[:]
    server_revenue = server.revenue
    reset_model(server.allocated_tasks, (server,), forgot_price=False)

    s, w, r = resource_allocation_policy.allocate(new_task, server)
    allocate(new_task, s, w, r, server)

    for task in sorted(tasks, key=lambda task: price_density.evaluate(task)):
        if server.can_run(task):
            s, w, r = resource_allocation_policy.allocate(new_task, server)
            allocate(task, s, w, r, server)

    task_price = server_revenue - server.revenue + server.price_change
    possible_speeds = {
        task: (task.loading_speed, task.compute_speed, task.sending_speed, task.running_server is not None)
        for task in tasks + [new_task]}

    reset_model(current_speeds.keys(), (server,))
    new_task.reset_allocation()

    for task, (loading, compute, sending) in current_speeds.items():
        allocate(task, loading, compute, sending, server)

    return task_price, possible_speeds


def optimal_task_price(new_task: Task, server: Server, time_limit: int, debug_results: bool = False):
    """
    Calculates the task price

    :param new_task: The new task
    :param server: The server
    :param time_limit: Time limit for the cplex
    :param debug_results: debug the results
    :return: task price and task speeds
    """
    assert 0 < time_limit, f'Time limit: {time_limit}'
    model = CpoModel(f'{new_task.name} Task Price')

    # Add the new task to the list of server allocated tasks
    tasks = server.allocated_tasks + [new_task]

    # Create all of the resource speeds variables
    loading_speed = {task: model.integer_var(min=1, max=server.bandwidth_capacity - 1) for task in tasks}
    compute_speed = {task: model.integer_var(min=1, max=server.computation_capacity) for task in tasks}
    sending_speed = {task: model.integer_var(min=1, max=server.bandwidth_capacity - 1) for task in tasks}
    # Create all of the allocation variables however only on the currently allocated tasks
    allocation = {task: model.binary_var(name=f'{task.name} Task allocated') for task in server.allocated_tasks}

    # Add the deadline constraint
    for task in tasks:
        model.add((task.required_storage / loading_speed[task]) +
                  (task.required_computation / compute_speed[task]) +
                  (task.required_results_data / sending_speed[task]) <= task.deadline)

    # Add the server resource constraints
    model.add(sum(task.required_storage * allocated for task, allocated in allocation.items()) +
              new_task.required_storage <= server.storage_capacity)
    model.add(sum(compute_speed[task] * allocated for task, allocated in allocation.items()) +
              compute_speed[new_task] <= server.computation_capacity)
    model.add(sum((loading_speed[task] + sending_speed[task]) * allocated for task, allocated in allocation.items()) +
              (loading_speed[new_task] + sending_speed[new_task]) <= server.bandwidth_capacity)

    # The optimisation function
    model.maximize(sum(task.price * allocated for task, allocated in allocation.items()))

    # Solve the model with a time limit
    model_solution = model.solve(log_output=None, TimeLimit=time_limit)

    # If the model solution failed then return an infinite price
    if model_solution.get_solve_status() != SOLVE_STATUS_FEASIBLE and \
            model_solution.get_solve_status() != SOLVE_STATUS_OPTIMAL:
        print(f'Cplex model failed - status: {model_solution.get_solve_status()}')
        return math.inf, {}

    # Get the max server profit that the model finds and calculate the task price through a vcg similar function
    new_server_revenue = model_solution.get_objective_values()[0]
    task_price = server.revenue - new_server_revenue + server.price_change

    # Get the resource speeds and task allocations
    speeds = {
        task: (model_solution.get_value(loading_speed[task]),
               model_solution.get_value(compute_speed[task]),
               model_solution.get_value(sending_speed[task]),
               model_solution.get_value(allocation[task]) if task in allocation else True)
        for task in tasks
    }

    debug(f'Sever: {server.name} - Prior revenue: {server.revenue}, new revenue: {new_server_revenue}, '
          f'price change: {server.price_change} therefore task price: {task_price}', debug_results)

    return task_price, speeds


def dia_solver(tasks: List[Task], servers: List[Server], task_price_solver,
               debug_allocation: bool = False) -> Tuple[int, float]:
    """
    Decentralised iterative auction solver

    :param tasks: List of tasks
    :param servers: List of servers
    :param task_price_solver: Task price solver
    :param debug_allocation: If to debug allocation
    :return: A tuple with the number of rounds and the solver time length
    """
    start_time = time()

    rounds: int = 0
    unallocated_tasks: List[Task] = tasks[:]
    while unallocated_tasks:
        task: Task = unallocated_tasks.pop(rnd.randint(0, len(unallocated_tasks)-1))

        min_price, min_speeds, min_server = -1, None, None
        for server in servers:
            price, speeds = task_price_solver(task, server)

            if min_price == -1 or price < min_price:
                min_price, min_speeds, min_server = price, speeds, server

        if min_price == -1 or task.value < min_price:
            debug(f'{task.name} Task set to {min_server.name} with price {min_price}', debug_allocation)
            allocate_task(task, min_price, min_server, unallocated_tasks, *min_speeds)
        else:
            debug(f'Removing {task.name} Task, min price is {min_price} and task value is {task.value}', debug_allocation)

        debug(f'Number of unallocated tasks: {len(unallocated_tasks)}\n', debug_allocation)
        rounds += 1

    return rounds, time() - start_time


def optimal_decentralised_iterative_auction(tasks: List[Task], servers: List[Server], time_limit: int = 5,
                                            debug_allocation: bool = False) -> Result:
    """
    Runs the optimal decentralised iterative auction

    :param tasks: List of tasks
    :param servers: list of servers
    :param time_limit: The time limit for the dia solver
    :param debug_allocation: If to debug allocation
    :return: The results of the auction
    """
    solver = functools.partial(optimal_task_price, time_limit=time_limit)
    rounds, solve_time = dia_solver(tasks, servers, solver, debug_allocation)

    return Result('Optimal DIA', tasks, servers, solve_time, is_auction=True,
                  **{'price change': {server.name: server.price_change for server in servers}, 'rounds': rounds})


def greedy_decentralised_iterative_auction(tasks: List[Task], servers: List[Server], price_density: PriceDensity,
                                           resource_allocation_policy: ResourceAllocationPolicy,
                                           debug_allocation: bool = False) -> Result:
    """
    Runs the greedy decentralised iterative auction

    :param tasks: List of tasks
    :param servers: List of servers
    :param price_density: Price density policy
    :param resource_allocation_policy: Resource allocation policy
    :param debug_allocation: If to debug allocation
    :return: The results of the auction
    """
    solver = functools.partial(greedy_task_price, price_density, resource_allocation_policy)
    rounds, solve_time = dia_solver(tasks, servers, solver, debug_allocation)

    return Result('Greedy DIA', tasks, servers, solve_time, is_auction=True,
                  **{'price change': {server.name: server.price_change for server in servers}, 'rounds': rounds})
