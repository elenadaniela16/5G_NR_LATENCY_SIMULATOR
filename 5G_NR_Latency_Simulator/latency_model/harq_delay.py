def harq_delay(num_retx: int, feedback_delay_us: float, retransmission_duration_us: float) -> float:
    """
    Compute HARQ delay including feedback and retransmission durations.

    Args:
        num_retx: number of retransmissions performed
        feedback_delay_us: per-HARQ feedback delay in microseconds
        retransmission_duration_us: duration of one retransmission in microseconds

    Returns:
        HARQ total delay in milliseconds
    """
    return (num_retx * (feedback_delay_us + retransmission_duration_us)) / 1000.0
