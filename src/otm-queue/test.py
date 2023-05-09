import unittest
import matplotlib.pyplot as plt
from core import Scenario
import os
import pandas as pd

class MyTestCase(unittest.TestCase):

    def test_load_and_run(self) -> None:

        scenario = Scenario(
            network_file = '../../cfg/intersection_network.json',
            demand_file = '../../cfg/intersection_demand.json',
            control_file = '../../cfg/intersection_control.json',
            output_requests = [
                { 'type':'link_flw', 'dt':'1','links':'1,2,3,4,5,6,7,8' },
                { 'type':'link_veh', 'dt':'1', 'links':'1,2,3,4,5,6,7,8' },
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
        scenario.run(duration=1000)

    def test_plot(self) -> None:

        output_folder = '../../output'
        prefix = 'run1'

        filename = os.path.join(output_folder,f"{prefix}_linkveh.csv")
        linkvehs = pd.read_csv(filename)
        plt.figure(figsize=(10, 3))
        plt.plot(linkvehs['time'], linkvehs['2'], label='2')
        plt.plot(linkvehs['time'], linkvehs['5'], label='5')
        plt.plot(linkvehs['time'], linkvehs['7'], label='7')
        plt.legend()
        plt.show()