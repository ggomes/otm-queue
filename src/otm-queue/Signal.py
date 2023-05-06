from typing import TYPE_CHECKING, Optional
from typing import Any
from enum import Enum
from abstract import AbstractActuator, AbstractCommand

if TYPE_CHECKING:
    from core import Scenario
    from LaneGroup import LaneGroup

BulbColor = Enum('BulbColor', ['RED', 'GREEN', 'DARK'])

class CommandSignal(AbstractCommand):
    value: dict[int, BulbColor] # phase, color
    def __init__(self, value: dict[int, BulbColor]) -> None:
        self.value = value

class SignalPhase:
    id: int
    my_signal: Any
    bulbcolor:BulbColor   # state: bulb color and transition pointer
    lanegroups: set["LaneGroup"]

    def __init__(self,scenario, actuator:AbstractActuator , jsonphase) -> None:
        self.my_signal = actuator
        self.phaseid = int(jsonphase['phase'])
        self.lanegroups = set()

        # populate lanegroups
        # rcids = {int(rcid) for rcid in jsonphase['roadconnections'].split(',')}
        # node = self.my_signal.target
        # nodeid = node.id
        # for rcid in rcids:
        #     node = scenario.network.nodes[nodeid]
        #     rc = node.road_connections[rcid]
        #     self.lanegroups.add(rc.get_in_lanegroups())

        # # register
        # for lg in self.lanegroups:
        #     lg.register_actuator(None, self.my_signal);

    def initialize(self)-> None:
        self.bulbcolor = BulbColor.DARK

    def set_bulb_color(self,to_color:BulbColor) -> None:

        # set the state
        self.bulbcolor = to_color

        # compute control rate
        if to_color==BulbColor.RED or to_color==BulbColor.DARK:
            rate_vps = 0.0
        elif to_color==BulbColor.GREEN:
            rate_vps = float('inf')

        # send to lane groups
        for lg in self.lanegroups:
            lg.set_actuator_capacity_vps(rate_vps)

class ActuatorSignal(AbstractActuator):

    signal_phases: dict[int, SignalPhase]

    def __init__(self,id:int, scenario:"Scenario", jsonact) -> None:
        super().__init__(id,scenario, jsonact)

        # read signal phases
        self.signal_phases = dict()
        for jsonphase in jsonact['signal']:
            phaseid = int(jsonphase['phase'])
            self.signal_phases[phaseid] = SignalPhase(scenario, self, jsonphase)

        # register the actuator
        self.target.register_actuator(self)

    def initialize(self) -> None:
        for p in self.signal_phases.values():
            p.initialize()

    def process_command(self, timestamp: float) -> None:

        if self.command is None:
            return

        # The command is a map from signal phase to color.
        # anything not in the map should be set to red
        signalcommand:dict[int, BulbColor]= self.command.value  # type: ignore
        for phase_id, signalphase in self.signal_phases.items():
            if phase_id in signalcommand.keys():
                bulbcolor = signalcommand[phase_id]
            else:
                bulbcolor = BulbColor.RED
            signalphase.set_bulb_color(bulbcolor)