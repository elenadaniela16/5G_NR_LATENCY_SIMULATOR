from simulator.link_adaptation import MCSParams

def n_subcarriers_per_rb() -> int:
    return 12

def compute_tbs(n_prbs: int, mcs: MCSParams,num_symbols: int) -> int:

    data_symbols = max(num_symbols - 1, 0)
    res_elements = n_prbs * n_subcarriers_per_rb() * data_symbols
    raw_bits = res_elements * mcs.Qm * mcs.code_rate
    tbs_bits = int((raw_bits // 8) * 8)
    return tbs_bits
