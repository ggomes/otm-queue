from typing import TYPE_CHECKING
from abstract import AbstractEvent
import heapq

if TYPE_CHECKING:
    from Demand import Demand
    from Splits import Link2Split

'''
Event prioties:
0: EventDemandChange
1: EventSplitChange
40: EventCreateVehicle
44: EventTransitToWaiting
45: EventSeviceLanegroupWaitingQueue
'''

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
        super().__init__(dispatcher=dispatcher,dispatch_order=1,timestamp=timestamp,recipient=splitProfile)
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

        vehicle.move_to_queue(lanegroup,lanegroup.waiting_queue)

class EventSeviceLanegroupWaitingQueue(AbstractEvent):

    def __init__(self,dispatcher,timestamp:float, obj) -> None:
        super().__init__(dispatcher,45,timestamp,obj)

    def action(self) -> None:
        self.recipient.service_waiting_queue(self.dispatcher)

class Dispatcher:
    events: list[tuple[float,int,AbstractEvent]]
    current_time: float

    def __init__(self) -> None:
        self.events = list()
        self.current_time = 0.0

    def register_event(self,event:AbstractEvent) -> None:
        if event.timestamp<self.current_time:
            return
        heapq.heappush(self.events,(event.timestamp,event.dispatch_order,event))

    def remove_events_for_recipient(self,clazz,recipient) -> None:
        self.events = [e for e in self.events if (not isinstance(e[2],clazz)) or (e[2].recipient is not recipient)]

    def advance(self,duration:float) -> None:
        stop_time = self.current_time + duration
        while len(self.events)>0 and self.current_time<=stop_time:
            timestamp, dispatchorder, event = heapq.heappop(self.events)
            self.current_time = timestamp
            event.action()