from queue import PriorityQueue
from typing import TYPE_CHECKING
from abstract import AbstractEvent
import heapq

if TYPE_CHECKING:
    from Demand import Demand
    from Splits import Link2Split

class EventDemandChange(AbstractEvent):
    demand_vps:float
    demand:'Demand'

    def __init__(self,dispatcher,timestamp:float, obj,demand_vps:float) -> None:
        super().__init__(dispatcher,0,timestamp,obj)
        self.demand_vps = demand_vps
        self.demand = obj

    def action(self) -> None:
        self.demand.set_current_demand_vps(self.dispatcher, self.demand_vps)
        self.demand.register_next_change(self.dispatcher)

class EventSplitChange(AbstractEvent):

    outlink2value: 'Link2Split'

    def __init__(self,dispatcher,timestamp:float, splitProfile, outlink2value:'Link2Split') -> None:
        super().__init__(dispatcher=dispatcher,dispatch_order=0,timestamp=timestamp,recipient=splitProfile)
        self.outlink2value = outlink2value

    def action(self):
        smp  = self.recipient   # SplitMatrixProfile
        smp.set_all_current_splits(self.outlink2value)
        time_splitvalue  = smp.get_change_following(self.timestamp)
        if time_splitvalue is not None:
            time = time_splitvalue[0]
            splitvalue = time_splitvalue[1]
            smp.register_next_change(self.dispatcher,time, splitvalue)

class EventCreateVehicle(AbstractEvent):

    def __init__(self,dispatcher , timestamp:float , demand:'Demand' ) -> None:
        super().__init__(dispatcher,40,timestamp,demand)

    def action(self) -> None:
        demand = self.recipient
        demand.insert_vehicle(self.dispatcher)
        demand.schedule_next_vehicle(self.dispatcher)

class EventTransitToWaiting(AbstractEvent):

    def __init__(self,dispatcher,timestamp:float , vehicle ) -> None:
        super().__init__(dispatcher,44,timestamp,vehicle)

    def action(self) -> None:

        vehicle = self.recipient
        lanegroup = vehicle.lg
        next_link = vehicle.next_link_id

        if next_link is None:
            vehicle.waiting_for_lane_change=False

        # inform listeners
        # if vehicle.get_event_listeners() is not None:
        #     for ev in vehicle.get_event_listeners():
        #         ev.move_from_to_queue(self.timestamp,vehicle,vehicle.my_queue,lanegroup.waiting_queue)

        vehicle.move_to_queue(lanegroup,lanegroup.waiting_queue)

class EventSeviceLanegroupWaitingQueue(AbstractEvent):

    def __init__(self,dispatcher,timestamp:float, obj) -> None:
        super().__init__(dispatcher,45,timestamp,obj)

    def action(self) -> None:
        self.recipient.service_waiting_queue(self.dispatcher)

class EventStopSimulation(AbstractEvent):

    def __init__(self , dispatcher, timestamp:float,scenario ) -> None:
        super().__init__(dispatcher, 10, timestamp, scenario)

    def action(self) -> None:
        self.dispatcher.stop()
        self.recipient.close_outputs()

class Dispatcher:
    current_time: float
    stop_time: float
    events: list[tuple[float,int,AbstractEvent]]
    continue_simulation: bool

    def __init__(self) -> None:
        self.events = list()

    def initialize(self) -> None:
        self.current_time = 0
        self.clear_events()
        self.continue_simulation = True

    def stop(self) -> None:
        self.clear_events()

    def clear_events(self) -> None:
        self.events = list()

    def register_event(self,event:AbstractEvent) -> None:
        if event.timestamp<self.current_time:
            return
        heapq.heappush(self.events,(event.timestamp,event.dispatch_order,event))

    def remove_events_for_recipient(self,clazz,recipient) -> None:
        self.events = [e for e in self.events if (not isinstance(e[2],clazz)) or (e[2].recipient is not recipient)]

    def dispatch_all_events(self) -> None:
        while len(self.events)>0:
            timestamp, dispatchorder, event = heapq.heappop(self.events)
            self.current_time = timestamp
            event.action()
