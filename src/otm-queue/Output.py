from abstract import AbstractOutput, AbstractOutputTimed
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from core import Scenario

class OutputLinkFlow(AbstractOutputTimed):

    def __init__(self,scenario:'Scenario',request:dict[str,str]) -> None:
        super().__init__(scenario,request)

    def get_name(self) -> str:
        return "linkflw"

    def get_header(self) -> str:
        return 'not implemented'

    def get_str(self) -> str:
        return '.'

class OutputLinkVeh(AbstractOutputTimed):

    def __init__(self,scenario:'Scenario',request:dict[str,str]) -> None:
        super().__init__(scenario,request)

    def get_name(self) -> str:
        return "linkveh"

    def get_header(self) -> str:
        return 'time,'+','.join([str(link.id) for link in self.scenario.network.links.values()])

    def get_str(self) -> str:
        return ','.join([str(link.get_num_vehicles()) for link in self.scenario.network.links.values()])

class OutputLanegroupFlow(AbstractOutputTimed):

    def __init__(self,scenario:'Scenario',request:dict[str,str]) -> None:
        super().__init__(scenario,request)

    def get_name(self) -> str:
        return "lgflw"

    def get_header(self) -> str:
        return 'not implemented'

    def get_str(self) -> str: 
        return '.'

class OutputLanegroupVeh(AbstractOutputTimed):

    def __init__(self,scenario:'Scenario',request:dict[str,str]) -> None:
        super().__init__(scenario,request)

    def get_name(self) -> str:
        return "lgveh"

    def get_header(self) -> str:
        header = 'time,'
        for link in self.scenario.network.links.values():
            for lg in link.lgs:
                header += "({};{};{}),".format(link.id, lg.start_lane, lg.num_lanes)
        return header[:-1]

    def get_str(self) -> str:
        z = ''
        for link in self.scenario.network.links.values():
            z += ','+','.join([str(lg.get_total_vehicles()) for lg in link.lgs])
        return z[1:]
    
class OutputVehicleEvents(AbstractOutput):

    def __init__(self,scenario:'Scenario',request:dict[str,str]) -> None:
        super().__init__(scenario,request)

    def get_name(self) -> str:
        return "veh"

    def get_header(self) -> str:
        return 'not implemented'

    def get_str(self) -> str:
        return '.'

class OutputControllerEvents(AbstractOutput):

    def __init__(self,scenario:'Scenario',request:dict[str,str]) -> None:
        super().__init__(scenario,request)

    def get_name(self) -> str:
        return "cnt"

    def get_header(self) -> str:
        return 'not implemented'

    def get_str(self) -> str:
        return '.'