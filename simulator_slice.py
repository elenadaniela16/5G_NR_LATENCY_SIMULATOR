from dataclasses import dataclass
from simulator.simulator import run_scenario, SimulationResult
from simulator.config import default_params, slice_profiles

@dataclass
class SliceMetrics:
    avg_latency_ms: float          # Latența medie (ms) pentru slice
    delivered_packets: int         # Numărul de pachete livrate cu succes în slice

@dataclass
class SliceSimulationResult:
    base: SimulationResult         # Rezultatul simulării clasice (fără slicing)
    per_slice: dict[str, SliceMetrics]  # Metrici agregate per slice

def run_scenario_slice(params: dict) -> SliceSimulationResult:
    """
    Rulează simularea 5G NR cu network slicing.
    Input în `params`:
      - 'ue_slice_mapping': dict[int, str]     # mapare UE -> denumire slice
      - 'slice_prb_shares': dict[str, float]   # share de PRB per slice (ex: {'eMBB':60, 'URLLC':20, 'mMTC':20})
    Poate conține și ceilalți parametri obișnuiți pentru run_scenario.
    """
    # 1) Extragem și eliminăm din params informațiile despre slicing
    ue_slice_mapping = params.pop('ue_slice_mapping')
    raw_shares       = params.pop('slice_prb_shares')

    # 1b) Normalizăm share-urile astfel încât să însumeze 1.0
    total = sum(raw_shares.values()) or 1.0
    slice_prb_shares = {sl: share / total for sl, share in raw_shares.items()}

    # 2) Injectăm mapările și share-urile normalizate în default_params,
    # ca scheduler-ul să le găsească la runtime
    default_params['ue_slice_mapping'] = ue_slice_mapping
    default_params['slice_prb_shares'] = slice_prb_shares

    # 2b) Overridem dimensiunea pachetelor per UE conform configurației slice-urilor
    # folosind câmpul 'packet_size_bits' din slice_profiles
    params['packet_size_bits'] = {
        ue: slice_profiles[sl]['packet_size_bits']
        for ue, sl in ue_slice_mapping.items()
    }

    # 3) Forțăm modul de scheduling pe 'slice'
    params['scheduler_mode'] = 'slice'

    # 4) Apelăm funcția de simulare existentă cu noii parametri
    sim_res: SimulationResult = run_scenario(params)

    # 5) Agregăm listele de latențe per slice, pe baza log-urilor de livrare
    per_slice_data: dict[str, list[float]] = {}
    for log in sim_res.delivered_logs:
        sl = ue_slice_mapping[log['ue']]
        per_slice_data.setdefault(sl, []).append(log['latency_ms'])

    # 6) Calculăm metricile (medie latență și număr livrări) pentru fiecare slice
    per_slice_metrics: dict[str, SliceMetrics] = {}
    for sl, lat_list in per_slice_data.items():
        count = len(lat_list)
        avg   = sum(lat_list) / count if count else 0.0
        per_slice_metrics[sl] = SliceMetrics(
            avg_latency_ms=avg,
            delivered_packets=count
        )

    # 7) Returnăm rezultatul complet: simularea de bază + metricile per slice
    return SliceSimulationResult(base=sim_res, per_slice=per_slice_metrics)
