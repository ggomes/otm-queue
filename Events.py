from queue import PriorityQueue
from typing import TYPE_CHECKING
from abstract import AbstractEvent

if TYPE_CHECKING:
    from profiles import Demand

class EventTransitToWaiting(AbstractEvent):

    def __init__(self,dispatcher,timestamp:float , vehicle ) -> None:
        super().__init__(dispatcher,44,timestamp,vehicle)

    def action(self) -> None:

        vehicle = self.recipient
        lanegroup = vehicle.get_lanegroup()
        next_link = vehicle.get_next_link_id()

        if next_link is None:
            vehicle.waiting_for_lane_change=False

        # do lane changing
        # if vehicle.waiting_for_lane_change){
        #     List<AbstractLaneGroup>  lgs = lanegroup.get_link().get_lgs();
        #     Map<Long,Double> sdf = lgs.stream()
        #             .filter(lg -> lg.connects_to_outlink(next_link) )
        #             .map(lg -> (MesoLaneGroup) lg)
        #             .collect(Collectors.toMap(MesoLaneGroup::getId,
        #                     MesoLaneGroup::get_waiting_supply) );
        #     long lgid = Collections.max(sdf.entrySet(), Comparator.comparingDouble(Map.Entry::getValue)).getKey();
        #
        #     lanegroup = (MesoLaneGroup) lgs.stream().filter(lg->lg.getId()==lgid).findFirst().orElse(null);
        #     vehicle.waiting_for_lane_change = false;
        # }

        # inform listeners
        if vehicle.get_event_listeners() is not None:
            for ev in vehicle.get_event_listeners():
                ev.move_from_to_queue(self.timestamp,vehicle,vehicle.my_queue,lanegroup.waiting_queue)

        vehicle.move_to_queue(self.timestamp,lanegroup.waiting_queue)

class EventSplitChange(AbstractEvent):

    outlink2value: dict[int,float]

    def __init__(self,dispatcher,timestamp:float, splitProfile, outlink2value:dict[int,float]) -> None:
        super().__init__(dispatcher=dispatcher,dispatch_order=0,timestamp=timestamp,recipient=splitProfile)
        self.outlink2value = outlink2value

    def action(self):
        smp  = self.recipient   # SplitMatrixProfile
        smp.set_all_current_splits(self.outlink2value)
        time_map  = smp.get_splits().get_change_following(self.timestamp)  # TimeMap
        smp.register_next_change(self.dispatcher,time_map)

class EventReleaseVehicleFromLaneGroup(AbstractEvent):

    def __init__(self,dispatcher,timestamp:float, obj) -> None:
        super().__init__(dispatcher,45,timestamp,obj)

    def action(self) -> None:
        self.recipient.release_vehicle_packets(self.timestamp)

class EventDemandChange(AbstractEvent):
    demand_vps:float
    demand:'Demand'

    def __init__(self,dispatcher,timestamp:float, obj,demand_vps:float) -> None:
        super().__init__(dispatcher,0,timestamp,obj)
        self.demand_vps = demand_vps
        self.demand = obj

    def action(self) -> None:
        self.demand.set_demand_vps(self.dispatcher,self.timestamp,self.demand_vps)
        self.demand.register_next_change(self.dispatcher,self.timestamp)

class EventCreateVehicle(AbstractEvent):
    pass

class EventStopSimulation(AbstractEvent):

    def __init__(self , dispatcher, timestamp:float ) -> None:
        super().__init__(dispatcher, 10, timestamp, None)

    def action(self) -> None:
        self.dispatcher.stop()

class Dispatcher:
    current_time: float
    stop_time: float
    events: PriorityQueue
    continue_simulation: bool
    verbose: bool

    def __init__(self,verbose:bool=False) -> None:
        self.events = PriorityQueue()
        self.verbose = verbose

    def initialize(self) -> None:
        self.current_time = 0
        self.clear_events()
        self.continue_simulation = True

    def clear_events(self) -> None:
        self.events.queue.clear()

    def register_event(self,event:AbstractEvent) -> None:
        if event.timestamp<self.current_time:
            return
        self.events.put((event.timestamp,event))

    def dispatch_all_events(self) -> None:
        while self.events:
            timestamp, event = self.events.get()
            self.current_time = timestamp
            print(self.events.qsize())
            print(timestamp, event)
            # event.action()
