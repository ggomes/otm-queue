from abc import ABC, abstractmethod
from typing import TYPE_CHECKING,Optional, Any
if TYPE_CHECKING:
    from core import Scenario

class AbstractEvent(ABC):
    timestamp: float
    recipient: Any
    dispatch_order: int

    def __init__(self, dispatcher, dispatch_order: int, timestamp: float, recipient: Any) -> None:
        self.dispatcher = dispatcher
        self.dispatch_order = dispatch_order
        self.timestamp = timestamp
        self.recipient = recipient

    @abstractmethod
    def action(self) -> None:
        pass

    def __lt__(self, that):
        if self.timestamp < that.timestamp:
            return False
        if that.timestamp < self.timestamp:
            return True
        if self.dispatch_order < that.dispatch_order:
            return False
        if that.dispatch_order < self.dispatch_order:
            return True
        return False

class EventPoke(AbstractEvent):

    def __init__(self,dispatcher, dispatch_order:int, timestamp:float, recipient) -> None:
        super().__init__(dispatcher, dispatch_order, timestamp, recipient)

    def action(self):
        self.recipient.poke(self.dispatcher,self.timestamp)

class AbstractCommand(ABC):
    pass

class AbstractActuator(ABC):

    id:int
    type:str
    dt:Optional[float]     # dt<=0 means event based (vehicle model) or dt=sim dt (fluid model)
    target:Any
    command:Optional[AbstractCommand]

    @abstractmethod
    def process_command(self, timestamp: float) -> None: pass

    def __init__(self, id:int, scenario:"Scenario", jsonact):

        self.id = id
        self.type = jsonact['type']
        self.dt = float(jsonact['dt']) if 'dt' in jsonact.keys() else None
        self.command = None

        jsontarget = jsonact['target']

        tgttype = jsontarget['type']
        if tgttype=='node':
            nodeid = int(jsontarget['id'])
            self.target = scenario.network.nodes[nodeid]
        else:
            print(f'Error: Unknown target type {tgttype}')


    def poke(self,dispatcher, timestamp:float):

        # process the command
        self.process_command(timestamp)

        # wake up in dt, if dt is defined
        if self.dt is not None:
            dispatcher.register_event(EventPoke(dispatcher,3,timestamp+self.dt,self))

class AbstractController(ABC):
    id:int
    type:str
    actuators:dict[int,AbstractActuator]
    command:dict[int, Optional[AbstractCommand]] # actuator id -> command
    dt:Optional[float]

    # event_output:OutputController


    @abstractmethod
    def update_command(self, dispatcher) -> None:
        pass

    def __init__(self,id:int,jsoncntrl,acts:dict[int,AbstractActuator]):
        self.id = id
        self.actuators = acts
        self.command = dict()
        self.dt = None if 'dt' not in jsoncntrl.keys() else float(jsoncntrl['dt'])
        self.type = jsoncntrl['type']

    def add_acuator(self,act:AbstractActuator):
        self.actuators[act.id] = act

    def initialize(self,scenario) -> None:
        self.poke(scenario.dispatcher, scenario.dispatcher.current_time)

    def poke(self,dispatcher, timestamp:float ) -> None:

        self.update_command(dispatcher)

        # send to actuators and poke immediately actuators that lack a dt
        for act in self.actuators.values():
            act.command = self.command.get(act.id)
            if act.dt is None:
                act.poke(dispatcher,timestamp)

        # write to output
        # if event_output is not None:
        #     event_output.write(EventWrapperController(timestamp, command))

        # wake up in dt, if dt is defined
        if (self.dt is not None) and (self.dt > 0):
            dispatcher.register_event(EventPoke(dispatcher, 20, timestamp + self.dt, self))
