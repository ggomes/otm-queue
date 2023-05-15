import unittest
import matplotlib.pyplot as plt
from core import Scenario
import os
import pandas as pd
import json

class MyTestCase(unittest.TestCase):

    def test_load_and_run(self) -> None:

        scenario = Scenario(
            network_file = '../../cfg/intersection_network.json',
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
            check=True,
            random_seed=24724
        )

        lg_ids = scenario.get_lanegroup_ids()

        lg2nextlinks = scenario.get_lg2nextlinks()

        # populate vehicles dict
        vehicles = dict()
        for lg in lg_ids:
            linkid = lg[0]
            startlane = lg[1]
            nextlinkids = lg2nextlinks[lg]
            if len(nextlinkids)==0:
                vehicles[(linkid, startlane, 'w')] = 1
                vehicles[(linkid, startlane, 't')] = 1
            else:
                for nextlinkid in nextlinkids:
                    vehicles[(linkid, startlane, 'w', nextlinkid)] = 1
                    vehicles[(linkid, startlane, 't', nextlinkid)] = 1

        # load inputs
        with open('../../cfg/intersection_input.json') as f:
            inputs = json.load(f)

        scenario.set_state_and_inputs(
            demands = inputs['demands'],
            splits = inputs['splits'],
            vehicles = vehicles,
            check = True
        )

        scenario.advance(duration=1000)

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