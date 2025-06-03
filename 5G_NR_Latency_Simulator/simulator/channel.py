# simulator/channel.py

import math
import random

from simulator.config import default_params, NUMEROLOGIES, PRB_TABLE

# Devierea standard pentru shadowing log-normal (în dB)
SIGMA_SHADOW_DB = 8.0

def compute_pathloss(d_m, fc_ghz=3.5, model='log_distance'):
    """
    Calculează path-loss-ul mediu (dB) folosind modelul log-distance:
      PL(d) = PL(d0) + 10·n·log10(d/d0)
    unde:
      d0 = 10 m (0.01 km), n = 3.5 (exemplu urban),
      PL(d0) = 20·log10(d0_km) + 20·log10(fc_ghz) + 32.44 (dB).
    """
    # Parametri de referință
    d0_km = 0.01  # 10 m
    n = 3.5       # exponentul de pierdere (urban)
    # Convertim distanța în km și ne asigurăm că nu e mai mică decât d0
    d_km = max(d_m / 1000.0, d0_km)

    # Pierderea la distanța de referință d0
    pl0 = 20 * math.log10(d0_km) + 20 * math.log10(fc_ghz) + 32.44

    # Modelul log-distance (fără shadowing/fading)
    pl = pl0 + 10 * n * math.log10(d_km / d0_km)
    return pl


def compute_shadowing():
    """
    Returnează offset-ul de shadowing (dB), distribuit log-normal:
      X ∼ N(0, SIGMA_SHADOW_DB^2).
    """
    return random.gauss(0.0, SIGMA_SHADOW_DB)


def compute_rayleigh_fading_db():
    """
    Returnează offset-ul de fading (dB), aproximat prin Rayleigh:
      - Generăm un RV Exponential(1.0) pentru puterea în valoare liniară,
      - Convertim în dB: 10·log10(fading_linear).
    Adăugăm un mic eps pentru a evita log10(0).
    """
    fading_linear = random.expovariate(1.0)  # media = 1
    return 10 * math.log10(fading_linear + 1e-12)


def compute_sinr(d_m, n_prbs, bw_mhz, scs_khz, model='log_distance'):
    """
    Calculează SINR în dB pentru un UE aflat la distanța d_m (metri),
    care transmite pe n_prbs PRB, într-o bandă totală bw_mhz (MHz),
    cu subcarrier spacing scs_khz (kHz), folosind modelul specificat.
    Se include path-loss mediu + shadowing + fading + noise floor.
    """
    cfg = default_params

    # 1) Path-loss mediu (dB)
    pl_med = compute_pathloss(d_m, model=model)

    # 2) Shadowing (log-normal) și small-scale fading (Rayleigh)
    shadow_db = compute_shadowing()
    fading_db = compute_rayleigh_fading_db()

    # Path-loss total (dB)
    pl_total_db = pl_med + shadow_db + fading_db

    # 3) Puterea de transmisie totală (dBm) și puterea pe un singur PRB
    tx_total_dbm = cfg['tx_power_dbm']  # de ex. 23 dBm
    # Dacă n_prbs > 0, împărțim puterea uniform pe PRB-uri:
    if n_prbs > 0:
        p_prb_dbm = tx_total_dbm - 10 * math.log10(n_prbs)
    else:
        # Dacă nu alocăm PRB (n_prbs=0), putem pune p_prb_dbm = −inf
        p_prb_dbm = -math.inf

    # 4) Noise floor (dBm) pe lățimea de bandă alocată (n_prbs·12·scs_khz)
    noise_density_dbm_hz = cfg['noise_density_dbm_hz']  # de ex. -174 dBm/Hz
    noise_figure_db = cfg['noise_figure_db']            # de ex. 7 dB
    # Calculăm BW (Hz) ocupată de n_prbs PRB: n_prbs * 12 * scs_khz*1e3
    bw_hz = n_prbs * 12 * (scs_khz * 1e3)
    if bw_hz > 0:
        noise_floor_dbm = (
            noise_density_dbm_hz
            + 10 * math.log10(bw_hz)
            + noise_figure_db
        )
    else:
        # Dacă nu e bandă ocupată, punem noise_floor = −inf
        noise_floor_dbm = -math.inf

    # 5) SINR (dB) = puterea pe PRB (dBm) − path-loss total (dB) − noise floor (dBm)
    sinr_db = p_prb_dbm - pl_total_db - noise_floor_dbm
    return sinr_db


def sinr_to_cqi(sinr_db):
    """
    Convertim SINR (dB) într-un CQI între 0 și 15,
    cu pași de aproximativ 5 dB între valori:
      CQI = floor(sinr_db / 5), limitat la [0, 15].
    """
    cqi = int(sinr_db // 5)
    if cqi < 0:
        return 0
    if cqi > 15:
        return 15
    return cqi
