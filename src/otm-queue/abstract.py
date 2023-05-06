from abc import ABC, abstractmethod
from typing import TYPE_CHECKING,Optional, Any
import os
if TYPE_CHECKING:
    from core import Scenario
    from Events import Dispatcher

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

    def __str__(self) -> str:
        return "time: {:.2f}, event: {}, recipient: {}".format(
            self.timestamp,
            self.__class__.__name__,
            self.recipient
        )

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

    def __init__(self, selfid:int, scenario:"Scenario", jsonact):

        self.id = selfid
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

class AbstractOutput(ABC):

    scenario : 'Scenario'
    mytype : str

    @abstractmethod
    def get_name(self) -> str: pass

    @abstractmethod
    def get_header(self) -> str: pass

    @abstractmethod
    def get_str(self) -> str: pass

    def __init__(self,scenario:'Scenario',request:dict[str,str]) -> None:
        self.scenario = scenario
        self.mytype = request['type']
        self.file = None

    def initialize(self,dispatcher:'Dispatcher',folder_prefix:str) -> None:
        self.file = open(f"{folder_prefix}_{self.get_name()}.csv", 'w')
        self.file.write(self.get_header()+'\n')

    def close(self) -> None:
        self.file.close()

class AbstractOutputTimed(AbstractOutput, ABC):
    dt:float

    def __init__(self,scenario:'Scenario',request:dict[str,str]) -> None:
        super().__init__(scenario,request)
        self.dt = float(request['dt'])

    def initialize(self, dispatcher,folder_prefix) -> None:
        super().initialize(dispatcher,folder_prefix)
        dispatcher.register_event(EventPoke(dispatcher,
                                            dispatch_order=70,
                                            timestamp=0.0,
                                            recipient=self))

    def poke(self,dispatcher:'Dispatcher', timestamp:float) -> None:
        self.file.write('{},{}\n'.format(timestamp,self.get_str()))
        dispatcher.register_event(EventPoke(dispatcher,
                                            dispatch_order=70,
                                            timestamp=timestamp + self.dt,
                                            recipient=self))
