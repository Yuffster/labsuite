import unittest
from labsuite.util import ExceptionProxy

class YakNotShavedException(Exception): pass
class ChoreException(Exception): pass
class RakeException(ChoreException): pass
class MowerException(ChoreException): pass
class HoseException(ChoreException): pass

class TodoList():

    _name = ""  # The name of the list.
    _tasks = None  # [] str of tasks.
    _shed = None  # List of items in the shed.

    def __init__(self, name, **items):
        self._name = name  # Honestly just using the names to debug.
        self._tasks = []
        self._shed = []
        for k in items:
            if items[k] is True:
                self.add_item(k)

    def add_task(self, task):
        self._tasks.append(task)

    def add_item(self, item):
        """ Puts an item back in the shed. """
        if item not in self._shed:
            self._shed.append(item)

    def mow_lawn(self):
        if 'mower' in self._shed:
            self.add_task('mow_lawn')
        else:
            raise MowerException("No lawn mower found.")

    def rake_leaves(self):
        if 'rake' in self._shed:
            self.add_task('rake leaves')
        else:
            raise RakeException("No rake found.")

    def wash_car(self):
        if 'hose' in self._shed:
            self.add_task('wash car')
        else:
            raise HoseException("No hose found.")

    def get_yak(self):
        raise YakNotShavedException("Yak not shaved.")

    def __add__(self, b):
        """ Not a robust example to draw from. """
        c = TodoList(self._name)
        c._shed = self._shed
        c._tasks = self._tasks
        b.reapply(c)
        return c


class PartialTodo(ExceptionProxy): pass


class ExceptionProxyTest(unittest.TestCase):

    def test_normal_behavior(self):
        todo = TodoList('saturday')
        with self.assertRaises(RakeException):
            todo.rake_leaves()
        with self.assertRaises(HoseException):
            todo.wash_car()
        with self.assertRaises(MowerException):
            todo.mow_lawn()
        with self.assertRaises(YakNotShavedException):
            todo.get_yak()

    def test_partial_with_no_allowed_exceptions(self):
        todo = PartialTodo(TodoList('sunday'))
        with self.assertRaises(RakeException):
            todo.rake_leaves()
        with self.assertRaises(HoseException):
            todo.wash_car()
        with self.assertRaises(MowerException):
            todo.mow_lawn()
        with self.assertRaises(YakNotShavedException):
            todo.get_yak()

    def test_partial_with_list_of_allowed_exceptions(self):
        todo = PartialTodo(TodoList('sunday'), RakeException, HoseException)
        todo.rake_leaves()
        todo.wash_car()
        with self.assertRaises(MowerException):
            todo.mow_lawn()
        with self.assertRaises(YakNotShavedException):
            todo.get_yak()

    def test_partial_with_list_of_subclassed_allowed_exceptions(self):
        todo = PartialTodo(TodoList('sunday'), RakeException, ChoreException)
        todo.rake_leaves()
        todo.wash_car()
        todo.mow_lawn()
        with self.assertRaises(YakNotShavedException):
            todo.get_yak()

    def test_concatination(self):
        t1 = PartialTodo(TodoList('saturday'), HoseException)
        t2 = PartialTodo(TodoList('sunday'), RakeException)
        t1.wash_car()  # Hose exception caught.
        t2.rake_leaves()  # Rake exception caught.
        with self.assertRaises(RakeException):
            t1 + t2  # t1 doesn't allow for RakeExceptions.
        with self.assertRaises(HoseException):
            t2 + t1  # t2 doesn't allow for HoseExceptions.
        # t3 allows both types.
        t3 = PartialTodo(TodoList('monday'), HoseException, RakeException)
        t4 = t3 + t1 + t2
        self.assertEqual(len(t4.problems), 2)
        self.assertEqual(len(t3.problems), 0)  # Make sure t3 isn't modified.
        t5 = TodoList('tuesday', hose=True, rake=True)
        t6 = t5 + t1 + t2
        t7 = TodoList('wednesday', hose=True)
        with self.assertRaises(RakeException):
            t7 + t1 + t2
        t8 = TodoList('thursday', rake=True)
        with self.assertRaises(HoseException):
            t8 + t1 + t2

    def test_application(self):
        t1 = TodoList('monday', rake=True)
        t1.rake_leaves()
        t2 = PartialTodo(TodoList('saturday'), HoseException)
        t2.wash_car()
        with self.assertRaises(HoseException):
            t1 + t2
        t1.add_item('hose')  # Add a hose so we can wash the car.
        t3 = t1 + t2
        self.assertEqual(t3._tasks, ['rake leaves', 'wash car'])
