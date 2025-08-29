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

# Funcția de extragere a parametrilor cadrului (slot complet sau mini-slot)
def get_frame_params(scs_mu: int, mini_symbols: list = None) -> FrameParams:
    # 1) Alegerea sub-carrier spacing (SCS) pe baza indexului numerologiei
    scs_khz = NUMEROLOGIES[scs_mu]
    # 2) Durata simbolului în microsecunde (1 secunda / (SCS * 1000))
    symbol_duration_us = 1e6 / (scs_khz * 1e3)
    # 3) Durata unui slot complet (14 simboluri × durata simbol)
    slot_duration_us = 14 * symbol_duration_us

    # 4) Dacă nu s-au furnizat mini-symbols, preluăm valorile implicite din config
    from simulator.config import default_params
    if mini_symbols is None:
        mini_symbols = default_params['mini_symbols']

    # 5) Calculăm durata fiecărui mini-slot (număr de simboluri × durata simbol)
    mini_slot_durations_us = [
        Nsymb * symbol_duration_us
        for Nsymb in mini_symbols
    ]

    # 6) Returnăm un dataclass cu toți parametrii calculați
    return FrameParams(
        scs_khz=scs_khz,                            # sub-carrier spacing utilizat
        symbol_duration_us=symbol_duration_us,      # durata unui simbol
        slot_duration_us=slot_duration_us,          # durata slotului complet
        num_symbols_per_slot=14,                    # simboluri per slot (fix 14)
        mini_symbols=mini_symbols,                  # lista de mini-slot lengths
        mini_slot_durations_us=mini_slot_durations_us  # duratele mini-sloturilor
    )
