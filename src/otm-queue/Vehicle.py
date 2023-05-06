from static import get_vehicle_id
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from LaneGroup import VehicleQueue
    from SimpleClasses import VehicleType

class Vehicle:

    id:int
    vtype:'VehicleType'
    next_link_id:int
    my_queue:'VehicleQueue'
    lg:'LaneGroup'

    # dispatch listeners
    # listener : VehicleListener

    def __init__(self, vtype:'VehicleType') -> None :
        self.id = get_vehicle_id()
        self.vtype = vtype
        self.next_link_id = -1
        self.my_queue = None
        self.lg = None
        # self.listener = listener

    def set_next_link_id(self, nextlink_id:int) -> None:
        self.next_link_id=nextlink_id

    # def get_next_link_id(self) -> int:
    #     if self.lg.link.is_sink:
    #         return -1
    #     return self.next_link_id

    def move_to_queue(self,timestamp:float,to_lg:'LaneGroup',to_queue:'VehicleQueue') -> None:

        from_queue = self.my_queue

        # remove vehicle from its current queue
        if from_queue is not None:
            from_queue.remove_given_vehicle(timestamp, self)

        # add to the to_queue
        to_queue.add_vehicle(self)

        # update vehicle queue
        self.my_queue = to_queue
        self.lg = to_lg