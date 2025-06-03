# latency_model/access_delay.py

def access_delay_sr(sr_rounds: int, slot_duration_us: float) -> float:
    """
    Compute access delay (uplink grant acquisition) as number of SR rounds * slot duration.

    Args:
        sr_rounds: number of scheduling request opportunities until grant
        slot_duration_us: duration of one slot in microseconds

    Returns:
        Access delay in milliseconds
    """
    # Convert microseconds to milliseconds
    return sr_rounds * slot_duration_us / 1000.0
