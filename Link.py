from typing import TYPE_CHECKING
from profiles import Demand
from SimpleClasses import RoadParams

if TYPE_CHECKING:
    from profiles import SplitMatrixProfile
    from LaneGroup import LaneGroup
    from core import Scenario

class Link:

    def __init__(self,network,linkid:int,jsonlink:dict,roadparam:dict) -> None:

        self.id:int = linkid
        self.full_lanes:int = int(jsonlink['full_lanes'])
        self.length:float = float(jsonlink['length'])
        self.startnode = network.nodes[int(jsonlink['start'])]
        self.startnode.add_output_link(self)
        self.endnode = network.nodes[int(jsonlink['end'])]
        self.endnode.add_input_link(self)
        self.roadparam = RoadParams(capacity = float(roadparam['capacity']),
                                    speed =  float(roadparam['speed']),
                                    jam_density =  float(roadparam['jam_density']) )
        self.demands:list[Demand] = list()
        self.split_profile:dict[int,SplitMatrixProfile] = dict()

        self.lgs : list[LaneGroup] = list()

        self.is_source = False
        self.is_sink = False

        # downstream lane count -> lane group
        # Probably don't need it
        # dnlane2lanegroup : dict[int,LaneGroup] = dict()

        # outlink -> lanegroups from which outlink is reachable
        # outlink2lanegroups : dict[int,set[LaneGroup] = set()

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
