from dataclasses import dataclass
from simulator.config import NUMEROLOGIES

@dataclass
class FrameParams:
    scs_khz: int
    symbol_duration_us: float
    slot_duration_us: float
    num_symbols_per_slot: int
    mini_symbols: list
    mini_slot_durations_us: list

def get_frame_params(scs_mu: int, mini_symbols: list = None) -> FrameParams:
    scs_khz = NUMEROLOGIES[scs_mu]
    symbol_duration_us = 1e6 / (scs_khz * 1e3)
    slot_duration_us = 14 * symbol_duration_us

    from simulator.config import default_params
    if mini_symbols is None:
        mini_symbols = default_params['mini_symbols']

    mini_slot_durations_us = [
        Nsymb * symbol_duration_us
        for Nsymb in mini_symbols
    ]

    return FrameParams(
        scs_khz=scs_khz,
        symbol_duration_us=symbol_duration_us,
        slot_duration_us=slot_duration_us,
        num_symbols_per_slot=14,
        mini_symbols=mini_symbols,
        mini_slot_durations_us=mini_slot_durations_us
    )
