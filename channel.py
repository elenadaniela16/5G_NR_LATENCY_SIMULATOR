import math
import random

from simulator.config import default_params

SIGMA_SHADOW_DB = 8.0

def compute_pathloss(d_m, fc_ghz=3.5, model='log_distance'):
    d0_km = 0.01
    n = 3.5
    d_km = max(d_m / 1000.0, d0_km)
    pl0 = 20*math.log10(d0_km) + 20*math.log10(fc_ghz) + 32.44
    return pl0 + 10*n*math.log10(d_km/d0_km)

def compute_shadowing():
    return random.gauss(0.0, SIGMA_SHADOW_DB)

def compute_rayleigh_fading_db():
    fading_linear = random.expovariate(1.0)
    return 10*math.log10(fading_linear + 1e-12)

def compute_sinr(d_m, n_prbs, bw_mhz, scs_khz, model='log_distance'):
    """
    Returns LINEAR SINR.
    """
    cfg = default_params

    # pathloss + shadow + fast fading (all in dB)
    pl_db = compute_pathloss(d_m, model=model) \
            + compute_shadowing() \
            + compute_rayleigh_fading_db()

    # tx power per PRB (dBm)
    p_tx_dbm = cfg['tx_power_dbm']
    if n_prbs > 0:
        p_prb_dbm = p_tx_dbm - 10*math.log10(n_prbs)
    else:
        p_prb_dbm = -math.inf

    # noise floor (dBm)
    noise_density_dbm_hz = cfg['noise_density_dbm_hz']
    noise_figure_db     = cfg['noise_figure_db']
    bw_hz = n_prbs * 12 * (scs_khz*1e3)
    if bw_hz > 0:
        noise_floor_dbm = noise_density_dbm_hz + 10*math.log10(bw_hz) + noise_figure_db
    else:
        noise_floor_dbm = -math.inf

    sinr_db = p_prb_dbm - pl_db - noise_floor_dbm
    return 10**(sinr_db/10.0)

def sinr_to_cqi(sinr_db):
    """
    Map SINR (dB) to a CQI in [0..15]. If SINR isn't a finite number,
    treat it as the worst channel (CQI=0).
    """
    # guard against NaN / infinite
    if not isinstance(sinr_db, (int, float)) or not math.isfinite(sinr_db):
        return 0

    # floor-divide by 5dB per CQI step
    cqi = int(math.floor(sinr_db / 5.0))
    if cqi < 0:
        return 0
    if cqi > 15:
        return 15
    return cqi