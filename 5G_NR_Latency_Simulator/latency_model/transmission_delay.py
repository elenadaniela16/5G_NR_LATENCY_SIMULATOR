def transmission_delay_bits(packet_size_bits: int, spectral_efficiency: float, bandwidth_hz: float) -> float:
    """
    Compute transmission delay = packet_size / (efficiency * bandwidth).

    Args:
        packet_size_bits: number of bits in packet
        spectral_efficiency: bits/s/Hz (Qm*code_rate)
        bandwidth_hz: total used bandwidth in Hz

    Returns:
        Transmission delay in milliseconds
    """
    rate_bps = spectral_efficiency * bandwidth_hz
    return packet_size_bits / rate_bps * 1000.0