from typing import Optional
import numpy as np

def get_waiting_time(rate: float) -> Optional[float]:

    if rate<0:
        return float('inf')

    process = 'poisson'

    wait = 0.0
    if process == 'poisson':
        wait = -np.log(1.0 - np.random.rand()) / rate
    elif process == 'deterministic':
        wait = 1.0 / rate
    else:
        print("Error: Unknown process")

    return wait
