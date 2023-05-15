from dataclasses import dataclass

@dataclass
class RoadConnection:
    id:int
    in_link:int
    in_link_lanes:tuple[int,int]
    out_link:int

@dataclass
class RoadParams:
    capacity : float
    speed : float
    jam_density : float

