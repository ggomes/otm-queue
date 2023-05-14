from dataclasses import dataclass
from typing import TYPE_CHECKING
from Signal import BulbColor, CommandSignal
from abstract import AbstractController, EventPoke

if TYPE_CHECKING:
    from abstract import AbstractActuator
    from Signal import ActuatorSignal


@dataclass
class StageindexReltime:
    index:int
    reltime:float

class Stage:

    duration:float          # duration in seconds of the stage, including
    phase_ids:set[int]
    cycle_starttime : float   # start time of this stage relative to

    def __init__(self,jsonstage) -> None:
        self.duration = float(jsonstage['duration'])
        self.phase_ids = {int(s) for s in jsonstage['phases'].split(',')}

class ControllerStage(AbstractController):

    cycle: float
    offset: float
    stages: list[Stage]
    curr_stage_index: int
    signal:'ActuatorSignal'

    def __init__(self,selfid:int, jsoncntrl,acts:dict[int,'AbstractActuator']) -> None:
        super().__init__(selfid,jsoncntrl,acts)

        self.signal = next(iter(self.actuators.values()))  # type: ignore

        self.stages = list()
        for jsonstage in jsoncntrl['stages']:
            self.stages.append(Stage(jsonstage))

        # parameters
        for p in jsoncntrl['parameters']:
            name = p['name']
            value = p['value']

            if name=='cycle':
                self.cycle = float(value)
            elif name=='offset':
                self.offset = float(value)
            else:
                print(f"Error: Unknown parameter {name}")

        # set start_time
        relstarttime = 0.0
        for stage in self.stages:
            stage.cycle_starttime = relstarttime%self.cycle
            relstarttime += stage.duration

    def initialize(self,scenario) -> None:
        super().initialize(scenario)

    def reset(self) -> None:
        pass

    def update_command(self, dispatcher) -> None:
        now = dispatcher.current_time
        x = self.get_stage_for_time(now)   # StageindexReltime

        self.set_stage_index(x.index)

        # register next poke
        next_stage_start = now - x.reltime + self.stages[x.index].duration
        dispatcher.register_event(EventPoke(dispatcher,2,next_stage_start,self))

    # Get the command that represents a given stage index
    def get_command_for_stage_index(self,index:int) -> CommandSignal:
        command: dict[int, BulbColor]  = dict()
        for phase_id in self.stages[index].phase_ids:
            command[phase_id] = BulbColor.GREEN
        return CommandSignal(command)

    # Set the current stage
    def set_stage_index(self,index:int) -> None:
        self.curr_stage_index = index
        c:CommandSignal = self.get_command_for_stage_index(index)
        self.command[self.signal.id] = c

    # for an absolute time value, returns the stage index and time
    # relative to the beginning of the cycle (offset time).
    # Assumes periodic extension in both directions.
    def get_stage_for_time(self,time:float) -> StageindexReltime:

        reltime = (time-self.offset)%self.cycle
        start_time = .0

        for index,stage in  enumerate(self.stages):
            end_time = start_time + stage.duration
            if end_time>reltime:
                return StageindexReltime(index,reltime-start_time)
            start_time = end_time

        return StageindexReltime(0,0)

    def __str__(self) -> str:
        return "cntr id={}".format(self.id)


