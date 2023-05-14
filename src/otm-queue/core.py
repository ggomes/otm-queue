from typing import TYPE_CHECKING, Optional
import json
from SimpleClasses import VehicleType, RoadConnection
from Link import Link
from Demand import Demand
from Splits import SplitMatrixProfile
from Signal import ActuatorSignal
from Controller import ControllerStage
from LaneGroup import LaneGroup
import numpy as np
from Events import Dispatcher
from Output import *
import os
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

    def __init__(self,myid:int):
        self.id = myid
        self.in_links = dict()
        self.out_links = dict()
        self.is_source = True
        self.is_sink = True
        self.is_many2one = False

    def add_input_link(self,link:"Link") -> None:
        self.in_links[link.id] = link
        self.is_source = False

    def add_output_link(self,link:"Link") -> None:
        self.out_links[link.id] = link
        self.is_sink = False

class Network:

    nodes: dict[int,Node]
    links: dict[int,"Link"]
    roadconn: dict[int,RoadConnection]
    num_lgs: int

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
        self.roadconn = dict()
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

            self.roadconn[rc.id] = rc

        # Create lane groups .....................................
        self.num_lgs = 0
        for link in self.links.values():

            # collect outgoing road connections
            out_rcs = [rc for rc in self.roadconn.values() if rc.in_link==link.id]

            # create set of all intersections of out_rcs up lanes
            lane_sets:set[tuple[int,int]] = set()
            for rc in out_rcs:
                if rc.in_link_lanes is None:
                    lane_sets.add((1,link.full_lanes))
                else:
                    lane_sets.add(rc.in_link_lanes)

            lanegroups = list()
            if len(lane_sets)==0:
                lanegroups.append(LaneGroup(link=link,
                                            num_lanes=link.full_lanes,
                                            start_lane=1,
                                            rp=link.roadparam))
            else:

                lane2rcs = list()
                for start_lane in range(1,link.full_lanes+1):
                    lane2rcs.append(frozenset(
                        {rc.id for rc in out_rcs
                         if (start_lane >= rc.in_link_lanes[0]) and
                            (start_lane <= rc.in_link_lanes[1])}
                    ))

                for myrcs in set(lane2rcs):
                    lanes = [lanerc==myrcs for lanerc in lane2rcs]
                    lanes_in_lg = np.where(lanes)[0] + 1
                    lg_start_lane = lanes_in_lg[0]
                    lg_num_lanes = lanes_in_lg.shape[0]
                    lanegroup = LaneGroup(link=link,
                                          num_lanes=lg_num_lanes,
                                          start_lane=lg_start_lane,
                                          rp=link.roadparam)

                    lanegroups.append(lanegroup)

            link.lgs = lanegroups
            self.num_lgs += len(lanegroups)

class Scenario:
    dispatcher : "Dispatcher"
    network : Network
    vtypes : dict[int, "VehicleType"]
    controllers : dict[int,"AbstractController"]
    actuators : dict[int,"AbstractActuator"]       # TODO WHY?
    demands : dict[int,set["Demand"]]              # TODO WHY?
    outputs : list['AbstractOutput']
    folder_prefix : str

    def __init__(self,
                 network_file:str,
                 demand_file:str,
                 control_file:str,
                 output_requests: Optional[list[dict[str, str]]] = None,
                 output_folder: Optional[str] = None,
                 prefix: Optional[str] = None,
                 check: Optional[bool] = False
    ) -> None:

        # read network
        with open(network_file) as f:
            jsonobj = json.load(f)
        self.network = Network(jsonobj)

        # make road connection to incoming lanegroup map
        rc2inlgs = dict()
        for rc in self.network.roadconn.values():
            in_link = self.network.links[rc.in_link]
            lanes = rc.in_link_lanes
            rc2inlgs[rc.id] = [lg for lg in in_link.lgs if
                             (lg.start_lane >= lanes[0]) and
                             (lg.start_lane+lg.num_lanes -1 <= lanes[1]) ]


        # populate link.nextlink2mylgs
        for link in self.network.links.values():
            if not link.is_sink:
                exiting_rcs = [rc for rc in self.network.roadconn.values() if rc.in_link==link.id]
                if len(exiting_rcs)==0:
                    for nextlink in link.endnode.out_links.values():
                        link.nextlink2mylgs[nextlink.id] = link.lgs
                else:
                    for rc in exiting_rcs:
                        link.nextlink2mylgs[rc.out_link]  = rc2inlgs[rc.id]

        with open(demand_file) as f:
            jsonobj = json.load(f)

        # read vehicle types
        self.vtypes = dict()
        for key, val in jsonobj['vehicletypes'].items():
            vtid:int = int(key)
            self.vtypes[vtid] = VehicleType(
                id=vtid,
                name=val['name'],
                pathfull=bool(val['pathfull'])
            )

        # read demands
        self.demands = dict()
        for x in jsonobj['demands']:
            demand:Demand = Demand(x,self)
            linkid = demand.link.id
            if linkid not in self.demands.keys():
                self.demands[linkid] = set()
            self.demands[linkid].add(demand)
            demand.link.demands.append(demand)

        # read splits
        for x in jsonobj['splits']:
            split = SplitMatrixProfile(x,self)
            linkin:Link = split.linkin
            if split.vtype.id in linkin.split_profile.keys():
                raise(Exception("Reapeated splits for link"))
            else:
                linkin.split_profile[split.vtype.id] = split

        with open(control_file) as f:
            jsonobj = json.load(f)

        # read actuators
        self.actuators = dict()
        for strid,jsonact in jsonobj['actuators'].items():
            actid = int(strid)
            acttype = jsonact['type']
            if acttype=='signal':
                self.actuators[actid] = ActuatorSignal(actid,self,jsonact,rc2inlgs)
            else:
                raise(Exception("Error: Unknown actuator type {acttype}"))

        # read controllers
        self.controllers = dict()
        for strid, jsoncnt in jsonobj['controllers'].items():
            cntid = int(strid)
            cnttype = jsoncnt['type']
            cntacts = {int(s):self.actuators[int(s)] for s in jsoncnt['target_actuators'].split(',')}
            if cnttype=='sig_pretimed':
                self.controllers[cntid] = ControllerStage(cntid, jsoncnt, cntacts)
            else:
                raise(Exception(f"Error: Unknown controller type {cnttype}"))

        # output requests
        if output_requests is not None:
            self.folder_prefix = os.path.join(output_folder,prefix)
            self.outputs = list()
            for request in output_requests:
                mytype = request['type']
                if mytype=='link_flw':
                    output = OutputLinkFlow(self,request)
                elif mytype=='link_veh':
                    output = OutputLinkVeh(self,request)
                elif mytype=='lg_flw':
                    output = OutputLanegroupFlow(self,request)
                elif mytype=='lg_veh':
                    output = OutputLanegroupVeh(self,request)
                elif mytype=='veh_events':
                    output = OutputVehicleEvents(self,request)
                elif mytype=='cnt_events':
                    output = OutputControllerEvents(self,request)
                else:
                    raise(Exception("Unknown output type"))
                self.outputs.append(output)

        # build and attach dispatcher
        self.dispatcher = Dispatcher()

        #  timed writer events
        for output in self.outputs:
            output.initialize(self.dispatcher,self.folder_prefix)

        for link in self.network.links.values():
            link.initialize(self)

        for cnt in self.controllers.values():
            cnt.initialize(self)

        if check:
            self.check()

    def check(self) -> bool:
        # TODO Implement this
        return True

    def get_lanegroup_ids(self) -> np.array:
        lgs = np.empty((self.network.num_lgs,2),dtype=int)
        c = 0
        for link in self.network.links.values():
            for lg in link.lgs:
                lgs[c,:] = lg.get_id()
                c += 1
        return lgs

    def reset(self) -> None:
        self.dispatcher = Dispatcher()
        for link in self.network.links.values():
            for lg in link.lgs:
                lg.clear()
        for controller in self.controllers.values():
            controller.reset()

    def set_vehicles(self,queue2vehicles) -> None:
        # state is a 2D numpy array of integers.
        # Each row contains the number of vehicles to assign to a queue in a lanegroup
        # (link_id, start_lane, 0 for transit;1 for waiting, number of vehicles)
        for i in range(queue2vehicles.shape[0]):
            link = self.network.links[queue2vehicles[i,0]]
            lg = link.get_lanegroup_for_startlane(queue2vehicles[i,1])
            if queue2vehicles[i,2]==0:
                lg.set_transit_vehicles(queue2vehicles[i,3])
            else:
                lg.set_waiting_vehicles(queue2vehicles[i,3])

    def get_vehicles(self) -> dict:
        # TODO Implement this
        pass

    def set_controller_command(self,command) -> None:
        # TODO Implement this
        pass

    def advance(self, duration):
        self.dispatcher.dispatch_to_time(self.dispatcher.current_time + duration)

    def close_outputs(self):
        for output in self.outputs:
            output.close()