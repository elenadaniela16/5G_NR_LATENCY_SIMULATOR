# simulator/simulator.py

from dataclasses import dataclass
import random

from simulator.config           import default_params, PRB_TABLE
from simulator.frames           import get_frame_params
from simulator.traffic          import TrafficManager
from simulator.scheduler        import allocate_rb
from simulator.harq_manager     import HarqManager
from simulator.link_adaptation  import select_mcs
from simulator.rb               import compute_tbs
from simulator.channel          import compute_pathloss, compute_sinr, sinr_to_cqi


@dataclass
class SimulationResult:
    latencies:    list    # ms
    ue_ids:       list
    slot_indices: list
    first_tx:     list    # bool
    delivered_logs: list   # detalii pe pachet


def run_scenario(params: dict = None) -> SimulationResult:
    cfg = default_params.copy()
    if params:
        cfg.update(params)

    fp = get_frame_params(cfg['scs_mu'], cfg.get('mini_symbols'))
    bw_mhz = cfg['bandwidth_mhz']
    scs_khz = fp.scs_khz

    total_prbs = PRB_TABLE.get(
        (bw_mhz, scs_khz),
        int((bw_mhz * 1e6) / (scs_khz * 1e3 * 12))
    )

    # Inițializăm managerul de trafic și-l populăm la start
    tm = TrafficManager(cfg['n_ues'], cfg['traffic_type'], cfg)
    tm.initialize()

    # Inițializăm HARQ
    hm = HarqManager(cfg['n_ues'])

    cell_r = cfg.get('cell_radius', 250)
    ue_dist = {ue: random.uniform(10, cell_r) for ue in range(cfg['n_ues'])}

    latencies, ue_ids, slots, first_tx = [], [], [], []
    delivered_logs = []

    if cfg['slot_type'] == 'mini':
        durations_us = fp.mini_slot_durations_us
        num_sym = cfg['mini_symbols'][0]
    else:
        durations_us = [fp.slot_duration_us]
        num_sym = fp.num_symbols_per_slot

    total_slots = int((cfg['sim_time_ms'] * 1000) / fp.slot_duration_us)

    for slot in range(total_slots):
        for dur_us in durations_us:
            now_ms = (slot * fp.slot_duration_us + dur_us) / 1000.0

            # Alocăm PRB-uri fără să apelăm vreun generate_traffic()
            alloc = allocate_rb(tm.buffers, ue_dist, total_prbs, fp, cfg['scheduler_mode'])

            for ue, n_prbs in alloc.items():
                if n_prbs > 0 and tm.buffers[ue] and tm.buffers[ue][0]['time_ms'] <= now_ms:
                    ev = tm.pop_packet(ue)
                    if 'remaining_bits' not in ev:
                        ev['remaining_bits'] = ev['size_bits']
                        ev['attempt'] = 0
                    ev['attempt'] += 1

                    pl = compute_pathloss(ue_dist[ue])
                    sinr = compute_sinr(
                        ue_dist[ue],
                        n_prbs,
                        bw_mhz,
                        scs_khz,
                        model='log_distance'
                    )
                    cqi = sinr_to_cqi(sinr)
                    mcs = select_mcs(cqi)
                    tbs = compute_tbs(n_prbs, mcs, num_sym)

                    ev['remaining_bits'] -= tbs

                    if ev['remaining_bits'] <= 0:
                        lat = now_ms - ev['time_ms']
                        latencies.append(lat)
                        ue_ids.append(ue)
                        slots.append(slot)
                        first = (ev['attempt'] == 1)
                        first_tx.append(first)

                        delivered_logs.append({
                            'ue': ue,
                            'slot': slot,
                            'latency_ms': round(lat, 3),
                            'distance_m': round(ue_dist[ue], 2),
                            'pathloss_db': round(pl, 2),
                            'sinr_db': round(sinr, 2),
                            'cqi': cqi,
                            'mcs_idx': mcs.index,
                            'Qm': mcs.Qm,
                            'code_rate': mcs.code_rate,
                            'n_prbs': n_prbs,
                            'tbs_bits': tbs,
                            'first_tx': first
                        })
                    else:
                        tm.buffers[ue].appendleft(ev)
                        hm.start_harq_tx(ue, slot, n_prbs, mcs.index, tbs)

            # Verificăm feedback-ul HARQ (fără arrival_slots)
            hm.check_feedback(
                slot_idx=slot,
                ue_distances=ue_dist,
                bw_mhz=bw_mhz,
                scs_khz=scs_khz,
                buffers=tm.buffers
            )

            if not tm.has_packets() and not hm.has_pending():
                break

        if not tm.has_packets() and not hm.has_pending():
            break

    return SimulationResult(latencies, ue_ids, slots, first_tx, delivered_logs)
