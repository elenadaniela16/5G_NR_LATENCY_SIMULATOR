import math
import random
from simulator.config import default_params

# Deviază canalul radio: pierdere de cale, shadowing și fading
SIGMA_SHADOW_DB = 8.0  # deviație standard pentru slow-fading (shadowing) în dB

def compute_pathloss(d_m, fc_ghz=3.5, model='log_distance'):
    """
    Calculează pathloss în dB pe baza modelului log-distance:
    - d0_km: referință la 10 m
    - n: exponent de atenuare (3.5)
    - fc_ghz: frecvența portante în GHz
    Folosim formula: PL0 + 10⋅n⋅log10(d/d0)
    """
    d0_km = 0.01            # distanța de referință în km (10 m)
    n = 3.5                 # exponentul de atenuare al canalului
    # transformăm distanța în km și evităm valori < d0
    d_km = max(d_m / 1000.0, d0_km)
    # calculăm PL la distanța de referință
    pl0 = 20*math.log10(d0_km) + 20*math.log10(fc_ghz) + 32.44
    # adăugăm termenul dependent de d
    return pl0 + 10*n*math.log10(d_km / d0_km)


def compute_shadowing():
    """
    Simulează fading lent (shadowing) ca un random gaussian în dB,
    deviația standard fiind SIGMA_SHADOW_DB.
    """
    return random.gauss(0.0, SIGMA_SHADOW_DB)


def compute_rayleigh_fading_db():
    """
    Simulează fading rapid (Rayleigh) generând un exponetial variate și transformând
    în dB. Se adaugă o mică constantă ca să evităm log10(0).
    """
    fading_linear = random.expovariate(1.0)
    return 10 * math.log10(fading_linear + 1e-12)


def compute_sinr(d_m, n_prbs, bw_mhz, scs_khz, model='log_distance'):
    """
    Calculează SINR-ul linie de bază:
    1) Pathloss + shadow + fast-fading în dB
    2) Putere Tx pe PRB (p_tx_dbm - 10*log10(n_prbs))
    3) Prag de zgomot: density + 10*log10(BW) + noise figure
    4) SINR_dB = P_tx_PRB - PL_total - noise_floor
    5) Returnăm SINR liniar (10^(dB/10)).
    """
    cfg = default_params

    # 1) Calculăm pierderile și fading-urile
    pl_db = compute_pathloss(d_m, model=model) \
            + compute_shadowing() \
            + compute_rayleigh_fading_db()

    # 2) Puterea transmisă per PRB (dBm)
    p_tx_dbm = cfg['tx_power_dbm']
    if n_prbs > 0:
        p_prb_dbm = p_tx_dbm - 10 * math.log10(n_prbs)
    else:
        p_prb_dbm = -math.inf  # fără resurse

    # 3) Calculăm noise floor (dBm): densitate + 10log BW + noise figure
    noise_density_dbm_hz = cfg['noise_density_dbm_hz']
    noise_figure_db     = cfg['noise_figure_db']
    bw_hz = n_prbs * 12 * (scs_khz * 1e3)
    if bw_hz > 0:
        noise_floor_dbm = noise_density_dbm_hz + 10 * math.log10(bw_hz) + noise_figure_db
    else:
        noise_floor_dbm = -math.inf

    # 4) SINR în dB și conversie la scala liniară
    sinr_db = p_prb_dbm - pl_db - noise_floor_dbm
    return 10 ** (sinr_db / 10.0)


def sinr_to_cqi(sinr_db):
    """
    Mapează SINR în dB la CQI (0–15) prin pași de 5 dB.
    Dacă SINR nu e un număr finit, returnăm CQI=0 (cel mai prost canal).
    """
    # evităm NaN și infinite
    if not isinstance(sinr_db, (int, float)) or not math.isfinite(sinr_db):
        return 0

    # Fiecare increment de 5 dB corespunde unui pas de CQI
    cqi = int(math.floor(sinr_db / 5.0))
    if cqi < 0:
        return 0
    if cqi > 15:
        return 15
    return cqi
