import unittest
from core import Scenario

class MyTestCase(unittest.TestCase):

    def test_load_and_run(self) -> None:

        scenario = Scenario('intersection.json',validate=True)

        scenario.request_outputs()
        scenario.initialize(output_prefix='out/a',validate=True)
        scenario.run(duration=100)

        print(scenario)


    def test_priority_queue(self) -> None:

        from queue import PriorityQueue

        q:PriorityQueue = PriorityQueue()
        q.put(10)
        q.put(1)
        q.put(5)
        while not q.empty():
            print(q.get())


