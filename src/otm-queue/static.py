from typing import Optional
import numpy as np

vehicle_id_count = 0

def get_service_period(rate: float) -> Optional[float]:

    if rate<=0:
        return None

    process = 'poisson'

    period = 0.0
    if process == 'poisson':
        period = -np.log(1.0 - np.random.rand()) / rate
    elif process == 'deterministic':
        period = 1.0 / rate
    else:
        print("Error: Unknown process")
    return period

def get_vehicle_id():
    global vehicle_id_count
    vehicle_id_count += 1
    return vehicle_id_count

