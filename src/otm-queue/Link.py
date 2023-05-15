from typing import TYPE_CHECKING, Optional
import numpy as np
from SimpleClasses import RoadParams
import random

if TYPE_CHECKING:
    from Splits import SplitMatrixProfile
    from LaneGroup import LaneGroup
    from core import Node
    from Events import Dispatcher
    from Vehicle import Vehicle

class Link:

    id: int
    full_lanes: int
    length: float
    startnode: 'Node'
    endnode: 'Node'
    roadparam: RoadParams
    split_profile: Optional['SplitMatrixProfile']
    lgs: list['LaneGroup']
    is_source: bool
    is_sink: bool

    # nextlink -> lanegroups in this link from which nextlink is reachable
    nextlink2mylgs: dict[int, list['LaneGroup']]

    def __init__(self,network,linkid:int,jsonlink:dict,roadparam:dict) -> None:

        self.id = linkid
        self.full_lanes = int(jsonlink['full_lanes'])
        self.length = float(jsonlink['length'])
        self.startnode = network.nodes[int(jsonlink['start'])]
        self.startnode.add_output_link(self)
        self.endnode = network.nodes[int(jsonlink['end'])]
        self.endnode.add_input_link(self)
        self.roadparam = RoadParams(capacity = float(roadparam['capacity']),
                                    speed =  float(roadparam['speed']),
                                    jam_density =  float(roadparam['jam_density']) )
        self.split_profile = None
        self.lgs = list()
        self.is_source = False
        self.is_sink = False
        self.nextlink2mylgs = dict()

    def sample_next_link(self) -> Optional[int]:
        if self.is_sink:
            return None
        if self.split_profile is not None:
            return self.split_profile.sample_output_link()
        else:
            return random.choice(list(self.endnode.out_links.keys()))

    def get_lanegroup_for_startlane(self,startlane:int) -> Optional['LaneGroup']:
        v = [lg for lg in self.lgs if lg.start_lane==startlane]
        if len(v)>0:
            return v[0]
        else:
            return None

    def get_lanegroups_for_nextlink(self, next_link:int) -> list['LaneGroup']:
        if len(self.nextlink2mylgs)>0:
            return self.nextlink2mylgs[next_link]
        else:
            return self.lgs

    def argmax_supply(self, candidate_lanegroups: list['LaneGroup']) -> 'LaneGroup':
        if len(candidate_lanegroups)==1:
            return candidate_lanegroups[0]
        ind = np.argmax([lg.get_supply_per_lane() for lg in candidate_lanegroups])
        return candidate_lanegroups[ind]

    def add_vehicle(self,vehicle:'Vehicle',dispatcher:'Dispatcher',joinlg:Optional['LaneGroup']=None):

        # sample its next link
        next_link_id = self.sample_next_link()
        vehicle.next_link_id = next_link_id

        # pick from among the eligible lane groups, unless joinlg is already given
        if joinlg is None:
            candidate_lane_groups: list[LaneGroup] = self.get_lanegroups_for_nextlink(vehicle.next_link_id)
            joinlg = self.argmax_supply(candidate_lane_groups)

        # add to joinlanegroup
        joinlg.add_vehicle_to_queue(vehicle,'t', dispatcher)

    def get_num_vehicles(self) -> float:
        return sum([lg.get_total_vehicles() for lg in self.lgs])