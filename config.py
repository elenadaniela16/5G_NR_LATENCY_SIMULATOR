NUMEROLOGIES = {
    0: 15,
    1: 30,
    2: 60,
    3: 120,
}

PRB_TABLE = {
    (5,   15): 25,
    (10,  15): 52,
    (15,  15): 79,
    (20,  15): 106,
    (10,  30): 24,
    (20,  30): 51,
    (40,  30): 106,
    (20,  60): 24,
    (40,  60): 51,
    (80,  60): 106,
    (10, 120): 6,
}

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

default_params = {
    'scs_mu': 1,
    'bandwidth_mhz': 10,
    'n_ues': 10,
    'sim_time_ms': 1000.0,
    'traffic_type': 'periodic',
    'period_ms': 10.0,
    'period_spread_pct':0.3,
    'lambda_per_ms':0.1,
    'lambda_spread_pct':0.2,
    'packet_size_bits': 512,
    'scheduler_mode': 'dynamic',
    'slot_type': 'full',
    'mini_symbols': [2, 4, 7],
    'coding_time_us': 100.0,
    'decoding_time_us': 200.0,
    'feedback_delay_us': 1000.0,
    'retransmission_duration_us': 2000.0,
    'tx_power_dbm': 0,
    'noise_figure_db': 7,
    'noise_density_dbm_hz': -174,
    "shadow_sigma_db": 8.0,
    "fast_fading":     True,
}

HARQ_MAX_ROUNDS = 4
HARQ_RTT_SLOTS = 4


