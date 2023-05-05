from typing import TYPE_CHECKING, Optional
import json
from SimpleClasses import VehicleType, RoadConnection
from Link import Link
from profiles import Demand, SplitMatrixProfile
from Signal import ActuatorSignal
from Controller import ControllerStage
from LaneGroup import LaneGroup
import numpy as np
from Events import Dispatcher, EventStopSimulation

if TYPE_CHECKING:
    from abstract import *

class Node:
    id: int
    in_links: dict[int,"Link"]
    out_links: dict[int,"Link"]
    road_connections: dict[int,"RoadConnection"]
    is_source: bool
    is_sink: bool
    is_many2one: bool

    signal:ActuatorSignal

    def __init__(self,myid:int):
        self.id = myid
        self.in_links = dict()
        self.out_links = dict()
        self.road_connections = dict()
        self.is_source = True
        self.is_sink = True
        self.is_many2one = False

    def register_actuator(self,act:"ActuatorSignal"):
        self.signal = act

    def add_road_connection(self,rc:"RoadConnection") -> None:
        self.road_connections[rc.id] = rc

    def add_input_link(self,link:"Link") -> None:
        self.in_links[link.id] = link
        self.is_source = False

    def add_output_link(self,link:"Link") -> None:
        self.out_links[link.id] = link
        self.is_sink = False

class Network:

    nodes: dict[int,Node]
    links: dict[int,"Link"]

    def __init__(self,netjson:dict[str,dict]) -> None:

        # read road parameters
        roadparams:dict = dict()
        for strid, roadparamjson in netjson['roadparams'].items():
            roadparamid = int(strid)
            roadparams[roadparamid] = {
                'capacity' : float(roadparamjson['capacity']),
                'speed' : float(roadparamjson['speed']),
                'jam_density' : float(roadparamjson['jam_density'])
            }

        # create nodes
        self.nodes = dict()
        for strid, nodejson in netjson['nodes'].items():
            nodeid = int(strid)
            node = Node(nodeid)
            self.nodes[nodeid] = node

        # create links
        self.links = dict()
        for strid, linkjson in netjson['links'].items():
            roadparam = int(linkjson['roadparam'])
            linkid = int(strid)
            link = Link(self,linkid,linkjson,roadparams[roadparam])
            self.links[linkid] = link

        # Set node is_many2one, link is_source, is_sink
        for node in self.nodes.values():
            node.is_many2one = len(node.in_links)>1 and len(node.out_links)==1

            if len(node.in_links) == 0:
                for link in node.out_links.values():
                    link.is_source = True

            if len(node.out_links) == 0:
                for link in node.in_links.values():
                    link.is_sink = True

        # read road connections
        for strid, roadconnjson in netjson['roadconnections'].items():

            in_link_id = int(roadconnjson['in_link'])
            in_link = self.links[in_link_id]

            if 'in_link_lanes' in roadconnjson.keys():
                x = [int(s) for s in roadconnjson['in_link_lanes'].split('-')]
                in_link_lanes = (x[0],x[1])
            else:
                in_link_lanes = (1,in_link.full_lanes)

            rc = RoadConnection(
                id = int(strid),
                in_link=in_link_id,
                in_link_lanes=in_link_lanes,
                out_link=int(roadconnjson['out_link']))

            # add road connections to nodes
            in_link.endnode.add_road_connection(rc)

        # Create lane groups .....................................
        for link in self.links.values():

            lanegroups = list()

            # collect outgoing road connections
            out_rcs = [rc for rc in link.endnode.road_connections.values() if rc.in_link==link.id]

            # if len(out_rcs)==0 and (not link.is_sink):
            #     raise(Exception("len(out_rcs)==0 and (not link.is_sink)"))

            # create set of all intersections of out_rcs up lanes
            lane_sets:set[tuple[int,int]] = set()
            for rc in out_rcs:
                if in_link_lanes is None:
                    lane_sets.add((1,link.full_lanes))
                else:
                    lane_sets.add(rc.in_link_lanes)

            if len(lane_sets)==0:
                lanegroups.append(LaneGroup(link=link,
                                            length=link.length,
                                            num_lanes=link.full_lanes,
                                            start_lane=1,
                                            rp=link.roadparam,
                                            out_rcs=None))

                link.set_lanegroups(lanegroups)
                continue

            lane2rcs = list()
            for start_lane in range(1,link.full_lanes+1):
                lane2rcs.append(frozenset(
                    {rc.id for rc in out_rcs if start_lane >= rc.in_link_lanes[0] and start_lane <= rc.in_link_lanes[1]}
                ))

            for myrcs in set(lane2rcs):
                lanes = [lanerc==myrcs for lanerc in lane2rcs]
                lanes_in_lg = np.where(lanes)[0] + 1
                lg_start_lane = lanes_in_lg[0]
                lg_num_lanes = lanes_in_lg.shape[0]
                lanegroup = LaneGroup(link=link,
                                      length=link.length,
                                      num_lanes=link.full_lanes,
                                      start_lane=lg_start_lane,
                                      rp=link.roadparam,
                                      out_rcs=set(myrcs))

                lanegroups.append(lanegroup)

            link.set_lanegroups(lanegroups)




            # # populate rc.out_lanegroups
            # for rc in link.start_node.road_connections:
            #     if rc.end_link==link:
            #         rc.out_lanegroups.clear()
            #         for (int lane = rc.get_end_link_from_lane(); lane <= rc.get_end_link_to_lane(); lane++)
            #             rc.out_lanegroups.add(link.get_lanegroup_for_up_lane(lane));


            # # populate link.outlink2lanegroups
            # if not link.is_sink():
            #     link.outlink2lanegroups = dict()
            #     for outlink in link.end_node.out_links:
            #         Set<AbstractLaneGroup> lgs = link.lgs.stream()
            #                 .filter(lg -> lg.outlink2roadconnection.containsKey(outlink.getId()))
            #                 .collect(Collectors.toSet());
            #         if(!lgs.isEmpty())
            #             link.outlink2lanegroups.put(outlink.getId(), lgs);

            # # create vehicle sources
            # if scenario.demands.containsKey(link.getId()):
            #     link.demandGenerators = new HashSet<>();
            #     for(DemandInfo demandinfo : scenario.demands.get(link.getId())){
            #         AbstractDemandGenerator source = create_source(
            #                 link,
            #                 demandinfo.profile,
            #                 scenario.commodities.get(demandinfo.commid),
            #                 demandinfo.pathid==null?null : (Path)scenario.subnetworks.get(demandinfo.pathid));
            #         link.demandGenerators.add(source);

class Scenario:
    dispatcher : "Dispatcher"
    network : Network
    vtypes : dict[int, "VehicleType"]
    controllers : dict[int,"AbstractController"]
    actuators : dict[int,"AbstractActuator"]
    demands : dict[int,set["Demand"]]

    def __init__(self,filename:str,validate:Optional[bool]=False) -> None:

        with open(filename) as f:
            scnjson = json.load(f)

        # read vehicle types
        self.vtypes = dict()
        for key, val in scnjson['vehicletypes'].items():
            vtid:int = int(key)
            self.vtypes[vtid] = VehicleType(
                id=vtid,
                name=val['name'],
                pathfull=bool(val['pathfull'])
            )

        # read network
        self.network = Network(scnjson['network'])

        # read demands
        self.demands = dict()
        for x in scnjson['demands']:
            linkid = int(x['link'])
            link = self.network.links[linkid]
            demand:Demand = Demand(x)
            if linkid not in self.demands.keys():
                self.demands[linkid] = set()
            self.demands[linkid].add(demand)
            link.add_demand(demand)

        # read splits
        for x in scnjson['splits']:

            nodeid:int = int(x['node'])
            vtid = int(x['vtype'])
            linkinid:int = int(x['link_in'])
            start_time:float = float(x['start_time']) if 'start_time' in x.keys() else 0.0
            dt:Optional[float] = float(x['dt']) if 'dt' in x.keys() else None

            # get node and link
            # node:Node = self.network.nodes[nodeid]
            linkin:Link = self.network.links[linkinid]

            # get smp
            if vtid not in linkin.split_profile.keys():
                linkin.split_profile[vtid] = SplitMatrixProfile(vtid, linkin,start_time,dt)
            smp = linkin.split_profile[vtid]

            # read splits
            for strid,v in x['link_out_value'].items():
                linkoutid = int(strid)
                values = [float(s) for s in v.split(',')]
                smp.splits.add_entry(linkoutid, values)

        # read actuators
        self.actuators = dict()
        for strid,jsonact in scnjson['actuators'].items():
            actid = int(strid)
            acttype = jsonact['type']
            if acttype=='signal':
                self.actuators[actid] = ActuatorSignal(actid,self,jsonact)
            else:
                raise(Exception("Error: Unknown actuator type {acttype}"))

        # read controllers
        self.controllers = dict()
        for strid, jsoncnt in scnjson['controllers'].items():
            cntid = int(strid)
            cnttype = jsoncnt['type']
            cntacts = {int(s):self.actuators[int(s)] for s in jsoncnt['target_actuators'].split(',')}
            if cnttype=='sig_pretimed':
                self.controllers[cntid] = ControllerStage(cntid, jsoncnt, cntacts)
            else:
                raise(Exception(f"Error: Unknown controller type {cnttype}"))

    def request_outputs(self,requests:Optional[tuple[dict]]=None) -> None:
        pass

    def initialize(self,output_prefix:Optional[str]='',validate:Optional[bool]=False) -> bool :

        # build and attach dispatcher
        self.dispatcher = Dispatcher()
        self.dispatcher.initialize()

        # append outputs from output request file ..................
        # if output_requests_file is not None and !output_requests_file.isEmpty()) :
        #     jaxb.OutputRequests jaxb_or = load_output_request(output_requests_file, true);
        #     scenario.outputs.addAll(create_outputs_from_jaxb(scenario,prefix,output_folder, jaxb_or));


        # validate the run parameters and outputs
        # OTMErrorLog errorLog1 = new OTMErrorLog();
        # runParams.validate(errorLog1);
        #
        # // check validation
        # errorLog1.check();

        # initialize and register outputs
        # for(AbstractOutput x : outputs)
        #     x.initialize(this);

        # register_with_dispatcher timed writer events
        # for AbstractOutput output : outputs)
        #     output.register(runParams,dispatcher);

        for link in self.network.links.values():
            link.initialize(self)

        #####################################
        # for model : models.values())
        #     model.initialize(this,runParams.start_time);
        #####################################

        for cnt in self.controllers.values():
            cnt.initialize(self)

        # for(AbstractScenarioEvent event: events.values())
        #     event.initialize(this);

        # if(path_tt_manager!=null)
        #     path_tt_manager.initialize(dispatcher);

        # validate
        valid = True
        if validate:
            valid = True
            # OTMErrorLog errorLog2 = validate_post_init();
            # errorLog2.check();

        return True

    def run(self,duration):

        # register stop the simulation
        now = self.dispatcher.current_time
        self.dispatcher.stop_time = now+duration
        self.dispatcher.register_event(EventStopSimulation(self.dispatcher,now+duration))

        # register scenario events
        # for e in self.events:
        #     if (e.timestamp>=now) and (e.timestamp<now+duration):
        #         self.dispatcher.register_event(e)

        # process all events
        self.dispatcher.dispatch_all_events()

