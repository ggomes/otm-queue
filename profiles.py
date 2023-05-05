from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional
from Events import Dispatcher
from Events import EventSplitChange, EventDemandChange, EventCreateVehicle
from static import get_waiting_time

# if TYPE_CHECKING:

@dataclass
class LinkCumSplit:
    link_id: int
    cumsplit : float

@dataclass
class TimeMap:
    time: float
    value: dict[int,float]

class Demand:

    vehicle_scheduled:bool
    # protected Profile1D profile;
    # protected Link link;
    # protected Path path;
    # protected Commodity commodity;
    source_demand_vps:float  # vps


    def __init__(self,demdict:dict[str,str]) -> None:
        self.link_id = int(demdict['link'])
        self.vtype_id = int(demdict['vtype'])
        self.value = float(demdict['value'])

        self.vehicle_scheduled = False
        self.source_demand_vps = 0

        # this.link = link;
        # this.profile = profile;
        # this.commodity = commodity;
        # this.path = path;

    # public final State sample_state(){
    #     if(commodity.pathfull){
    #         return new State(commodity.getId(),path.getId(),true);
    #     } else {
    #         return new State(commodity.getId(),link.sample_next_link(commodity.getId()),false);
    #     }
    # }

    def initialize(self,dispatcher:Dispatcher) -> None:
        self.vehicle_scheduled = False

    def set_demand_vps(self,dispatcher:Dispatcher ,time:float ,value:float ) -> None:
        self.source_demand_vps = value
        if value>0:
            self.schedule_next_vehicle(dispatcher, time)

    def schedule_next_vehicle(self,dispatcher:Dispatcher , timestamp:float ) -> None:

        if self.vehicle_scheduled:
            return

        wait_time = get_waiting_time(self.source_demand_vps)
        if wait_time is not None:
            dispatcher.register_event(EventCreateVehicle(dispatcher, timestamp + wait_time, self))
            vehicle_scheduled = True



    def insert_vehicle(timestamp:float ) -> None:
        pass

        # # AbstractVehicleModel model = (AbstractVehicleModel) link.get_model();
        #
        # # create a vehicle
        # vehicle = create_vehicle(vtype,VehicleType.vehicle_event_listeners)
        #
        # # sample key
        # # State state = sample_state();
        # # vehicle.set_state(state);
        #
        # if(commodity.pathfull)
        #     vehicle.path = path;
        #
        # # extract next link
        # Long next_link = commodity.pathfull ? link.get_next_link_in_path(path.getId()).getId() : state.pathOrlink_id;
        #
        # # candidate lane groups
        # Set<AbstractLaneGroup> candidate_lane_groups = link.get_lanegroups_for_outlink(next_link);
        #
        # # pick from among the eligible lane groups
        # AbstractLaneGroup join_lanegroup = link.get_model().lanegroup_proportions(candidate_lane_groups).keySet().iterator().next();
        #
        # # package and add to joinlanegroup
        # self.join_lanegroup.add_vehicle_packet(timestamp,new PacketLaneGroup(vehicle),next_link);
        #
        # # this scheduled vehicle has been created
        # self.vehicle_scheduled = False


    def register_with_dispatcher(self,dispatcher:Dispatcher ) -> None:
        value = self.profile.get_value_for_time(dispatcher.current_time)
        dispatcher.register_event(EventDemandChange(dispatcher, dispatcher.current_time, self, value))

    def register_next_change(self,dispatcher:Dispatcher, timestamp:float  ) -> None:
        time_value:TimeValue  = self.profile.get_change_following(timestamp)
        if time_value is not None:
            dispatcher.register_event(EventDemandChange(dispatcher, time_value.time, self, time_value.value))

        # schedule next vehicle
        self.schedule_next_vehicle(dispatcher, timestamp)


class Profile2D:
    start_time: float
    dt: Optional[float]
    values: dict[int,list[float]]  # linkout->profile
    num_times: int

    def __init__(self,start_time:float, dt:Optional[float]=None) -> None:
        self.start_time = start_time
        self.dt = dt
        self.values = dict()

    def add_entry(self,linkoutid:int, values:list[float]) -> None:
        if linkoutid in self.values.keys():
            print(f"Warning: Overwriting split profile")
        else:
            self.values[linkoutid] = values

        self.num_times = len(values)


    def get_value_for_time(self,time:float) -> dict[int,float]:

        if (self.dt is None) or (self.dt==0):
            return self.get_ith_value(0)
        return self.get_ith_value( int(time/self.dt) )

    # public TimeMap get_change_following(float now){
    #     if(now<start_time)
    #         return new TimeMap(start_time,get_ith_value(0));
    #     if(dt==null || dt==0)
    #         return null;
    #
    #     int index = (int)((now+dt-start_time)/dt);
    #     if(index>num_times-1)
    #         return null;
    #     return new TimeMap(start_time + index*dt,get_ith_value(index));
    # }

    # get values for time index i
    def get_ith_value(self,i:int) -> dict[int,float]:
        r:dict[int,float] = dict()
        step = max(0,min(i,self.num_times-1))
        for k,v in self.values.items():
            r[k] = v[step]
        return r

    # public Set<Long> get_nonzero_outlinks(){
    #     Set<Long> x = new HashSet<>();
    #     for(Map.Entry<Long,List<Double>> e : values.entrySet())
    #         if(!e.getValue().stream().allMatch(v->v==0d))
    #             x.add(e.getKey());
    #     return x;
    # }

class SplitMatrixProfile:
    vtid: int
    splits: Profile2D    # link out id -> split profile

    # current splits
    # outlink2split: dict[int,float]  # output link id -> split
    # outlinks_without_splits: set[int]
    # total_split: float
    # link_cumsplit: list[LinkCumSplit]  # output link id -> cummulative split

    def __init__(self,vtid:int,link_in,start_time: float, dt: Optional[float]=None ) -> None:
        self.vtid = vtid
        self.link_in = link_in
        self.splits = Profile2D(start_time, dt)

    def validate_pre_init(self,scenario) -> None:

        node = self.link_in.endnode
        vtype = scenario.vtypes[self.vtid]

        # reachable_outlinks: set[int]  = node.road_connections
                # .filter(rc->rc.get_start_link()!=null && rc.get_end_link()!=null && rc.get_start_link().getId().equals(link_in.getId()))
                # .map(z->z.get_end_link().getId())
                # .collect(Collectors.toSet());

        # nonzero_outlinks: set[int] = self.splits.get_nonzero_outlinks()

        # check that there is a road connection for every split ratio
        # if(!reachable_outlinks.containsAll(nonzero_outlinks)) {
        #     Set<Long> unreachable = new HashSet<>();
        #     unreachable.addAll(splits.values.keySet());
        #     unreachable.removeAll(reachable_outlinks);
        #     errorLog.addError(String.format("No road connection supporting split from link %d to link(s) %s",link_in.getId(), OTMUtils.comma_format(unreachable)));

    def initialize(self,dispatcher: Dispatcher) -> None :
        if self.splits is None:
            return
        now: float = dispatcher.current_time
        self.set_all_current_splits(self.splits.get_value_for_time(now))
        time_splits: dict[int,float] = self.splits.get_value_for_time(now)
        dispatcher.register_event(EventSplitChange(dispatcher,now, self, time_splits))

    # return an output link id according to split ratios for this commodity and line
    def sample_output_link(self) -> int :
        return -1

    #     r:float = OTMUtils.random_zero_to_one()
    #
    #     Optional<LinkCumSplit> z = link_cumsplit.stream()
    #             .filter(x->x.cumsplit<r)  // get all cumsplit < out
    #             .reduce((a,b)->b);        // get last such vauue
    #
    #     return z.isPresent() ? z.get().link_id : null;
    # }

    def register_next_change(self,dispatcher:Dispatcher,time_map:TimeMap) -> None:
        if time_map is not None:
            dispatcher.register_event(EventSplitChange(dispatcher,time_map.time, self, time_map.value))

    def set_all_current_splits(self,newsplit:dict[int,float] ) -> None:
        self.outlink2split = newsplit
        # self.propagate_split_change()