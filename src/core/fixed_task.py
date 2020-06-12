"""Fixed Job class"""

from __future__ import annotations

from abc import abstractmethod, ABC

from docplex.cp.model import CpoModel

from src.core.server import Server
from src.core.task import Task


class FixedTask(Task):
    """Job with a fixing resource usage speed"""

    def __init__(self, task: Task, fixed_value: FixedValue, fixed_name: bool = True):
        name = "Fixed " + task.name if fixed_name else task.name
        super().__init__(name, task.required_storage, task.required_computation, task.required_results_data,
                         task.value, task.deadline)
        self.original_task = task
        self.loading_speed, self.compute_speed, self.sending_speed = self.find_fixed_speeds(fixed_value)

    def find_fixed_speeds(self, fixed_value: FixedValue):
        """
        Find the optimal fixed speeds of the task
        :param fixed_value: The fixed value function to value the speeds
        :return:
        """
        model = CpoModel("Speeds")
        loading_speed = model.integer_var(min=1)
        compute_speed = model.integer_var(min=1)
        sending_speed = model.integer_var(min=1)

        model.add(self.required_storage / loading_speed +
                  self.required_computation / compute_speed +
                  self.required_results_data / sending_speed <= self.deadline)

        model.minimize(fixed_value.evaluate(loading_speed, compute_speed, sending_speed))

        model_solution = model.solve(log_output=None)

        return model_solution.get_value(loading_speed), \
               model_solution.get_value(compute_speed), \
               model_solution.get_value(sending_speed)

    def allocate(self, loading_speed: int, compute_speed: int, sending_speed: int, running_server: Server,
                 price: float = None):
        """
        Overrides the allocate function from task to just allocate the running server and the price
        :param loading_speed: Ignored
        :param compute_speed: Ignored
        :param sending_speed: Ignored
        :param running_server: The server the task is running on
        :param price: The price of the task
        """
        assert self.running_server is None

        self.running_server = running_server

        if price is not None:
            self.price = price

    def reset_allocation(self, forgot_price: bool = True):
        """
        Overrides the reset_allocation function from task to just change the server not resource speeds
        """
        self.running_server = None

        if forgot_price:
            self.price = 0


class FixedValue(ABC):
    """
    Fixed Value policy for the fixed task to select the speed
    """

    def __init__(self, name):
        self.name = name

    @abstractmethod
    def evaluate(self, loading_speed: int, compute_speed: int, sending_speed: int) -> int:
        """
        Evaluate how good certain speeds
        :param loading_speed: Loading speed
        :param compute_speed: Compute speed
        :param sending_speed: Sending speed
        :return: How good it is
        """
        pass


class FixedSumSpeeds(FixedValue):
    """Fixed sum of speeds"""

    def __init__(self):
        super().__init__("Sum speeds")

    def evaluate(self, loading_speed: int, compute_speed: int, sending_speed: int) -> int:
        """Evaluation of how good it is"""
        return loading_speed + compute_speed + sending_speed

# TODO add more fixed value classes