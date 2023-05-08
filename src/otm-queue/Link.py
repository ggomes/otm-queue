from typing import TYPE_CHECKING, Optional
import numpy as np
from Demand import Demand
from SimpleClasses import RoadParams
import random

if TYPE_CHECKING:
    from Splits import SplitMatrixProfile
    from LaneGroup import LaneGroup
    from core import Scenario, Node
    from Events import Dispatcher
    from Vehicle import Vehicle

class Link:

    id: int
    full_lanes: int
    length: float
    startnode: 'Node'
    endnode: 'Node'
    roadparam: RoadParams
    demands: list[Demand]
    split_profile: dict[int, 'SplitMatrixProfile']
    lgs: list['LaneGroup']
    is_source: bool
    is_sink: bool
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
        self.demands = list()
        self.split_profile = dict()
        self.lgs = list()
        self.is_source = False
        self.is_sink = False

        # downstream lane count -> lane group
        # Probably don't need it
        # dnlane2lanegroup : dict[int,LaneGroup] = dict()

        # nextlink -> lanegroups in this link from which nextlink is reachable
        self.nextlink2mylgs = dict()

        # control flows to downstream links
        # unique_acts_flowToLinks : set[ActuatorFlowToLinks]
        # acts_flowToLinks dict[int,dict[int,ActuatorFlowToLinks] = dict() # road connection->commodity->actuator

        # demands ............................................
        # demandGenerators : set[AbstractDemandGenerator]

        # travel timer
        # link_tt : LinkTravelTimer

    def add_demand(self,demand:Demand) -> None:
        self.demands.append(demand)

    def set_lanegroups(self,newlgs: list['LaneGroup'] ) -> None:
        self.lgs = newlgs
        # dnlane2lanegroup = dict()
        # for lg in self.lgs:
        #     for lane in range(lg.start_lane_dn,lg.start_lane_dn+lg.num_lanes):
        #         dnlane2lanegroup[lane] = lg

    def initialize(self,scenario:'Scenario') -> None:

        for lg in self.lgs:
            lg.initialize(scenario)

        # from outlinks, remove ones without splits or actuators (unnecessary)
        # Set<Long> pathless_comms = states.stream().filter(s->!s.isPath).map(s->s.commodity_id).collect(toSet());
        # for(Long commid : pathless_comms){
        #     Set<Long> outlinks = new HashSet<>();
        #     outlinks.addAll(this.outlink2lanegroups.keySet());
        #     if(split_profile!=null && split_profile.containsKey(commid)) {
        #         SplitMatrixProfile smp = split_profile.get(commid);
        #         if(smp.get_splits()!=null)
        #             outlinks.removeAll(smp.get_splits().values.keySet());
        #     }
        # }

        for sp in self.split_profile.values():
            sp.initialize(scenario.dispatcher)

        for d in self.demands:
            d.initialize(scenario.dispatcher)

    def sample_next_link(self,vtid:int) -> Optional[int]:
        if self.is_sink:
            return None
        if len(self.split_profile)>0:
            return self.split_profile[vtid].sample_output_link()
        else:
            return random.choice(list(self.endnode.out_links.keys()))

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
        next_link_id = self.sample_next_link(vehicle.vtype.id)
        vehicle.next_link_id = next_link_id

        # pick from among the eligible lane groups, unless joinlg is already given
        if joinlg is None:
            candidate_lane_groups: list[LaneGroup] = self.get_lanegroups_for_nextlink(vehicle.next_link_id)
            joinlg = self.argmax_supply(candidate_lane_groups)

        # add to joinlanegroup
        joinlg.add_vehicle(vehicle,dispatcher)


    def get_total_vehicles(self) -> float:
        return sum([lg.get_total_vehicles() for lg in self.lgs])