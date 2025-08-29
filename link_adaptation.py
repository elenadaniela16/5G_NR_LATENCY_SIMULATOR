from dataclasses import dataclass
import math
from simulator.config import MCS_TABLE

@dataclass
class MCSParams:
    index:      int       # indicele CQI/MCS
    Qm:         int       # numărul de biți per simbol (modulație)
    code_rate:  float     # rata de codare asociată schemei de codare

# Încarcă tabelul MCS din config (dict cqi -> (Qm, code_rate))
def load_mcs_table() -> dict:
    return MCS_TABLE

# Selectează parametrii MCS pe baza valorii CQI primite
def select_mcs(cqi: int) -> MCSParams:
    # Obținem cheile valide și le limităm pe CQI la [min, max]
    keys = sorted(MCS_TABLE.keys())
    if cqi < keys[0]:
        cqi = keys[0]
    elif cqi > keys[-1]:
        cqi = keys[-1]
    # Extragem (Qm, code_rate) din tabel
    Qm, code_rate = MCS_TABLE[cqi]
    return MCSParams(index=cqi, Qm=Qm, code_rate=code_rate)

# Estimează BLER bazat pe SINR și indice MCS
def estimate_bler(sinr_db: float, mcs_idx: int) -> float:
    # Extragem Qm și code_rate (nu folosit direct aici)
    Qm, code_rate = MCS_TABLE.get(mcs_idx, (2, 0.12))

    # Definim un SNR de referință liniar cu indicele MCS
    snr_ref = 5.0 * mcs_idx  # 5 dB per treaptă de CQI

    # α controlează panta tranziției BLER
    alpha = 0.5

    # Model exponential: BLER = exp(-α*(sinr - snr_ref))
    exponent = -alpha * (sinr_db - snr_ref)
    bler = math.exp(exponent)

    # Limităm BLER la intervalul [0,1]
    if bler < 0.0:
        bler = 0.0
    elif bler > 1.0:
        bler = 1.0

    return bler
