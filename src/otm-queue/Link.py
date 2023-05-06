from typing import TYPE_CHECKING
import numpy as np
from Demand import Demand
from SimpleClasses import RoadParams
import random

if TYPE_CHECKING:
    from Splits import SplitMatrixProfile
    from LaneGroup import LaneGroup
    from core import Scenario, Node

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
    outlink2lanegroups: dict[int, list['LaneGroup']]

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

        # outlink -> lanegroups from which outlink is reachable
        self.outlink2lanegroups = dict()

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

    def sample_next_link(self,vtid:int) -> int:
        if len(self.split_profile)>0:
            return self.split_profile[vtid].sample_output_link()
        else:
            return random.choice(list(self.endnode.out_links.keys()))

    def get_lanegroups_for_outlink(self,next_link:int) -> list['LaneGroup']:
        if len(self.outlink2lanegroups)>0:
            return self.outlink2lanegroups[next_link]
        else:
            return self.lgs

    def argmax_supply(self, candidate_lanegroups: list['LaneGroup']) -> 'LaneGroup':
        ind = np.argmax([lg.get_supply_per_lane() for lg in candidate_lanegroups])
        return candidate_lanegroups[ind]

    def get_total_vehicles(self) -> float:
        return sum([lg.get_total_vehicles() for lg in self.lgs])