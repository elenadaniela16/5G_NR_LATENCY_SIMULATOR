'''
traffic.py

Module to generate traffic events (periodic and aperiodic) and maintain per-UE packet buffers.
'''
from collections import deque
import random
import math

def generate_periodic(ue_id: int, period_ms: float, packet_size_bits: int, sim_time_ms: float) -> deque:
    '''
    Generate periodic traffic for a single UE.

    Args:
        ue_id: Unique identifier for the UE
        period_ms: Interval between packets in milliseconds
        packet_size_bits: Size of each packet in bits
        sim_time_ms: Total simulation time in milliseconds

    Returns:
        deque of packet events: each event is a dict with keys 'time_ms', 'ue_id', 'size_bits'
    '''
    buf = deque()
    t = 0.0
    while t < sim_time_ms:
        buf.append({'time_ms': t, 'ue_id': ue_id, 'size_bits': packet_size_bits})
        t += period_ms
    return buf


def generate_aperiodic(ue_id: int, rate_lambda: float, packet_size_bits: int, sim_time_ms: float) -> deque:
    '''
    Generate aperiodic (Poisson) traffic for a single UE using exponential inter-arrivals.

    Args:
        ue_id: Unique identifier for the UE
        rate_lambda: Average packet arrival rate (packets per ms)
        packet_size_bits: Size of each packet in bits
        sim_time_ms: Total simulation time in milliseconds

    Returns:
        deque of packet events
    '''
    buf = deque()
    t = 0.0
    while t < sim_time_ms:
        inter_arrival = random.expovariate(rate_lambda)
        t += inter_arrival
        if t < sim_time_ms:
            buf.append({'time_ms': t, 'ue_id': ue_id, 'size_bits': packet_size_bits})
    return buf


class TrafficManager:
    '''
    Maintains per-UE packet buffers for traffic events.
    '''
    def __init__(self, n_ues: int, traffic_type: str, params: dict):
        self.buffers = {ue: deque() for ue in range(n_ues)}
        self.traffic_type = traffic_type
        self.params = params

    def initialize(self):
        '''Generate traffic for all UEs based on traffic_type.'''
        for ue in range(len(self.buffers)):
            if self.traffic_type == 'periodic':
                self.buffers[ue] = generate_periodic(
                    ue,
                    self.params['period_ms'],
                    self.params['packet_size_bits'],
                    self.params['sim_time_ms']
                )
            else:
                # Convert rate per ms
                rate = self.params.get('lambda_per_ms', 1.0)
                self.buffers[ue] = generate_aperiodic(
                    ue,
                    rate,
                    self.params['packet_size_bits'],
                    self.params['sim_time_ms']
                )

    def get_ready_ues(self, current_time_ms: float) -> list:
        '''
        Return list of UEs that have packets ready at or before current_time_ms.
        '''
        ready = []
        for ue, buf in self.buffers.items():
            if buf and buf[0]['time_ms'] <= current_time_ms:
                ready.append(ue)
        return ready

    def pop_packet(self, ue: int):
        '''Pop and return the next packet event for a UE.'''
        return self.buffers[ue].popleft() if self.buffers[ue] else None

    def has_packets(self) -> bool:
        '''Return True if any UE buffer is non-empty.'''
        return any(len(buf) > 0 for buf in self.buffers.values())
