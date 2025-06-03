def processing_delay_coding_decoding(coding_time_us: float, decoding_time_us: float) -> float:
    """
    Compute processing delay for coding and decoding.

    Args:
        coding_time_us: time to code a transport block in microseconds
        decoding_time_us: time to decode in microseconds

    Returns:
        Processing delay in milliseconds
    """
    return (coding_time_us + decoding_time_us) / 1000.0
