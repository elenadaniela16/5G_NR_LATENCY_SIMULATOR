def propagation_delay(distance_m: float, c: float = 3e8) -> float:
    """
    Compute propagation delay as distance / speed of light.

    Args:
        distance_m: propagation distance in meters
        c: speed of light in m/s

    Returns:
        Propagation delay in milliseconds
    """
    return distance_m / c * 1000.0
