import unittest
from core import Scenario

class MyTestCase(unittest.TestCase):

    def test_load_and_run(self) -> None:

        scenario = Scenario('../../cfg/intersection.json',validate=True)

        scenario.request_outputs(
            output_folder = '../../output',
            prefix = 'run1',
            requests = [
                # { 'type':'link_flw', 'dt':'10','links':'1,2,3,4,5,6,7,8' },
                # { 'type':'link_veh', 'dt':'1', 'links':'1,2,3,4,5,6,7,8' },
                # { 'type':'lg_flw', 'dt':'10', 'links':'1,2,3,4,5,6,7,8' },
                # { 'type':'lg_veh', 'dt':'10', 'links':'1,2,3,4,5,6,7,8' },
                # { 'type':'veh_events', 'links':'1,2,3,4,5,6,7,8' },
                { 'type':'cnt_events', 'ids':'0' }
            ]
        )

        scenario.initialize(output_prefix='out/a',validate=True)
        scenario.run(duration=500)
        self.assertTrue(True)
