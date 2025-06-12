from collections import deque
import random
from simulator.config import default_params

def generate_periodic(ue_id: int, period_ms: float, packet_size_bits: int, sim_time_ms: float) -> deque:
    buf = deque()
    t = 0.0
    while t < sim_time_ms:
        buf.append({'time_ms': t, 'ue_id': ue_id, 'size_bits': packet_size_bits})
        t += period_ms
    return buf

def generate_aperiodic(ue_id: int, rate_lambda: float, packet_size_bits: int, sim_time_ms: float) -> deque:
    buf = deque()
    t = 0.0
    while t < sim_time_ms:
        inter_arrival = random.expovariate(rate_lambda)
        t += inter_arrival
        if t < sim_time_ms:
            buf.append({'time_ms': t, 'ue_id': ue_id, 'size_bits': packet_size_bits})
    return buf


class TrafficManager:
    def __init__(self, n_ues: int, traffic_type: str, params: dict):
        self.buffers = {ue: deque() for ue in range(n_ues)}
        self.traffic_type = traffic_type
        self.params = params
        self.arrival_slots = {}

    def initialize(self):
        n_ues = len(self.buffers)

        # pull defaults from config.py
        base_period       = self.params.get('period_ms',       default_params['period_ms'])
        period_spread     = self.params.get('period_spread_pct',   default_params['period_spread_pct'])
        base_lambda       = self.params.get('lambda_per_ms',   default_params['lambda_per_ms'])
        lambda_spread     = self.params.get('lambda_spread_pct',   default_params['lambda_spread_pct'])

        for ue in range(n_ues):
            if self.traffic_type == 'periodic':
                # per-UE random spread around base_period
                if period_spread and period_spread > 0.0:
                    factor = random.uniform(1.0 - period_spread, 1.0 + period_spread)
                    ue_period = base_period * factor
                    print(f"[DEBUG] UE {ue}: period_ms = {ue_period:.3f}")
                else:
                    ue_period = base_period

                self.buffers[ue] = generate_periodic(
                    ue,
                    ue_period,
                    self.params['packet_size_bits'],
                    self.params['sim_time_ms']
                )
            else:
                # per-UE random spread around base_lambda
                if lambda_spread and lambda_spread > 0.0:
                    factor = random.uniform(1.0 - lambda_spread, 1.0 + lambda_spread)
                    ue_lambda = base_lambda * factor
                    print(f"[DEBUG] UE {ue}: lambda_per_ms = {ue_lambda:.4f}")
                else:
                    ue_lambda = base_lambda

                self.buffers[ue] = generate_aperiodic(
                    ue,
                    ue_lambda,
                    self.params['packet_size_bits'],
                    self.params['sim_time_ms']
                )

    def get_ready_ues(self, current_time_ms: float) -> list:
        return [ue for ue, buf in self.buffers.items() if buf and buf[0]['time_ms'] <= current_time_ms]

    def pop_packet(self, ue: int, arrival_slot: int = None):
        if not self.buffers[ue]:
            return None
        ev = self.buffers[ue].popleft()
        if arrival_slot is not None:
            self.arrival_slots[ue] = arrival_slot
        return ev

    def has_packets(self) -> bool:
        return any(len(buf) > 0 for buf in self.buffers.values())
