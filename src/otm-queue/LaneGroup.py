from typing import TYPE_CHECKING, Optional
from Events import EventSeviceLanegroupWaitingQueue, EventTransitToWaiting
from collections import deque
from static import get_service_period
import numpy as np
from Vehicle import Vehicle

if TYPE_CHECKING:
    from core import Link
    from SimpleClasses import RoadParams
    from Events import Dispatcher

class VehicleQueue:
    typestr:str
    queue:deque

    def __init__(self,typestr:str):
        self.typestr = typestr
        self.queue = deque()

    def clear(self) -> None:
        self.queue = deque()

    def get_total_vehicles(self) -> int:
        return len(self.queue)

    def add_vehicle(self,v:'Vehicle') -> None:
        self.queue.append(v)

    def remove_lead_vehicle(self) -> None:
        self.queue.popleft()

    def get_lead_vehicle(self) -> 'Vehicle':
        return self.queue[0]

class LaneGroup:

    link : "Link"
    num_lanes : int
    start_lane: int

    max_vehicles : float
    transit_time_sec : float
    saturation_flow_rate_vps : float
    nom_saturation_flow_rate_vps : float
    longitudinal_supply: float       # [veh]
    nextlinks:list['Link']

    actuator : bool
    transit_queue: VehicleQueue
    waiting_queue: VehicleQueue

    def __init__(self,link:"Link", num_lanes:int , start_lane:int, rp:'RoadParams') -> None:

        self.link = link
        self.num_lanes = num_lanes
        self.start_lane = start_lane

        if link.is_source:
            self.max_vehicles = float('inf')
        else:
            self.max_vehicles = rp.jam_density * (link.length/1000.0) * self.num_lanes
        self.transit_time_sec = (link.length/rp.speed)* 3.6 # [m]/[kph] -> [sec]
        self.saturation_flow_rate_vps = rp.capacity*self.num_lanes/3600
        self.nom_saturation_flow_rate_vps = self.saturation_flow_rate_vps
        self.longitudinal_supply = 0.0

        self.has_actuator = False
        self.transit_queue = VehicleQueue('transit')
        self.waiting_queue = VehicleQueue('waiting')

        self.update_long_supply()

    def get_id(self):
        return self.link.id, self.start_lane

    def register_signal(self):
        if self.has_actuator:
            raise(Exception("Lanegroup is assigned multiple actuators"))
        self.has_actuator = True

    def clear(self) -> None:
        self.transit_queue.clear()
        self.waiting_queue.clear()

    def update_long_supply(self) -> None:
        self.longitudinal_supply =  self.max_vehicles - self.get_total_vehicles()

    def set_vehicles(self,vehs:int,queue:str,nextlinkid:int,dispatcher:'Dispatcher'):
        if vehs>self.longitudinal_supply:
            raise(Exception("Setting too many vehicles"))
        for i in range(vehs):
            vehicle = Vehicle()
            vehicle.next_link_id = nextlinkid
            self.add_vehicle_to_queue(vehicle, queue, dispatcher)

    def get_total_vehicles(self) -> float:
        return self.transit_queue.get_total_vehicles() + self.transit_queue.get_total_vehicles()

    def get_supply_per_lane(self) -> float:
        return self.longitudinal_supply / self.num_lanes

    def set_actuator_capacity_vps(self,rate_vps:float,dispatcher:'Dispatcher') -> None:
        if rate_vps<0:
            return
        self.saturation_flow_rate_vps = min(self.nom_saturation_flow_rate_vps,rate_vps)

        # Recompute exit times for all vehicles in the waiting queue
        self.reset_exit_times(dispatcher)

    def reset_exit_times(self,dispatcher:'Dispatcher')->None:
        now = dispatcher.current_time
        dispatcher.remove_events_for_recipient(EventSeviceLanegroupWaitingQueue,self)

        if self.saturation_flow_rate_vps<=0.0:
            return

        # reschedule for all vehicles in waiting queue
        next_release = now + get_service_period(self.saturation_flow_rate_vps)
        dispatcher.register_event(EventSeviceLanegroupWaitingQueue(dispatcher,next_release,self))

    def add_vehicle_to_queue(self, veh: 'Vehicle', queuestr: str, dispatcher: Optional['Dispatcher']=None) -> None:

        if queuestr=='t':
            queue = self.transit_queue
        elif queuestr=='w':
            queue = self.waiting_queue
        else:
            queue = None

        # tell the vehicle it has moved
        veh.move_to_queue(self,queue)

        # dispatch to go to waiting queue
        if queue is self.transit_queue:
            now = dispatcher.current_time
            dispatcher.register_event(EventTransitToWaiting(dispatcher,now + self.transit_time_sec,veh))

        self.update_long_supply()

    def service_waiting_queue(self, dispatcher:'Dispatcher') -> None:

        # schedule the next vehicle release dispatch
        self.schedule_service_waiting_queue(dispatcher)

        # ignore if waiting queue is empty
        if self.waiting_queue.get_total_vehicles()==0:
            return

        # otherwise get the first vehicle
        vehicle = self.waiting_queue.get_lead_vehicle()

        nextlg = None
        nextlg_supply = float('inf')

        if not self.link.is_sink:
            next_link_id = vehicle.next_link_id
            if next_link_id in self.link.endnode.out_links.keys():
                nextlgs = self.link.endnode.out_links[next_link_id].lgs
                nextlgs_supply = [lg.longitudinal_supply for lg in nextlgs]
                nextlg_ind = np.argmax(nextlgs_supply)
                nextlg = nextlgs[nextlg_ind]
                nextlg_supply = nextlgs_supply[nextlg_ind]

        if nextlg_supply >= 1:

            # send vehicle to next link
            if not self.link.is_sink:
                nextlg.link.add_vehicle(vehicle,dispatcher,joinlg=nextlg)

            self.update_long_supply()

    def schedule_service_waiting_queue(self, dispatcher:'Dispatcher') -> None:
        nowtime = dispatcher.current_time
        service_period = get_service_period(self.saturation_flow_rate_vps)
        if service_period is not None:
            timestamp = nowtime + service_period
            dispatcher.register_event(EventSeviceLanegroupWaitingQueue(dispatcher, timestamp, self))

    def __str__(self) -> str:
        return "({},{})".format(self.link.id, self.start_lane)

    def __key(self):
        return (self.link.id, self.start_lane)

    def __hash__(self):
        return hash(self.__key())

    def __eq__(self, other):
        if isinstance(other, LaneGroup):
            return self.__key() == other.__key()
        return NotImplemented

