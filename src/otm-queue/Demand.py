from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional
import numpy as np
from Events import Dispatcher, EventDemandChange, EventCreateVehicle
from static import get_waiting_time
from Vehicle import Vehicle

if TYPE_CHECKING:
    from core import Scenario, LaneGroup
    from Link import Link
    from SimpleClasses import VehicleType

class Demand:

    link: 'Link'
    vtype: 'VehicleType'
    profile: np.array
    dt: Optional[float]

    # current status
    current_demand_vps:float  # vps
    vehicle_scheduled:bool

    def __init__(self,demjson:dict[str,str],scenario:'Scenario') -> None:
        linkid = int(demjson['link'])
        vtypeid = int(demjson['vtype'])

        self.link = scenario.network.links[linkid]
        self.vtype = scenario.vtypes[vtypeid]
        self.profile = np.array([float(s) for s in demjson['value'].split(',')])
        self.dt = None if ('dt' not in demjson.keys()) else float(demjson['dt'])

        if self.profile.shape[0]==1:
            self.dt=None

    def initialize(self,dispatcher:Dispatcher) -> None:
        self.current_demand_vps = 0
        self.vehicle_scheduled = False
        dispatcher.register_event(EventDemandChange(dispatcher, 0,self, self.profile[0]))

    def set_current_demand_vps(self, dispatcher:Dispatcher, value:float) -> None:
        self.current_demand_vps = value
        if value>0:
            self.schedule_next_vehicle(dispatcher)

    def schedule_next_vehicle(self,dispatcher:Dispatcher) -> None:

        if self.vehicle_scheduled:
            return

        now = dispatcher.current_time
        wait_time = get_waiting_time(self.current_demand_vps)
        if wait_time is not None:
            dispatcher.register_event(EventCreateVehicle(dispatcher, now + wait_time, self))
            self.vehicle_scheduled = True

    def insert_vehicle(self,timestamp:float,dispatcher:Dispatcher ) -> None:

        # create a vehicle
        vehicle = Vehicle(self.vtype)

        # sample its next link
        next_link = self.link.sample_next_link(self.vtype.id)

        # candidate lane groups
        candidate_lane_groups:list[LaneGroup] = self.link.get_lanegroups_for_outlink(next_link)

        # pick from among the eligible lane groups
        join_lanegroup:LaneGroup = self.link.argmax_supply(candidate_lane_groups)
            # .keySet().iterator().next()

        # package and add to joinlanegroup
        join_lanegroup.add_vehicle(timestamp,vehicle,dispatcher)

        # this scheduled vehicle has been created
        self.vehicle_scheduled = False

    def register_next_change(self,dispatcher:Dispatcher) -> None:

        if self.dt is None:
            return

        index = int(dispatcher.current_time / self.dt) + 1
        if index<self.profile.shape[0]:
            timesamp = index * self.dt
            value = self.profile[index]
            dispatcher.register_event(EventDemandChange(dispatcher, timesamp,self, value))


    def __str__(self) -> str:
        return "dem link {}, vtype {}".format(self.link.id,self.vtype.id)
