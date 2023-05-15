# from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional
from Events import Dispatcher, EventSplitChange
from Link import Link
# from SimpleClasses import VehicleType
import numpy as np

if TYPE_CHECKING:
    from core import Scenario

Link2Split = tuple[np.array,np.array]  # list of outlink ids and corresponding splits

class Profile2D:
    dt: Optional[float]
    values: dict[int,np.array]  # linkout->profile
    linksout: np.array
    num_times: int

    def __init__(self, splitjson:dict[str,str], dt:Optional[float]=None) -> None:
        self.dt = dt

        self.values = dict()
        linkoutlist = list()
        for strid, v in splitjson.items():
            linkoutid = int(strid)
            vals = np.array([float(s) for s in v.split(',')])
            if linkoutid in self.values.keys():
                print(f"Warning: Overwriting split profile")
            else:
                self.values[linkoutid] = vals
                linkoutlist.append(linkoutid)

        x = np.unique([val.shape[0] for val in self.values.values()])
        if x.shape[0]!=1:
            raise(Exception("Bad values in split ratio"))

        self.num_times = x[0]
        self.linksout = np.array(linkoutlist)

    def get_value_for_time(self,time:float) -> Link2Split:
        if (self.dt is None) or (self.dt==0):
            return self.get_ith_value(0)
        return self.get_ith_value( int(time/self.dt) )

    # get values for time index i
    def get_ith_value(self,i:int) -> Link2Split:
        splits = np.empty(self.linksout.shape[0])
        step = max(0,min(i,self.num_times-1))
        for k,linkid in enumerate(self.linksout):
            splits[k] = self.values[linkid][step]
        return self.linksout, splits

class SplitMatrixProfile:

    linkin: Link
    dt: Optional[float]
    profile: Profile2D    # link out id -> split profile

    # current status
    outlink2split: Link2Split   # out link id -> split

    def __init__(self,splitjson:dict[str,str],scenario:'Scenario') -> None:
        linkinid = int(splitjson['link_in'])
        self.dt = float(splitjson['dt']) if 'dt' in splitjson.keys() else None
        self.linkin = scenario.network.links[linkinid]
        # noinspection PyTypeChecker
        self.profile = Profile2D(splitjson['link_out_value'],self.dt)

    def set_all_current_splits(self, newsplit:Link2Split) -> None:
        self.outlink2split = newsplit

    def get_change_following(self,now:float) -> Optional[tuple[float,Link2Split]]:

        if (self.dt is None) or (self.dt==0) :
            return None

        index = int((now+self.dt)/self.dt)
        if index>=self.profile.num_times:
            return None

        return index*self.dt , self.profile.get_ith_value(index)

    # return an output link id according to split ratios for this commodity and line
    def sample_output_link(self) -> int :
        return np.random.choice(self.outlink2split[0], p=self.outlink2split[1])

    def register_next_change(self, dispatcher:Dispatcher, time:float, splitvalue:Link2Split) -> None:
        if splitvalue is not None:
            dispatcher.register_event(EventSplitChange(dispatcher,time, self, splitvalue))

    def __str__(self) -> str:
        return "link={}".format(self.linkin.id)