from simulator.link_adaptation import MCSParams

# Numărul fix de subcarrier-uri într-un Resource Block (RB)
def n_subcarriers_per_rb() -> int:
    return 12

# Calculul Transport Block Size (TBS) pentru un set de PRB-uri și MCS dat
# - n_prbs: numărul de Resource Blocks alocate
# - mcs: obiect MCSParams conținând Qm și rata de codare
# - num_symbols: numărul de simboluri fizice disponibile per transmisie

def compute_tbs(n_prbs: int, mcs: MCSParams, num_symbols: int) -> int:
    # 1) Excludem simbolul de control (tastariu): folosim doar data symbols
    data_symbols = max(num_symbols - 1, 0)
    # 2) Numărul total de elemente de resursă (subcarriers × simboluri)
    res_elements = n_prbs * n_subcarriers_per_rb() * data_symbols
    # 3) Raw bits = elemente de resursă × modulatie × rata de codare
    raw_bits = res_elements * mcs.Qm * mcs.code_rate
    # 4) Întotdeauna rotunjim în jos la cel mai apropiat octet (8 biți)
    tbs_bits = int((raw_bits // 8) * 8)
    return tbs_bits
