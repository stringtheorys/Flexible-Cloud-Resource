"""Implementation of a priority queue using a binary heap"""

from __future__ import annotations

from enum import Enum, auto
from math import log2, ceil
from typing import List, Generic, TypeVar, Callable

T = TypeVar('T')


class Comparison(Enum):
    """
    Comparison types
    """
    GREATER = auto()
    EQUAL = auto()
    LESS = auto()

    @staticmethod
    def compare(value_1: float, value_2: float) -> Comparison:
        """
        Evaluate the two values to return the comparison
        :param value_1: The value
        :param value_2: The value
        :return: Ordering of the values
        """
        if value_1 > value_2:
            return Comparison.GREATER
        elif value_2 > value_1:
            return Comparison.LESS
        else:
            return Comparison.EQUAL


class PriorityQueue(Generic[T]):
    """
    A custom binary heap for the nodes of the branch and bound algorithm
    """

    queue: List[T] = []
    size: int = 0

    def __init__(self, comparator: Callable[[T, T], Comparison]):
        self.comparator = comparator

    def pop(self) -> T:
        """
        Remove the head element of the queue
        :return: The head of the queue
        """
        if self.size == 1:
            return self.queue.pop(0)

        pop_value = self.queue[0]
        self.queue[0] = self.queue.pop(-1)
        self.size -= 1

        pos = 0
        while True:
            left, right, largest = self.left(pos), self.right(pos), pos

            if left < self.size and self.comparator(self.queue[pos], self.queue[left]) == Comparison.GREATER:
                largest = left
            if right < self.size and self.comparator(self.queue[largest], self.queue[right]) == Comparison.GREATER:
                largest = right

            if largest == pos:
                break
            else:
                self.swap(pos, largest)
                pos = largest

        return pop_value

    def push(self, data: T):
        """
        Pushes the data to the queue
        :param data: The data to add
        """
        self.queue.append(data)
        self.size += 1

        pos = self.size - 1
        parent = self.parent(pos)
        while pos > 0 and self.comparator(self.queue[parent], self.queue[pos]) == Comparison.GREATER:
            self.swap(pos, parent)

            pos = parent
            parent = self.parent(pos)

    def push_all(self, data: List[T]):
        """
        Push all of the data
        :param data: List of data to add to the queue
        """
        for d in data:
            self.push(d)

    @staticmethod
    def parent(pos: int) -> int:
        """
        Gets the parent position of the pos in the tree
        :param pos: Position
        :return: Parent position
        """
        return (pos - 1) // 2

    @staticmethod
    def left(pos: int) -> int:
        """
        Gets the left child position of the pos in the tree
        :param pos: Position
        :return: Left position
        """
        return 2 * pos + 1

    @staticmethod
    def right(pos: int) -> int:
        """
        Gets the right child position of the pos in the tree
        :param pos: Position
        :return: Right position
        """
        return 2 * pos + 2

    def swap(self, child: int, parent: int):
        """
        Swap the child and parent positions in the list
        :param child: The child position
        :param parent: The parent position
        """
        temp = self.queue[child]
        self.queue[child] = self.queue[parent]
        self.queue[parent] = temp

    def __str__(self) -> str:
        """
        Returns a string of the queue
        :return: String of the queue
        """
        return '[' + ', '.join(self.queue) + ']'
    
    def pretty_print(self):
        level: List[int] = [0]
        left_padding: int = ((2 ** ceil(log2(self.size+1))) - 1) // 2
        center_padding: int = 0
        value_size = max(len('{}'.format(value)) for value in self.queue) * ' '
        while level:
            new_level: List[int] = []
            print(value_size * left_padding, end="")
            for pos in level:
                print(self.queue[pos] + value_size * center_padding, end="")
                if self.left(pos) < self.size:
                    new_level.append(self.left(pos))
                if self.right(pos) < self.size:
                    new_level.append(self.right(pos))
            print()
            level = new_level
            center_padding = left_padding
            left_padding = (left_padding - 1) // 2