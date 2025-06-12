from dataclasses import dataclass
import random
import math

from simulator.link_adaptation import select_mcs, MCSParams, estimate_bler
from simulator.channel import compute_pathloss, compute_sinr, sinr_to_cqi
from simulator.frames import get_frame_params
from simulator.scheduler import allocate_rb
from simulator.traffic import TrafficManager
from simulator.rb import compute_tbs
from simulator.harq_manager import HarqManager
from simulator.config import default_params, PRB_TABLE


#
# ────────────────────────────────────────────────────────────
#           FUNCȚII DE CALCUL AL COMPONENTELOR DE LATENȚĂ
# ────────────────────────────────────────────────────────────
#

def access_delay_sr(sr_rounds: int, slot_duration_us: float) -> float:
    return (sr_rounds * slot_duration_us) / 1000.0

def scheduling_delay(k_slots: int, slot_duration_us: float, algo_factor: float = 1.0) -> float:
    return (k_slots * slot_duration_us * algo_factor) / 1000.0

def transmission_delay_bits(packet_size_bits: int, spectral_efficiency: float, bandwidth_hz: float) -> float:
    if spectral_efficiency * bandwidth_hz <= 0:
        return float("inf")
    t_tx_s = packet_size_bits / (spectral_efficiency * bandwidth_hz)
    return t_tx_s * 1000.0

def processing_delay_coding_decoding(coding_time_us: float, decoding_time_us: float) -> float:
    return (coding_time_us + decoding_time_us) / 1000.0

def harq_delay(num_retx: int, feedback_delay_us: float, retransmission_duration_us: float) -> float:
    if num_retx <= 0:
        return 0.0
    total_us = num_retx * (feedback_delay_us + retransmission_duration_us)
    return total_us / 1000.0

def propagation_delay(distance_m: float) -> float:
    c = 3e8
    t_prop_s = distance_m / c
    return t_prop_s * 1000.0

def total_latency(params: dict) -> float:
    T_access = access_delay_sr(params.get("sr_rounds", 0), params["slot_duration_us"])
    T_sched  = scheduling_delay(params.get("k_slots",   0), params["slot_duration_us"], params.get("algo_factor", 1.0))
    T_tx     = transmission_delay_bits(params["packet_size_bits"], params["spectral_efficiency"], params["bandwidth_hz"])
    T_proc   = processing_delay_coding_decoding(params.get("coding_time_us", 0.0), params.get("decoding_time_us", 0.0))
    T_harq   = harq_delay(params.get("num_retx", 0), params.get("feedback_delay_us", 0.0), params.get("retransmission_duration_us", 0.0))
    T_prop   = propagation_delay(params.get("distance_m", 0.0))
    return T_access + T_sched + T_tx + T_proc + T_harq + T_prop


#
# ────────────────────────────────────────────────────────────
#         DATACLASS PENTRU REZULTATELE SIMULĂRII
# ────────────────────────────────────────────────────────────
#

@dataclass
class SimulationResult:
    latencies:      list
    ue_ids:         list
    slot_indices:   list
    first_tx:       list
    delivered_logs: list
    harq_stats:     list


#
# ────────────────────────────────────────────────────────────
#               FUNCȚIA PRINCIPALĂ DE SIMULARE
# ────────────────────────────────────────────────────────────
#

def run_scenario(params: dict = None) -> SimulationResult:
    # 1) build cfg
    cfg = default_params.copy()
    if params:
        cfg.update(params)

    # fading params
    sigma_shadow_db    = cfg.get("shadow_sigma_db", default_params.get("shadow_sigma_db", 8.0))
    apply_fast_fading  = cfg.get("fast_fading",     default_params.get("fast_fading", True))

    # frame & PRBs
    fp       = get_frame_params(cfg["scs_mu"], cfg.get("mini_symbols"))
    bw_mhz   = cfg["bandwidth_mhz"]
    scs_khz  = fp.scs_khz
    total_prbs = PRB_TABLE.get(
        (bw_mhz, scs_khz),
        int((bw_mhz * 1e6) / (scs_khz * 1e3 * 12))
    )

    # traffic & HARQ
    tm = TrafficManager(cfg["n_ues"], cfg["traffic_type"], cfg)
    tm.initialize()
    symbol_duration_ms = fp.symbol_duration_us / 1000.0
    num_symbols       = fp.num_symbols_per_slot
    full_slot_ms      = fp.slot_duration_us / 1000.0
    hm = HarqManager(cfg["n_ues"], symbol_duration_ms, num_symbols, full_slot_ms)

    # static UE distances
    cell_r = cfg.get("cell_radius", 250)
    ue_dist = {ue: random.uniform(10, cell_r) for ue in range(cfg["n_ues"])}

    # buffers for results
    latencies, ue_ids, slots, first_tx = [], [], [], []
    delivered_logs, arrival_times = [], {}

    # choose TTI durations & symbol count
    if cfg["slot_type"] == "mini":
        durations_us = fp.mini_slot_durations_us
        num_sym      = cfg["mini_symbols"][0]
    else:
        durations_us = [fp.slot_duration_us]
        num_sym      = fp.num_symbols_per_slot

    total_slots = int((cfg["sim_time_ms"] * 1000) / fp.slot_duration_us)

    # main simulation loop
    for slot in range(total_slots):
        for dur_us in durations_us:
            now_ms = (slot * fp.slot_duration_us + dur_us) / 1000.0

            alloc = allocate_rb(tm.buffers, ue_dist, total_prbs, fp, cfg["scheduler_mode"])

            for ue, n_prbs in alloc.items():
                if n_prbs == 0 or not tm.buffers[ue] or tm.buffers[ue][0]["time_ms"] > now_ms:
                    continue

                ev = tm.pop_packet(ue)
                # init per-packet fields
                if "remaining_bits" not in ev:
                    ev.update({
                        "remaining_bits":       ev["size_bits"],
                        "attempt":              0,
                        "sr_rounds":            0,
                        "k_slots":              0,
                        "spectral_efficiency":  0.0,
                        "has_been_allocated":   False
                    })
                    arrival_times[ue] = ev["time_ms"]

                ev["attempt"] += 1
                if not ev["has_been_allocated"]:
                    ev["sr_rounds"] += 1
                    ev["k_slots"]    += 1
                    ev["has_been_allocated"] = True

                # 1) pathloss & baseline SINR (linear)
                pl_db    = compute_pathloss(ue_dist[ue])
                sinr_lin = compute_sinr(ue_dist[ue], n_prbs, bw_mhz, scs_khz, model="log_distance")

                # 2) shadow & fast fading
                shadow_db = random.gauss(0.0, sigma_shadow_db)
                fad_lin   = abs(random.gauss(0.0, 1.0)) if apply_fast_fading else 1.0

                # 3) combine → final SINR (dB)
                sinr_db      = 10 * math.log10(sinr_lin) - shadow_db
                sinr_with_f  = (10 ** (sinr_db / 10.0)) * fad_lin
                final_sinr_db = 10 * math.log10(sinr_with_f)

                # 4) MCS choice
                cqi = sinr_to_cqi(final_sinr_db)
                mcs: MCSParams = select_mcs(cqi)
                ev["spectral_efficiency"] = mcs.Qm * mcs.code_rate

                # 5) how many bits fit
                tbs_from_table = compute_tbs(n_prbs, mcs, num_sym)
                n_tx_bits = min(tbs_from_table, ev["remaining_bits"])
                ev["remaining_bits"] -= n_tx_bits

                if ev["remaining_bits"] > 0:
                    # still incomplete → HARQ
                    tm.buffers[ue].appendleft(ev)
                    hm.start_harq_tx(ue, slot, n_prbs, mcs.index, n_tx_bits, arrival_times[ue])

                else:
                    # packet “fits” → now do BLER check
                    bler = estimate_bler(final_sinr_db, mcs.index)
                    rnd = random.random()
                    print(f"[HARQ DEBUG] UE{ue} slot={slot} rnd={rnd:.3f} BLER={bler:.3f}")
                    if rnd < bler:
                        # decode failure → HARQ
                        print(f"[HARQ DEBUG]   → UE{ue} NACK at slot {slot}")
                        ev["remaining_bits"] = ev["size_bits"]
                        tm.buffers[ue].appendleft(ev)
                        hm.start_harq_tx(ue, slot, n_prbs, mcs.index, n_tx_bits, arrival_times[ue])

                    else:
                        # decode success → record latency inline
                        print(f"[HARQ DEBUG] UE{ue} slot={slot} first‐TX succeeded (BLER={bler:.3f})")
                        params_latency = {
                            "sr_rounds":                 ev.get("sr_rounds", 0),
                            "k_slots":                   ev.get("k_slots",   0),
                            "slot_duration_us":          dur_us,
                            "packet_size_bits":          ev["size_bits"],
                            "spectral_efficiency":       ev["spectral_efficiency"],
                            "bandwidth_hz":              bw_mhz * 1e6,
                            "coding_time_us":            cfg.get("coding_time_us", 0.0),
                            "decoding_time_us":          cfg.get("decoding_time_us", 0.0),
                            "num_retx":                  ev["attempt"] - 1,
                            "feedback_delay_us":         cfg.get("feedback_delay_us", 0.0),
                            "retransmission_duration_us":cfg.get("retransmission_duration_us", 0.0),
                            "distance_m":                ue_dist[ue],
                        }
                        latency = total_latency(params_latency)

                        latencies.append(latency)
                        ue_ids.append(ue)
                        slots.append(slot)
                        first_tx.append(ev["attempt"] == 1)
                        delivered_logs.append({
                            "ue":           ue,
                            "slot":         slot,
                            "latency_ms":   round(latency, 3),
                            "distance_m":   round(ue_dist[ue], 2),
                            "pathloss_db":  round(pl_db, 2),
                            "sinr_db":      round(final_sinr_db, 2),
                            "cqi":          cqi,
                            "mcs_idx":      mcs.index,
                            "Qm":           mcs.Qm,
                            "code_rate":    mcs.code_rate,
                            "n_prbs":       n_prbs,
                            "tbs_teoretic": tbs_from_table,
                            "tbs_bits":     n_tx_bits,
                            "first_tx":     (ev["attempt"] == 1),
                        })

            # end of minislot; HARQ feedback once per full slot
            hm.check_feedback(slot, ue_dist, bw_mhz, scs_khz, tm.buffers, arrival_times)
            if not tm.has_packets() and not hm.has_pending():
                break
        if not tm.has_packets() and not hm.has_pending():
            break

    harq_stats = hm.get_latency_stats()
    return SimulationResult(latencies, ue_ids, slots, first_tx, delivered_logs, harq_stats)
