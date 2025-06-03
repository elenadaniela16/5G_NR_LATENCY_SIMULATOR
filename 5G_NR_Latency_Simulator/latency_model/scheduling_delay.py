def scheduling_delay(k_slots: int, slot_duration_us: float, algo_factor: float = 1.0) -> float:
    """
    Compute scheduling delay as k_slots * slot_duration * algorithm factor.

    Args:
        k_slots: number of slots waited until scheduling
        slot_duration_us: slot duration in microseconds
        algo_factor: factor accounting for scheduler processing overhead

    Returns:
        Scheduling delay in milliseconds
    """
    return k_slots * slot_duration_us * algo_factor / 1000.0