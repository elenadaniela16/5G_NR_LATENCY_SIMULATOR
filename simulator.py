from dataclasses import dataclass
import random
import math

# Importăm funcțiile de adaptare a legăturii și de estimare BLER
from simulator.link_adaptation import select_mcs, MCSParams, estimate_bler
# Importăm funcțiile pentru calculul caracteristicilor canalului
from simulator.channel import compute_pathloss, compute_sinr, sinr_to_cqi
# Obținem parametrii cadrului (slot/full sau mini-slot)
from simulator.frames import get_frame_params
# Scheduler-ul care decide distribuția PRB-urilor între UE
from simulator.scheduler import allocate_rb
# Managerul traficului (buffer-urile cu pachete) pentru UE-uri
from simulator.traffic import TrafficManager
# Calculul Transport Block Size pentru fiecare alocare
from simulator.rb import compute_tbs
# Managerul HARQ (retransmisii și statistică)
from simulator.harq_manager import HarqManager
# Parametri impliciți și tabelul de PRB-uri per configurare BW/SCS
from simulator.config import default_params, PRB_TABLE


# ────────────────────────────────────────────────────────────
#    FUNCȚII DE CALCUL AL COMPONENTELOR DE LATENȚĂ
# ────────────────────────────────────────────────────────────

def access_delay_sr(sr_rounds: int, slot_duration_us: float) -> float:
    # Întârzierea din faza de Scheduling Request (număr de runde SR × durata slotului)
    return (sr_rounds * slot_duration_us) / 1000.0  # convertim µs → ms

def scheduling_delay(k_slots: int, slot_duration_us: float, algo_factor: float = 1.0) -> float:
    # Întârzierea provocată de așteptarea alocării (k sloturi × durată ± factor algoritm)
    return (k_slots * slot_duration_us * algo_factor) / 1000.0

def transmission_delay_bits(packet_size_bits: int, spectral_efficiency: float, bandwidth_hz: float) -> float:
    # Timpul de transmitere efectivă în ms
    if spectral_efficiency * bandwidth_hz <= 0:
        return float("inf")  # dacă nu există resurse, latență infinite
    t_tx_s = packet_size_bits / (spectral_efficiency * bandwidth_hz)  # în secunde
    return t_tx_s * 1000.0  # convertim în ms

def processing_delay_coding_decoding(coding_time_us: float, decoding_time_us: float) -> float:
    # Sumă timpi codare + decodare (în µs → ms)
    return (coding_time_us + decoding_time_us) / 1000.0

def harq_delay(num_retx: int, feedback_delay_us: float, retransmission_duration_us: float) -> float:
    # Calcul întârziere HARQ: fiecare retransmisie înseamnă feedback + durată retransmisie
    if num_retx <= 0:
        return 0.0
    total_us = num_retx * (feedback_delay_us + retransmission_duration_us)
    return total_us / 1000.0

def propagation_delay(distance_m: float) -> float:
    # Întârzierea de propagare (distanță / viteză luminii în ms)
    c = 3e8  # viteză lumină în m/s
    t_prop_s = distance_m / c
    return t_prop_s * 1000.0

def total_latency(params: dict) -> float:
    # Reunim toate componentele de latență într-un singur valoare totală (ms)
    T_access = access_delay_sr(params.get("sr_rounds", 0), params["slot_duration_us"])
    T_sched  = scheduling_delay(params.get("k_slots",   0), params["slot_duration_us"], params.get("algo_factor", 1.0))
    T_tx     = transmission_delay_bits(params["packet_size_bits"], params["spectral_efficiency"], params["bandwidth_hz"])
    T_proc   = processing_delay_coding_decoding(params.get("coding_time_us", 0.0), params.get("decoding_time_us", 0.0))
    T_harq   = harq_delay(params.get("num_retx", 0), params.get("feedback_delay_us", 0.0), params.get("retransmission_duration_us", 0.0))
    T_prop   = propagation_delay(params.get("distance_m", 0.0))
    return T_access + T_sched + T_tx + T_proc + T_harq + T_prop


# ────────────────────────────────────────────────────────────
#    DATACLASS PENTRU REZULTATELE SIMULĂRII
# ────────────────────────────────────────────────────────────

@dataclass
class SimulationResult:
    # Colectăm toate valorile esențiale: latențe, UE-uri, slot-uri, flag first_tx, logs detaliate, statistici HARQ
    latencies:      list
    ue_ids:         list
    slot_indices:   list
    first_tx:       list
    delivered_logs: list
    harq_stats:     list
    distance_log: list


# ────────────────────────────────────────────────────────────
#    MOBILITATEA UE-URILOR
# ────────────────────────────────────────────────────────────

def init_positions(n_ues: int, R: float) -> dict:
    # Generăm poziții uniforme pe aria cercului de rază R
    pos = {}
    for ue in range(n_ues):
        r = R * math.sqrt(random.random())  # distribuție uniformă în suprafață
        theta = random.random() * 2 * math.pi
        pos[ue] = [r * math.cos(theta), r * math.sin(theta)]
    return pos

def init_speeds(n_ues: int) -> dict:
    # Definim viteze: 70% pietoni (0.5–1.5 m/s), 30% vehicule (10–15 m/s)
    speeds = {}
    for ue in range(n_ues):
        if random.random() < 0.7:
            speeds[ue] = random.uniform(0.5, 1.5)
        else:
            speeds[ue] = random.uniform(10.0, 15.0)
    return speeds

def init_headings(n_ues: int) -> dict:
    # Direcții random [0, 2π) pentru fiecare UE
    return { ue: random.random() * 2 * math.pi for ue in range(n_ues) }


# ────────────────────────────────────────────────────────────
#    FUNCȚIA PRINCIPALĂ DE SIMULARE
# ────────────────────────────────────────────────────────────

def run_scenario(params: dict = None) -> SimulationResult:
    # 1) Citim configurarea de bază și suprascriem cu parametrii primiți
    cfg = default_params.copy()
    if params:
        cfg.update(params)

    # 2) Extragem parametrii fading (shadowing, fast fading)
    sigma_shadow_db   = cfg.get("shadow_sigma_db", default_params.get("shadow_sigma_db", 8.0))
    apply_fast_fading = cfg.get("fast_fading",     default_params.get("fast_fading", True))

    # 3) Parametri cadrului (slot / mini-slot) și număr total de PRB-uri disponibile
    fp       = get_frame_params(cfg["scs_mu"], cfg.get("mini_symbols"))
    bw_mhz   = cfg["bandwidth_mhz"]
    scs_khz  = fp.scs_khz
    total_prbs = PRB_TABLE.get((bw_mhz, scs_khz), int((bw_mhz * 1e6) / (scs_khz * 1e3 * 12)))

    # 4) Inițializăm managerii de trafic și HARQ
    tm = TrafficManager(cfg["n_ues"], cfg["traffic_type"], cfg)
    tm.initialize()  # populăm buffer-ele cu pachete
    symbol_duration_ms = fp.symbol_duration_us / 1000.0
    num_symbols       = fp.num_symbols_per_slot
    full_slot_ms      = fp.slot_duration_us / 1000.0
    hm = HarqManager(cfg["n_ues"], symbol_duration_ms, num_symbols, full_slot_ms)

    # 5) Inițializare mobilitate UE: poziții, viteze, direcții → calcul distanțe
    cell_r   = cfg.get("cell_radius", 500)
    pos      = init_positions(cfg["n_ues"], cell_r)
    print("[DEBUG] Poziții inițiale UE:", pos)
    speeds   = init_speeds(cfg["n_ues"])
    headings = init_headings(cfg["n_ues"])
    ue_dist  = { ue: math.hypot(x, y) for ue, (x, y) in pos.items() }
    print("[DEBUG] Distanțe inițiale UE:", ue_dist)
    # 6) Pregătim structurile pentru rezultate
    latencies, ue_ids, slots, first_tx = [], [], [], []
    delivered_logs, arrival_times = [], {}

    # 7) Alegem durata fiecărui TTI (slot complet sau liste de mini-sloturi)
    if cfg["slot_type"] == "mini":
        durations_us = fp.mini_slot_durations_us
        num_sym      = cfg["mini_symbols"][0]
    else:
        durations_us = [fp.slot_duration_us]
        num_sym      = fp.num_symbols_per_slot
    total_slots = int((cfg["sim_time_ms"] * 1000) / fp.slot_duration_us)
    distance_log = []
    # 8) Bucla principală: pentru fiecare slot și sub-slot (mini)
    for slot in range(total_slots):
        for dur_us in durations_us:
            now_ms = (slot * fp.slot_duration_us + dur_us) / 1000.0

            # 8.1) Scheduler: alocăm PRB-uri pe baza funcției allocate_rb
            alloc = allocate_rb(tm.buffers, ue_dist, total_prbs, fp, cfg["scheduler_mode"])

            # 8.2) Procesăm fiecare UE cu buffer și resurse alocate
            for ue, n_prbs in alloc.items():
                # sărim dacă nu avem PRB sau nu e nimic în buffer sau e prea devreme
                if n_prbs == 0 or not tm.buffers[ue] or tm.buffers[ue][0]["time_ms"] > now_ms:
                    continue

                ev = tm.pop_packet(ue)

                # Inițializare prima dată când ev apare: număr biți, încercări, SR, slots
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

                # Contor încercare + calcul SR și scheduling delay prima dată
                ev["attempt"] += 1
                if not ev["has_been_allocated"]:
                    ev["sr_rounds"] += 1
                    ev["k_slots"]    += 1
                    ev["has_been_allocated"] = True

                # 8.3) Actualizare mobilitate UE în acest mini-slot
                x, y = pos[ue]
                theta = headings[ue]
                delta_s = speeds[ue] * (dur_us / 1e6)
                x_new = x + delta_s * math.cos(theta)
                y_new = y + delta_s * math.sin(theta)
                # dacă iese din celulă, schimbă direcția
                if math.hypot(x_new, y_new) > cell_r:
                    theta = (theta + math.pi) % (2 * math.pi)
                    headings[ue] = theta
                    x_new = x + delta_s * math.cos(theta)
                    y_new = y + delta_s * math.sin(theta)
                pos[ue] = [x_new, y_new]
                print( f"[DEBUG] UE{ue} noua poziție: x={x_new:.2f}, y={y_new:.2f} la slot {slot}")
                ue_dist[ue] = math.hypot(x_new, y_new)
                print(f"[DEBUG] UE{ue} noua distanță: x={ue_dist[ue]:.2f}la slot {slot}")
                distance_log.append({
                    "ue": ue,
                    "slot": slot,
                    "distance_m": round(ue_dist[ue], 2)
                })
                # 8.4) Calcul pierdere de cale și SINR de bază
                pl_db    = compute_pathloss(ue_dist[ue])
                sinr_lin = compute_sinr(ue_dist[ue], n_prbs, bw_mhz, scs_khz, model="log_distance")

                # 8.5) Aplicăm shadowing și fast fading
                shadow_db = random.gauss(0.0, sigma_shadow_db)
                fad_lin   = abs(random.gauss(0.0, 1.0)) if apply_fast_fading else 1.0

                # 8.6) Combinăm în SINR final în dB
                sinr_db       = 10 * math.log10(sinr_lin) - shadow_db
                sinr_with_f   = (10 ** (sinr_db / 10.0)) * fad_lin
                final_sinr_db = 10 * math.log10(sinr_with_f)

                # 8.7) Alegerea MCS pe baza CQI
                cqi = sinr_to_cqi(final_sinr_db)
                mcs: MCSParams = select_mcs(cqi)
                ev["spectral_efficiency"] = mcs.Qm * mcs.code_rate

                # 8.8) Calcul câți biți pot fi trimiși în acest TTI
                tbs_from_table = compute_tbs(n_prbs, mcs, num_sym)
                n_tx_bits      = min(tbs_from_table, ev["remaining_bits"])
                ev["remaining_bits"] -= n_tx_bits

                if ev["remaining_bits"] > 0:
                    #print(f"[DEBUG] UE{ue} HARQ round {ev['attempt']} – rămân {ev['remaining_bits']} biți")
                    # 8.9) Dacă nu încape, inițiem HARQ
                    tm.buffers[ue].appendleft(ev)
                    hm.start_harq_tx(ue, slot, n_prbs, mcs.index, n_tx_bits, arrival_times[ue])
                else:
                    # 8.10) Dacă încape complet, test BLER
                    bler = estimate_bler(final_sinr_db, mcs.index)
                    if random.random() < bler:
                        # NACK → retransmitere HARQ
                        ev["remaining_bits"] = ev["size_bits"]
                        tm.buffers[ue].appendleft(ev)
                        hm.start_harq_tx(ue, slot, n_prbs, mcs.index, n_tx_bits, arrival_times[ue])
                    else:
                        # ACK → calculăm latența totală și logăm
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
                        #print(f"[DEBUG] UE{ue} ACK slot={slot}, latență totală={latency:.3f}ms")
                        # stocăm rezultatele
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

            # 8.11) La sfârșitul fiecărui slot complet, procesăm feedback HARQ
            hm.check_feedback(slot, ue_dist, bw_mhz, scs_khz, tm.buffers, arrival_times)
            # 8.12) Dacă nu mai avem trafic și HARQ în așteptare, ieșim
            if not tm.has_packets() and not hm.has_pending():
                break
        if not tm.has_packets() and not hm.has_pending():
            break

    # primim statistici HARQ (rundă, latențe)
    harq_stats = hm.get_latency_stats()
    # întoarcem toate rezultatele într-un singur obiect
    return SimulationResult(latencies, ue_ids, slots, first_tx, delivered_logs, harq_stats, distance_log )
