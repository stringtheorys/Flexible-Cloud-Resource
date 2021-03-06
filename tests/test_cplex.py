"""
Tests using cplex for optimal solutions with cp and mp models
"""

from __future__ import annotations

from docplex.cp.model import CpoModel, SOLVE_STATUS_OPTIMAL

from branch_bound.branch_bound import branch_bound_algorithm
from core.core import reset_model
from extra.model import ModelDistribution
from optimal.flexible_optimal import flexible_optimal


def test_cplex():
    model = CpoModel('test')
    x = model.integer_var(name='x')
    model.minimize(5 * x ** 2 - 10 * x + 1)

    solution = model.solve()
    assert solution.get_solve_status() == SOLVE_STATUS_OPTIMAL


def test_cp_optimality():
    model = ModelDistribution('../models/synthetic.mdl', 20, 3)
    tasks, servers = model.generate()

    results = flexible_optimal(tasks, servers, time_limit=10)
    print(results.store())


def test_branch_bound():
    model = ModelDistribution('../models/synthetic.mdl', 4, 2)
    tasks, servers = model.generate()

    branch_bound_result = branch_bound_algorithm(tasks, servers, debug_update_lower_bound=True)
    branch_bound_result.pretty_print()

    reset_model(tasks, servers)

    optimal_result = flexible_optimal(tasks, servers, time_limit=200)
    optimal_result.pretty_print()
