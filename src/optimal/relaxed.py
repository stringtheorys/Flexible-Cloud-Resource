"""Relaxed model with a single super server allow a upper bound to be found, solved through mixed integer programming"""

from __future__ import annotations

from time import time
from typing import List, Dict, Optional

from docplex.cp.model import CpoModel, CpoVariable
from docplex.cp.solution import CpoSolveResult
from docplex.cp.solution import SOLVE_STATUS_FEASIBLE, SOLVE_STATUS_OPTIMAL

from src.core.core import print_model, print_model_solution
from src.core.result import Result
from src.core.server import Server
from src.core.super_server import SuperServer
from src.core.task import Task


def relaxed_algorithm(tasks: List[Task], servers: List[Server], time_limit: int,
                      debug_time: bool = False) -> Optional[Result]:
    """
    Runs the optimal algorithm solution
    :param tasks: A list of tasks
    :param servers: A list of servers
    :param time_limit: The time limit to solve
    :param debug_time: If to print the time taken
    :return: The result from optimal solution
    """
    start_time = time()

    model = CpoModel("Server Job Allocation")

    loading_speeds: Dict[Task, CpoVariable] = {}
    compute_speeds: Dict[Task, CpoVariable] = {}
    sending_speeds: Dict[Task, CpoVariable] = {}
    task_allocation: Dict[Task, CpoVariable] = {}

    super_server = SuperServer(servers)

    for task in tasks:
        loading_speeds[task] = model.integer_var(min=1, max=super_server.bandwidth_capacity,
                                                 name="{} loading speed".format(task.name))
        compute_speeds[task] = model.integer_var(min=1, max=super_server.computation_capacity,
                                                 name="{} compute speed".format(task.name))
        sending_speeds[task] = model.integer_var(min=1, max=super_server.bandwidth_capacity,
                                                 name="{} sending speed".format(task.name))
        task_allocation[task] = model.binary_var(name="{} allocation".format(task.name))

        model.add(task.required_storage / loading_speeds[task] +
                  task.required_computation / compute_speeds[task] +
                  task.required_results_data / sending_speeds[task] <= task.deadline)

    model.add(sum(task.required_storage * task_allocation[task]
                  for task in tasks) <= super_server.storage_capacity)
    model.add(sum(compute_speeds[task] * task_allocation[task]
                  for task in tasks) <= super_server.computation_capacity)
    model.add(sum((loading_speeds[task] + sending_speeds[task]) * task_allocation[task]
                  for task in tasks) <= super_server.bandwidth_capacity)

    model.maximize(sum(task.value * task_allocation[task] for task in tasks))

    # Run the model
    model_solution: CpoSolveResult = model.solve(log_output=None, RelativeOptimalityTolerance=0.01,
                                                 TimeLimit=time_limit)
    if debug_time:
        print("Solve time: {} secs, Objective value: {}, bounds: {}, gaps: {}"
              .format(round(model_solution.get_solve_time(), 2), model_solution.get_objective_values(),
                      model_solution.get_objective_bounds(), model_solution.get_objective_gaps()))

    # Check that it is solved
    if model_solution.get_solve_status() != SOLVE_STATUS_FEASIBLE and \
            model_solution.get_solve_status() != SOLVE_STATUS_OPTIMAL:
        print("Optimal algorithm failed")
        print_model_solution(model_solution)
        print_model(tasks, servers)
        return None

    # For each of the tasks allocate if allocated to the server
    for task in tasks:
        if model_solution.get_value(task_allocation[task]):
            task.allocate(model_solution.get_value(loading_speeds[task]),
                          model_solution.get_value(compute_speeds[task]),
                          model_solution.get_value(sending_speeds[task]), super_server)
            super_server.allocate_task(task)

    return Result("Relaxed", tasks, [super_server], time() - start_time, solve_status=model_solution.get_solve_status())