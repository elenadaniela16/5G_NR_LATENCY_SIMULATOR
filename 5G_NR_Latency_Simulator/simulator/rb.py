from simulator.link_adaptation import MCSParams

def n_subcarriers_per_rb() -> int:
    return 12

def compute_tbs(n_prbs: int, mcs: MCSParams,num_symbols: int) -> int:
    """
    Calculează Transport Block Size (TBS) în biți pentru un TTI
    (slot full sau mini-slot cu num_symbols simboluri).
    - rezervăm 1 simbol pentru PDCCH
    - RE_data = n_prbs * 12 * (num_symbols - 1)
    - TBS = floor(RE_data * Qm * code_rate / 8) * 8
    """
    data_symbols = max(num_symbols - 1, 0)
    res_elements = n_prbs * n_subcarriers_per_rb() * data_symbols
    raw_bits = res_elements * mcs.Qm * mcs.code_rate
    tbs_bits = int((raw_bits // 8) * 8)
    return tbs_bits
