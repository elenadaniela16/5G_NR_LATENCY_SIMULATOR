from .access_delay import access_delay_sr
from .scheduling_delay import scheduling_delay
from .transmission_delay import transmission_delay_bits
from .processing_delay import processing_delay_coding_decoding
from .harq_delay import harq_delay
from .propagation_delay import propagation_delay


def total_latency(params: dict) -> float:
    """
    Compute total radio latency given parameter dictionary.

    Expected params:
        sr_rounds, k_slots, slot_duration_us,
        packet_size_bits, spectral_efficiency, bandwidth_hz,
        coding_time_us, decoding_time_us,
        num_retx, feedback_delay_us, retransmission_duration_us,
        distance_m

    Returns:
        Total latency in milliseconds
    """
    T_access = access_delay_sr(params['sr_rounds'], params['slot_duration_us'])
    T_sched = scheduling_delay(params['k_slots'], params['slot_duration_us'], params.get('algo_factor', 1.0))
    T_tx = transmission_delay_bits(params['packet_size_bits'], params['spectral_efficiency'], params['bandwidth_hz'])
    T_proc = processing_delay_coding_decoding(params['coding_time_us'], params['decoding_time_us'])
    T_harq = harq_delay(params['num_retx'], params['feedback_delay_us'], params['retransmission_duration_us'])
    T_prop = propagation_delay(params['distance_m'])
    return T_access + T_sched + T_tx + T_proc + T_harq + T_prop
