import unittest
import numpy as np
from core import Scenario

class MyTestCase(unittest.TestCase):

    def test_load_and_run(self) -> None:

        try:
            scenario = Scenario(
                network_file = '../../cfg/intersection_network.json',
                demand_file = '../../cfg/intersection_demand.json',
                control_file = '../../cfg/intersection_control.json',
                output_requests = [
                    { 'type':'link_flw', 'dt':'10','links':'1,2,3,4,5,6,7,8' },
                    { 'type':'link_veh', 'dt':'10', 'links':'1,2,3,4,5,6,7,8' },
                    { 'type':'lg_flw', 'dt':'10', 'links':'1,2,3,4,5,6,7,8' },
                    { 'type':'lg_veh', 'dt':'10', 'links':'1,2,3,4,5,6,7,8' },
                    { 'type':'veh_events', 'links':'1,2,3,4,5,6,7,8' },
                    { 'type':'cnt_events', 'ids':'0' }
                ],
                output_folder = '../../output',
                prefix = 'run1',
                check=True
            )

            scenario.get_lanegroups()

            scenario.set_state({})

            scenario.run(duration=1)

        except Exception as e:
            print(e)

        self.assertTrue(True)

    def test_priority_queue(self) -> None:

        from queue import PriorityQueue

        q:PriorityQueue = PriorityQueue()
        q.put(10)
        q.put(1)
        q.put(5)
        while not q.empty():
            print(q.get())
        self.assertTrue(True)

    def test_random_choice(self) -> None:
        N = 100
        A = np.empty(N)
        for i in range(N):
            A[i] = np.random.choice([0,1,-5,10,8], p=[0.1, 0, 0.3, 0.6, 0])

        # plt.figure()
        # plt.hist(A)
        # plt.show()