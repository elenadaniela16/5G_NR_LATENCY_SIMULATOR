from collections import deque
import random
from simulator.config import default_params

# ────────────────────────────────────────────────────────────
#     FUNCȚII PENTRU GENERAREA TRAFICULUI (Periodic/Aperiodic)
# ────────────────────────────────────────────────────────────

def generate_periodic(ue_id: int, period_ms: float, packet_size_bits, sim_time_ms: float) -> deque:
    """
    Generează trafic periodic pentru un UE:
      - ue_id: ID-ul utilizatorului
      - period_ms: intervalul între pachete (ms)
      - packet_size_bits: dimensiunea pachetului (int sau dict per UE)
      - sim_time_ms: durata totală a simulării (ms)
    Returnează un deque cu evenimente planificate.
    """
    # Determină dimensiunea pachetului pentru acest UE
    size = packet_size_bits[ue_id] if isinstance(packet_size_bits, dict) else packet_size_bits

    buf = deque()
    # Fază inițială aleatoare pentru a evita burst-ul sincron la t = 0
    t = random.uniform(0, period_ms)
    # Planifică pachete la fiecare periodă până la sfârșitul simulării
    while t < sim_time_ms:
        buf.append({
            'time_ms':   t,      # momentul sosirii pachetului
            'ue_id':     ue_id,  # ID-ul UE
            'size_bits': size    # dimensiunea pachetului
        })
        t += period_ms
    return buf


def generate_aperiodic(ue_id: int, rate_lambda: float, packet_size_bits, sim_time_ms: float) -> deque:
    """
    Generează trafic aperiodic (Poisson) pentru un UE:
      - rate_lambda: rata medie de sosiri (1/ms)
      Restul parametrilor ca mai sus.
    """
    # Dimensiunea pachetului pentru acest UE
    size = packet_size_bits[ue_id] if isinstance(packet_size_bits, dict) else packet_size_bits

    buf = deque()
    t = 0.0
    # Generează inter-arrival times expovariate până la timpul de simulare
    while t < sim_time_ms:
        inter_arrival = random.expovariate(rate_lambda)
        t += inter_arrival
        if t < sim_time_ms:
            buf.append({
                'time_ms':   t,
                'ue_id':     ue_id,
                'size_bits': size
            })
    return buf


# ────────────────────────────────────────────────────────────
#     CLASA TRAFFICMANAGER: GESTIONEAZĂ BUFFER-ELE CU PACHETE
# ────────────────────────────────────────────────────────────

class TrafficManager:
    def __init__(self, n_ues: int, traffic_type: str, params: dict):
        """
        Initializează managerul de trafic:
          - n_ues: număr de UE-uri
          - traffic_type: 'periodic' sau 'aperiodic'
          - params: dicționar cu toți parametrii simulatorului (period_ms, lambda_per_ms etc.)
        """
        # Creează câte un buffer vid pentru fiecare UE
        self.buffers = {ue: deque() for ue in range(n_ues)}
        self.traffic_type = traffic_type
        self.params = params
        # Înregistrează slotul de sosire al fiecărui pachet (opțional)
        self.arrival_slots = {}

    def initialize(self):
        """
        Populează buffer-ele pentru fiecare UE conform modelului ales:
          - periodic: generează cu generate_periodic()
          - aperiodic: generează cu generate_aperiodic()
        Parametrii period_ms, lambda_per_ms și procentele de variație
        se iau din self.params sau default_params.
        """
        n_ues       = len(self.buffers)
        base_period = self.params.get('period_ms', default_params['period_ms'])
        spread_p    = self.params.get('period_spread_pct', default_params['period_spread_pct'])
        base_lambda = self.params.get('lambda_per_ms', default_params['lambda_per_ms'])
        spread_l    = self.params.get('lambda_spread_pct', default_params['lambda_spread_pct'])
        sim_time    = self.params.get('sim_time_ms', default_params['sim_time_ms'])
        packet_size = self.params.get('packet_size_bits', default_params['packet_size_bits'])

        for ue in range(n_ues):
            if self.traffic_type == 'periodic':
                # Aplică o variație procentuală pe perioada de generare
                if spread_p > 0.0:
                    factor = random.uniform(1.0 - spread_p, 1.0 + spread_p)
                    ue_period = base_period * factor
                else:
                    ue_period = base_period
                # Generează și stochează traficul periodic
                self.buffers[ue] = generate_periodic(
                    ue, ue_period,
                    packet_size,
                    sim_time
                )
            else:
                # Aplică o variație procentuală pe rata Poisson
                if spread_l > 0.0:
                    factor = random.uniform(1.0 - spread_l, 1.0 + spread_l)
                    ue_lambda = base_lambda * factor
                else:
                    ue_lambda = base_lambda
                # Generează și stochează traficul aperiodic
                self.buffers[ue] = generate_aperiodic(
                    ue, ue_lambda,
                    packet_size,
                    sim_time
                )

    def get_ready_ues(self, current_time_ms: float) -> list[int]:
        """
        Returnează lista UE-urilor care au cel puțin un pachet gata de transmis
        (primul pachet în buffer are time_ms ≤ current_time_ms).
        """
        return [
            ue for ue, buf in self.buffers.items()
            if buf and buf[0]['time_ms'] <= current_time_ms
        ]

    def pop_packet(self, ue: int, arrival_slot: int = None) -> dict | None:
        """
        Extrage primul pachet din buffer-ul UE-ului:
          - dacă arrival_slot este specificat, îl înregistrează în self.arrival_slots
        Returnează dict-ul pachet sau None dacă buffer-ul este gol.
        """
        if not self.buffers[ue]:
            return None
        ev = self.buffers[ue].popleft()
        if arrival_slot is not None:
            self.arrival_slots[ue] = arrival_slot
        return ev

    def has_packets(self) -> bool:
        """
        Returnează True dacă există pachete rămase în vreun buffer.
        """
        return any(self.buffers[ue] for ue in self.buffers)
