from abstract import AbstractOutput, AbstractOutputTimed
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from core import Scenario

class OutputLinkFlow(AbstractOutputTimed):

    def __init__(self,scenario:'Scenario',request:dict[str,str]) -> None:
        super().__init__(scenario,request)

    def get_name(self) -> str:
        return "linkflw"

    def get_str(self) -> str: 
        return '.'

class OutputLinkVeh(AbstractOutputTimed):

    def __init__(self,scenario:'Scenario',request:dict[str,str]) -> None:
        super().__init__(scenario,request)

    def get_name(self) -> str:
        return "linkveh"

    def get_str(self) -> str: 
        return '.'

class OutputLanegroupFlow(AbstractOutputTimed):

    def __init__(self,scenario:'Scenario',request:dict[str,str]) -> None:
        super().__init__(scenario,request)

    def get_name(self) -> str:
        return "lgflw"

    def get_str(self) -> str: 
        return '.'
class OutputLanegroupVeh(AbstractOutputTimed):

    def __init__(self,scenario:'Scenario',request:dict[str,str]) -> None:
        super().__init__(scenario,request)

    def get_name(self) -> str:
        return "lgveh"

    def get_str(self) -> str: 
        return '.'
    
class OutputVehicleEvents(AbstractOutput):

    def __init__(self,scenario:'Scenario',request:dict[str,str]) -> None:
        super().__init__(scenario,request)

    def get_name(self) -> str:
        return "veh"

    def get_str(self) -> str:
        return '.'

class OutputControllerEvents(AbstractOutput):

    def __init__(self,scenario:'Scenario',request:dict[str,str]) -> None:
        super().__init__(scenario,request)

    def get_name(self) -> str:
        return "cnt"

    def get_str(self) -> str:
        return '.'