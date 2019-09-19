"""Combinatorial Double Auction"""

from __future__ import annotations

from math import exp
from time import time
from typing import List, Dict, Optional

from docplex.cp.model import CpoModel
from docplex.cp.solution import SOLVE_STATUS_UNKNOWN

from core.core import allocate, list_copy_remove
from core.job import Job
from core.model import reset_model
from core.result import Result
from core.server import Server


class FixedJob(Job):
    """Job with a fixing resource usage speed"""

    def __init__(self, job, servers):
        super().__init__("fixed " + job.name, job.required_storage, job.required_computation, job.required_results_data,
                         job.value, job.deadline)
        self.original_job = job
        self.loading_speed, self.compute_speed, self.sending_speed = min(
            ((s, w, r)
             for s in range(1, max(server.max_bandwidth for server in servers))
             for w in range(1, max(server.max_computation for server in servers))
             for r in range(1, max(server.max_bandwidth for server in servers))
             if job.required_storage * w * r + s * job.required_computation * r +
             s * w * job.required_results_data <= job.deadline * s * w * r),
            key=lambda x: exp(x[0]) ** 3 + exp(x[1]) ** 3 + exp(x[2]) ** 3)

    def allocate(self, loading_speed: int, compute_speed: int, sending_speed: int, running_server: Server,
                 price: float = None):
        """
        Overrides the allocate function from job to just allocate the running server and the price
        :param loading_speed: Ignored
        :param compute_speed: Ignored
        :param sending_speed: Ignored
        :param running_server: The server the job is running on
        :param price: The price of the job
        """
        self.running_server = running_server
        self.price = price

    def reset_allocation(self):
        """
        Overrides the reset_allocation function from job to just change the server not resource speeds
        """
        self.running_server = None


def optimal_algorithm(jobs: List[FixedJob], servers: List[Server], time_limit) -> Optional[int]:
    """
    Finds the optimal solution
    :param jobs: A list of jobs
    :param servers: A list of servers
    :param time_limit: The time limit to solve with
    :return: The results
    """
    model = CpoModel("CDA")

    # As no resource speeds then only assign binary variables for the allocation
    allocations = {(job, server): model.binary_var(name='{} job {} server'.format(job.name, server.name))
                   for job in jobs for server in servers}

    # Allocation constraint
    for job in jobs:
        model.add(sum(allocations[(job, server)] for server in servers) <= 1)

    # Server resource speeds constraints
    for server in servers:
        model.add(sum(job.required_storage * allocations[(job, server)] for job in jobs) <= server.max_storage)
        model.add(sum(job.compute_speed * allocations[(job, server)] for job in jobs) <= server.max_storage)
        model.add(sum((job.loading_speed + job.sending_speed) * allocations[(job, server)]
                      for job in jobs) <= server.max_storage)

    # Optimisation
    model.maximize(sum(job.value * allocations[(job, server)] for job in jobs for server in servers))

    # Solve the cplex model with time limit
    model_solution = model.solve(log_output=None, RelativeOptimalityTolerance=0.01, TimeLimit=time_limit)
    if model_solution.get_solve_status() == SOLVE_STATUS_UNKNOWN:
        print("Fixed VCG auction failure")
        return None

    # Allocate all of the jobs
    for job in jobs:
        for server in servers:
            if model_solution.get_value(allocations[(job, server)]):
                job.running_server = server
                server.allocate_job(job)

    return sum(job.value for job in jobs if job.running_server)


def fixed_vcg_auction(jobs: List[Job], servers: List[Server], time_limit: int,
                      debug_running: bool = False,  debug_results: bool = False) -> Optional[Result]:
    """
    Combinatorial Double auction solved through VCG auction algorithm
    :param jobs: a list of jobs
    :param servers: a list of servers
    :param time_limit:The time limit
    :param debug_running: debug the running
    :param debug_results: debug the results
    :return: the results
    """
    start_time = time()

    # Generate the fixed jobs
    fixed_jobs = [FixedJob(job, servers) for job in jobs]

    # Price information
    job_prices: Dict[Job, float] = {}
    server_revenues: Dict[Server, float] = {}

    # Find the optimal solution
    if debug_running:
        print("Finding optimal")
    optimal_solution = optimal_algorithm(fixed_jobs, servers, time_limit=time_limit)
    if optimal_solution is None:
        return None
    elif debug_results:
        print("Optimal total utility: {}".format(optimal_solution))

    # Save the job and server information from the optimal solution
    allocated_jobs = [job for job in fixed_jobs if job.running_server]
    job_allocation: Dict[Job, Server] = {job: job.running_server for job in fixed_jobs}

    if debug_running:
        print("Allocated jobs: {}".format(", ".join([job.name for job in allocated_jobs])))

    # For each allocated job, find the sum of values if the job doesnt exist
    for job in allocated_jobs:
        # Reset the model and remove the job from the job list
        reset_model(fixed_jobs, servers)
        jobs_prime = list_copy_remove(fixed_jobs, job)

        # Find the optimal solution where the job doesnt exist
        if debug_running:
            print("Solving for without {} job".format(job.name))
        optimal_prime = optimal_algorithm(jobs_prime, servers, time_limit=time_limit)
        if optimal_prime is None:
            return None
        else:
            job_prices[job] = optimal_solution - optimal_prime
            if debug_results:
                print("Job {}: £{:.1f}, Value: {} ".format(job.name, job_prices[job], job.value))

    # For each server, find the sum of values if the server doesnt exist
    for server in servers:
        # Resets the model and removes the server from the server list
        reset_model(fixed_jobs, servers)
        servers_prime = list_copy_remove(servers, server)

        # Find the optimal solution where the server doesnt exist
        if debug_running:
            print("Solving for without {} server".format(server.name))
        optimal_prime = optimal_algorithm(fixed_jobs, servers_prime, time_limit=time)
        if optimal_prime is None:
            return None
        else:
            server_revenues[server] = optimal_solution - optimal_prime
            if debug_results:
                print("Server {}: £{:.1f}".format(server.name, server_revenues[server]))

    # Resets all of the jobs and servers and allocates all of their info from the original optimal solution
    reset_model(fixed_jobs, servers)
    for job in allocated_jobs:
        allocate(job, -1, -1, -1, job_allocation[job], job_prices[job])

    # Check that the job prices sum to the same value as the server revenues,
    # else the optimal solution hasn't been found at some point
    if sum(job_prices.values()) != sum(server_revenues.values()):
        print("Fixed  VCG fail as sum of job prices {} != sum of server prices {}"
              .format(sum(job_prices.values()), sum(server_revenues.values())))

    return Result('vcg', fixed_jobs, servers, time() - start_time, individual_compute_time=time_limit, show_money=True,
                  failure=sum(job_prices.values()) != sum(server_revenues.values()))