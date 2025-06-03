# simulator/link_adaptation.py

from dataclasses import dataclass
import math

from simulator.config import MCS_TABLE

@dataclass
class MCSParams:
    index:      int
    Qm:         int
    code_rate:  float

def load_mcs_table() -> dict:
    """
    Încarcă tabelul MCS (CQI -> (Qm, code_rate)) din config.
    """
    return MCS_TABLE

def select_mcs(cqi: int) -> MCSParams:
    """
    Alege parametrul MCS corespunzător valorii de CQI.
    Dacă CQI-ul nu este exact în tabel, se face clamp la limite.
    """
    keys = sorted(MCS_TABLE.keys())
    if cqi < keys[0]:
        cqi = keys[0]
    elif cqi > keys[-1]:
        cqi = keys[-1]
    Qm, code_rate = MCS_TABLE[cqi]
    return MCSParams(index=cqi, Qm=Qm, code_rate=code_rate)

def get_tbs_bits(mcs_idx: int, n_prbs: int, num_symbols: int) -> int:
    """
    Calculează transport block size (TBS) aproximativ, în funcție de:
      - mcs_idx: indicele MCS (care ne indică Qm și code_rate)
      - n_prbs: numărul de PRB-uri alocate
      - num_symbols: câte simboluri fizice sunt transmise (e.g. 14 pentru un full-slot, sau 2/4/7 pentru un mini-slot)
    Formula aproximativă:
        TBS ≈ Qm * code_rate * num_subcarriers_total * num_symbols
    unde num_subcarriers_total = n_prbs * 12 (12 subcarriers per PRB).
    Returnează un întreg (rotunjit în jos).
    """
    # Extragem parametrii MCS
    Qm, code_rate = MCS_TABLE.get(mcs_idx, (0, 0.0))
    # Numărul de subcarriers totale
    num_subcarriers = n_prbs * 12
    # Calcul brut de biți
    raw_bits = Qm * code_rate * num_subcarriers * num_symbols
    # Rotunjim în jos la cel mai apropiat întreg
    return int(math.floor(raw_bits))

def estimate_bler(sinr_db: float, mcs_idx: int) -> float:
    """
    Estimează BLER (Block Error Rate) aproximativ pentru un anumit SINR și MCS.
    Model simplificat: BLER scade exponențial cu SINR - SNR_ref, unde SNR_ref corespunde
    unei valori de BLER 0.5 (pe baza CQI-ului). În lipsa unui model detaliat, folosim:
        BLER ≈ exp( -α * (sinr_db - snr_ref) )
    α este o constantă de decădere (alegem α = 0.5 pentru o variație rezonabilă).
    snr_ref îl determinăm astfel încât sinr_db = SNR_ref => BLER ≈ 0.5.
    Având în vedere că CQI-ul reflectă intervalul de SINR, alegem snr_ref = 5 * mcs_idx.
    """
    # Pentru MCS foarte mic (mcs_idx = 0), considerăm un SNR_ref minim
    snr_ref = 5 * mcs_idx
    alpha = 0.5
    exponent = -alpha * (sinr_db - snr_ref)
    bler = math.exp(exponent)

    # Clamp între 0 și 1
    if bler < 0.0:
        bler = 0.0
    elif bler > 1.0:
        bler = 1.0
    return bler
