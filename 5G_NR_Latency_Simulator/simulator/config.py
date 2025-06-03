# Numerologii: μ → Δf în kHz
NUMEROLOGIES = {
    0: 15,
    1: 30,
    2: 60,
    3: 120,
}

# Tabel oficial 3GPP TS 38.101-1: (BW_MHz, Δf_kHz) → număr PRB
PRB_TABLE = {
    (5,   15): 25,    (10,  15): 52,    (15,  15): 79,    (20,  15): 106,
    (10,  30): 24,    (20,  30): 51,    (40,  30): 106,
    (20,  60): 24,    (40,  60): 51,    (80,  60): 106,
    (10, 120): 6,
}

# MCS table: CQI index → (Qm, code_rate)
# Values from 3GPP TS 38.214 Table 5.1.3-1 (example subset)
MCS_TABLE = {
    0:  (2,  0.12),
    1:  (2,  0.19),
    2:  (2,  0.25),
    3:  (2,  0.37),
    4:  (4,  0.60),
    5:  (4,  0.88),
    6:  (6,  0.36),
    7:  (6,  0.48),
    8:  (6,  0.60),
    9:  (6,  0.74),
    10: (6,  0.88),
    11: (8,  0.37),
    12: (8,  0.48),
    13: (8,  0.60),
    14: (8,  0.74),
    15: (8,  0.93),
}

# Parametri default de simulare
default_params = {
    'scs_mu':           1,         # μ = 1 → 30 kHz
    'bandwidth_mhz':    10,        # MHz
    'n_ues':            10,
    'sim_time_ms':      1000.0,
    'traffic_type':     'periodic',
    'period_ms':        10.0,
    'packet_size_bits': 1200,
    'scheduler_mode':   'dynamic',   # 'dynamic' or 'semi'
    'slot_type':        'full',      # 'full' or 'mini'
    'mini_symbols':     [2, 4, 7],   # opțiuni mini-slot
    'tx_power_dbm':     0,
    'noise_figure_db':  7,
    'noise_density_dbm_hz': -174,
}
# HARQ
HARQ_MAX_ROUNDS = 4
HARQ_RTT_SLOTS = 4

