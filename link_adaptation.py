from dataclasses import dataclass
import math

from simulator.config import MCS_TABLE

@dataclass
class MCSParams:
    index:      int
    Qm:         int
    code_rate:  float

def load_mcs_table() -> dict:
    return MCS_TABLE

def select_mcs(cqi: int) -> MCSParams:
    keys = sorted(MCS_TABLE.keys())
    if cqi < keys[0]:
        cqi = keys[0]
    elif cqi > keys[-1]:
        cqi = keys[-1]
    Qm, code_rate = MCS_TABLE[cqi]
    return MCSParams(index=cqi, Qm=Qm, code_rate=code_rate)

def get_tbs_bits(mcs_idx: int, n_prbs: int, num_symbols: int) -> int:
    Qm, code_rate = MCS_TABLE.get(mcs_idx, (0, 0.0))
    num_subcarriers = n_prbs * 12
    raw_bits = Qm * code_rate * num_subcarriers * num_symbols
    return int(math.floor(raw_bits))

def estimate_bler(sinr_db: float, mcs_idx: int) -> float:
    snr_ref = 5 * mcs_idx
    alpha = 0.5
    exponent = -alpha * (sinr_db - snr_ref)
    bler = math.exp(exponent)

    if bler < 0.0:
        bler = 0.0
    elif bler > 1.0:
        bler = 1.0
    return bler
