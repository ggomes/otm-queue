from abc import ABC, abstractmethod
from typing import TYPE_CHECKING,Optional, Any
if TYPE_CHECKING:
    from core import Scenario
    from Events import Dispatcher
    from Output import OutputControllerEvents

class AbstractEvent(ABC):
    timestamp: float
    dispatch_order: int
    recipient: Any

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
    def process_command(self, timestamp: float,dispatcher:'Dispatcher') -> None: pass

    @abstractmethod
    def register_with_targets(self) -> None: pass

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
        self.process_command(timestamp,dispatcher)

        # wake up in dt, if dt is defined
        if self.dt is not None:
            dispatcher.register_event(EventPoke(dispatcher,3,timestamp+self.dt,self))

class AbstractController(ABC):
    id:int
    type:str
    actuators:dict[int,AbstractActuator]
    command:dict[int, Optional[AbstractCommand]] # actuator id -> command
    dt:Optional[float]
    event_writer:Optional['OutputControllerEvents']

    @abstractmethod
    def update_command(self, dispatcher) -> None: pass

    @abstractmethod
    def reset(self) -> None: pass

    def write_event(self,timestamp:float,val:str) -> None:
        if self.event_writer is not None:
            self.event_writer.file.write('{},{},{}\n'.format(timestamp,self.id,val))

    def __init__(self,id:int,jsoncntrl,acts:dict[int,AbstractActuator]):
        self.id = id
        self.actuators = acts
        self.command = dict()
        self.dt = None if 'dt' not in jsoncntrl.keys() else float(jsoncntrl['dt'])
        self.type = jsoncntrl['type']
        self.event_writer = None

    def add_acuator(self,act:AbstractActuator):
        self.actuators[act.id] = act

    def register_event_writer(self,x:'OutputControllerEvents') -> None:
        if self.event_writer is None:
            self.event_writer = x

    def poke(self,dispatcher, timestamp:float ) -> None:

        self.update_command(dispatcher)

        # send to actuators and poke immediately actuators that lack a dt
        for act in self.actuators.values():
            act.command = self.command.get(act.id)
            if act.dt is None:
                act.poke(dispatcher,timestamp)

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

    def __init__(self,scenario:'Scenario',request:dict[str,str]) -> None:
        self.scenario = scenario
        self.mytype = request['type']
        self.file = None

    def open_output_file(self, dispatcher: 'Dispatcher', folder_prefix:str) -> None:
        self.file = open(f"{folder_prefix}_{self.get_name()}.csv", 'w')
        self.file.write(self.get_header()+'\n')

    def close(self) -> None:
        self.file.close()

class AbstractOutputTimed(AbstractOutput, ABC):
    dt:float

    @abstractmethod
    def get_str(self) -> str: pass

    def __init__(self,scenario:'Scenario',request:dict[str,str]) -> None:
        super().__init__(scenario,request)
        self.dt = float(request['dt'])

    def open_output_file(self, dispatcher, folder_prefix) -> None:
        super().open_output_file(dispatcher, folder_prefix)
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
