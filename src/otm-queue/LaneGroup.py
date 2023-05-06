from typing import TYPE_CHECKING
from typing import Any, Optional
from Events import EventReleaseVehicleFromLaneGroup, EventTransitToWaiting
from queue import Queue
from static import get_waiting_time

if TYPE_CHECKING:
    from core import Link
    from Vehicle import Vehicle
    from Signal import ActuatorSignal
    from SimpleClasses import RoadConnection, RoadParams
    from Events import Dispatcher

class VehicleQueue:
    queue:Queue
    # lg:'LaneGroup'

    def __init__(self,lg:'LaneGroup'):
        self.queue = Queue()
        # self.lg = lg

    def clear(self) -> None:
        self.queue = Queue()

    def get_total_vehicles(self) -> int:
        return self.queue.qsize()

    def add_vehicle(self,v:'Vehicle') -> None:
        self.queue.put(v)

    def remove_given_vehicle(self,timestamp:float, v:'Vehicle') -> None:
        pass

class LaneGroup:

    neighbor_instart_lane:Any     # lanegroup down and in
    neighbor_out:Any      # lanegroup down and out
    longitudinal_supply: float       # [veh]

    link : "Link"
    num_lanes : int
    length : float  # [m]

    max_vehicles : float
    transit_queue: VehicleQueue
    waiting_queue: VehicleQueue

    transit_time_sec : float
    saturation_flow_rate_vps : float
    nom_saturation_flow_rate_vps : float

    # public StateContainer buffer;

    actuator_capacity : Optional['ActuatorSignal']

    # flow accumulator
    # protected FlowAccumulatorState flw_acc;

    # one-to-one map at the lanegroup level
    outlink2roadconnection : dict[int, Any]  # dict[int, RoadConnection]

    # state to the road connection it must use (should be avoided in the one-to-one case)
    # I SHOULD BE ABLE TO ELIMINATE THIS SINCE IT IS SIMILAR TO OUTLINK2ROADCONNECTION
    # AND ALSO ONLY USED BY THE NODE MODEL
    # protected Map<State,Long> state2roadconnection;

    # target lane group to direction
    # state2lanechangedirections : dict[State,Set<Maneuver>>
    # private Map<State,Set<Maneuver>> disallowed_state2lanechangedirections = new HashMap<>();

    # lane changing
    # protected Map<State , Map<Maneuver,Double>> state2lanechangeprob; // state-> maneuver -> probability

    def __init__(self,link:"Link",length:float , num_lanes:int , start_lane:int, rp:'RoadParams' , out_rcs:Optional[list['RoadConnection']] = None ) -> None:

        self.link = link
        self.length = length
        self.num_lanes = num_lanes
        # self.id = OTMUtils.get_lanegroup_id();
        self.start_lane_dn = start_lane
        # self.state2roadconnection = dict()
        # self.state2lanechangeprob = dict()
        self.max_vehicles =  rp.jam_density * (self.length/1000.0) * self.num_lanes

        self.transit_time_sec = (self.length/rp.speed)* 3.6 # [m]/[kph] -> [sec]
        self.saturation_flow_rate_vps = rp.capacity*self.num_lanes/3600

        self.actuator_capacity = None

        self.outlink2roadconnection = dict()
        if out_rcs is not None:
            for rc in out_rcs:
                # rc.in_lanegroups.add(self)
                self.outlink2roadconnection[rc.out_link] = rc

        self.transit_queue = VehicleQueue(self)
        self.waiting_queue = VehicleQueue(self)

    def register_actuator(self,act:"ActuatorSignal"):
        self.actuator_capacity = act

    def initialize(self,scenario) -> None:

        self.transit_queue.clear()
        self.waiting_queue.clear()

        # register first vehicle exit
        # TODO : Uncomment this
        # self.schedule_release_vehicle(scenario.dispatcher)

        self.update_long_supply()

    def update_long_supply(self) -> None:
        self.longitudinal_supply =  self.max_vehicles - self.get_total_vehicles()

    def get_total_vehicles(self) -> float:
        return self.transit_queue.get_total_vehicles() + self.transit_queue.get_total_vehicles()

    def get_supply_per_lane(self) -> float:
        return self.longitudinal_supply / self.num_lanes

    # def get_waiting_supply(self,) -> float:
    #     return self.waiting_queue.lanegroup.get_long_supply()

    def set_actuator_capacity_vps(self,rate_vps:float) -> None:
        if rate_vps<0:
            return
        self.saturation_flow_rate_vps = min(self.nom_saturation_flow_rate_vps,rate_vps)

        # Recompute exit times for all vehicles in the waiting queue
        # self.reset_exit_time()

    def set_to_nominal_capacity(self) -> None:
        self.saturation_flow_rate_vps = self.nom_saturation_flow_rate_vps
        # self.reset_exit_time()

    # private void reset_exit_time(){
    #
    #     // remove future release vehicle events
    #     Scenario scenario = link.get_scenario();
    #
    #     float now = scenario.dispatcher.current_time;
    #
    #     scenario.dispatcher.remove_events_for_recipient(EventReleaseVehicleFromLaneGroup.class,this);
    #
    #     if(this.saturation_flow_rate_vps<0.0001)
    #         return;
    #
    #     // reschedule for all vehicles in waiting queue
    #     float next_release = scenario.dispatcher.current_time +
    #             OTMUtils.get_waiting_time(saturation_flow_rate_vps,link.get_model().stochastic_process);
    #     scenario.dispatcher.register_event(
    #             new EventReleaseVehicleFromLaneGroup(scenario.dispatcher,next_release,this));
    #
    # }

    # def get_upstream_vehicle_position(self) -> float:
    #     return self.longitudinal_supply * self.length / self.max_vehicles


     # * A vehicle arrives at this lanegroup.
     # * Vehicles do not know their next_link. It is assumed that the vehicle fits in this lanegroup.
     # * 2. tag it with next_link and target lanegroups.
     # * 3. add the core.packet to this lanegroup.
    def add_vehicle(self, timestamp:float, veh:'Vehicle',dispatcher:'Dispatcher') -> None:

        # tell the event listeners
        # if veh.get_event_listeners() is not None:
        #     for ev in veh.get_event_listeners():
        #         ev.move_from_to_queue(timestamp,veh,veh.my_queue,self.transit_queue)

        # tell the vehicle it has moved
        veh.move_to_queue(timestamp,self,self.transit_queue)

        # tell the travel timers
        # if travel_timer is not None:
        #     self.travel_timer.vehicle_enter(timestamp,veh)

        # dispatch to go to waiting queue
        dispatcher.register_event(EventTransitToWaiting(dispatcher,timestamp + self.transit_time_sec,veh))

        self.update_long_supply()

    # /**
    #  * An event signals an opportunity to release a vehicle. The lanegroup must,
    #  * 1. construct packets to be released to each of the lanegroups reached by each of it's
    #  *    road connections.
    #  * 2. check what portion of each of these packets will be accepted. Reduce the packets
    #  *    if necessary.
    #  * 3. call add_vehicle_packet for each reduces core.packet.
    #  * 4. remove the vehicle packets from this lanegroup.
    #  */
    def release_vehicles(self,timestamp:float) -> None:
        pass

        # # schedule the next vehicle release dispatch
        # self.schedule_release_vehicle(timestamp)
        #
        # # ignore if waiting queue is empty
        # if self.waiting_queue.get_total_vehicles()==0:
        #     return
        #
        # # otherwise get the first vehicle
        # vehicle = self.waiting_queue.peek_vehicle()
        #
        # next_supply = float('inf')
        # next_link:"Link" = None
        # rc:RoadConnection = None
        #
        # if not self.link.is_sink():
        #
        #     # get next link
        #     next_link_id = vehicle.next_link_id
        #
        #     rc = self.outlink2roadconnection[next_link_id]
        #
        #     next_link = rc.get_end_link()
        #
        #     # at least one candidate lanegroup must have space for one vehicle.
        #     # Otherwise the road connection is blocked.
        #     next_supply = max([lg.get_long_supply() for lg in rc.get_out_lanegroups() ])
        #
        #
        # if next_supply > 0:
        #
        #     # remove vehicle from this lanegroup
        #     self.waiting_queue.remove_given_vehicle(timestamp,vehicle)
        #
        #     # inform flow accumulators
        #     self.update_flow_accummulators(vehicle.get_state(),1.0)
        #
        #     # inform the travel timers
        #     if self.travel_timer is not None:
        #         self.travel_timer.vehicle_exit(timestamp,vehicle,self.link.getId(),next_link)
        #
        #     # send vehicle core.packet to next link
        #     if (next_link is not None) and (rc is not None):
        #         next_link.get_model().add_vehicle_packet(next_link,timestamp,PacketLink(vehicle,rc))
        #
        #     # TODO Need a better solution than this.
        #     # TODO This is adhoc for when the next links is a fluid model.
        #     # Todo Then the event counter is not getting triggered.
        #     # inform the queue counters
        #     # if (next_link is not None) and !(next_link.get_model() instanceof ModelSpatialQ) && vehicle.get_event_listeners()!=null) {
        #     #     for (InterfaceVehicleListener ev : vehicle.get_event_listeners())
        #     #         ev.move_from_to_queue(timestamp, vehicle, waiting_queue, null);
        #
        #     self.update_long_supply()

    def schedule_release_vehicle(self,dispatcher) -> None:
        nowtime = dispatcher.current_time
        wait_time = get_waiting_time(self.saturation_flow_rate_vps)
        if wait_time is not None:
            timestamp = nowtime + wait_time
            dispatcher.register_event(EventReleaseVehicleFromLaneGroup(dispatcher,timestamp,self))

    def __str__(self) -> str:
        return "lg link {}, lanes {}-{}".format(self.link.id,self.start_lane_dn,
                                                self.start_lane_dn+self.num_lanes-1)



    # public final FlowAccumulatorState request_flow_accumulator(Set<Long> comm_ids){
    #     if(flw_acc==null)
    #         flw_acc = new FlowAccumulatorState();
    #     for(State state : link.states)
    #         if(comm_ids==null || comm_ids.contains(state.commodity_id))
    #             flw_acc.add_state(state);
    #     return flw_acc;
    # }

    # public final void update_flow_accummulators(State state, double num_vehicles){
    #     if(flw_acc!=null)
    #         flw_acc.increment(state,num_vehicles);
    # }
