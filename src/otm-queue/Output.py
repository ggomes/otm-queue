from abstract import AbstractOutput, AbstractOutputTimed
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from core import Scenario

def read_links(scenario,request):
    if 'links' in request.keys():
        return [scenario.network.links[int(linkid)] for linkid in request['links'].split(',')]
    else:
        return list(scenario.network.links.values())

class OutputLinkFlow(AbstractOutputTimed):

    def __init__(self,scenario:'Scenario',request:dict[str,str]) -> None:
        super().__init__(scenario,request)
        self.links = read_links(scenario,request)

    def get_name(self) -> str:
        return "linkflw"

    def get_header(self) -> str:
        return 'time,'+','.join([str(link.id) for link in self.links])

    def get_str(self) -> str:
        return ','.join([str(link.exit_count()) for link in self.links])

class OutputLinkVeh(AbstractOutputTimed):

    def __init__(self,scenario:'Scenario',request:dict[str,str]) -> None:
        super().__init__(scenario,request)
        self.links = read_links(scenario,request)

    def get_name(self) -> str:
        return "linkveh"

    def get_header(self) -> str:
        return 'time,'+','.join([str(link.id) for link in self.links])

    def get_str(self) -> str:
        return ','.join([str(link.get_num_vehicles()) for link in self.links])

class OutputLanegroupFlow(AbstractOutputTimed):

    def __init__(self,scenario:'Scenario',request:dict[str,str]) -> None:
        super().__init__(scenario,request)
        self.links = read_links(scenario,request)

    def get_name(self) -> str:
        return "lgflw"

    def get_header(self) -> str:
        header = 'time,'
        for link in self.scenario.network.links.values():
            for lg in link.lgs:
                header += "({};{}),".format(link.id, lg.start_lane)
        return header[:-1]

    def get_str(self) -> str: 
        z = ''
        for link in self.scenario.network.links.values():
            z += ','+','.join([str(lg.exit_count) for lg in link.lgs])
        return z[1:]

class OutputLanegroupVeh(AbstractOutputTimed):

    def __init__(self,scenario:'Scenario',request:dict[str,str]) -> None:
        super().__init__(scenario,request)
        self.links = read_links(scenario,request)

    def get_name(self) -> str:
        return "lgveh"

    def get_header(self) -> str:
        header = 'time,'
        for link in self.scenario.network.links.values():
            for lg in link.lgs:
                header += "({};{}),".format(link.id, lg.start_lane)
        return header[:-1]

    def get_str(self) -> str:
        z = ''
        for link in self.scenario.network.links.values():
            z += ','+','.join([str(lg.get_total_vehicles()) for lg in link.lgs])
        return z[1:]

class OutputControllerEvents(AbstractOutput):

    def __init__(self,scenario:'Scenario',request:dict[str,str]) -> None:
        super().__init__(scenario,request)
        if 'ctrls' in request.keys():
            self.ctrls = [scenario.controllers[int(cntrlid)] for cntrlid in request['ctrls'].split(',')]
        else:
            self.ctrls = list(scenario.controllers.values())

        for cntrl in  self.ctrls:
            cntrl.register_event_writer(self)

    def get_name(self) -> str:
        return "ctrl"

    def get_header(self) -> str:
        return 'time,id,event'
