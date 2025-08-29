import random
from simulator.config import HARQ_MAX_ROUNDS, HARQ_RTT_SLOTS
from simulator.link_adaptation import estimate_bler, select_mcs
from simulator.channel import sinr_to_cqi, compute_sinr
from simulator.rb import compute_tbs

# Clasa care reprezintă un singur proces HARQ pentru un UE
class HarqProcess:

    def __init__(self, ue_id, start_slot, n_prbs, mcs_idx, tbs_bits, arrival_time_ms):
        # Identificator UE și slot inițial de trimitere
        self.ue_id = ue_id
        self.round_idx = 0             # numărul iterărilor HARQ deja efectuate
        self.n_prbs = n_prbs           # resursele alocate inițial (PRB-uri)
        self.mcs_idx = mcs_idx         # indicele MCS folosit prima dată
        self.tbs_bits = tbs_bits       # numărul de biți trimiși prima dată
        self.start_slot = start_slot   # slot-ul inițial de transmitere
        self.arrival_time_ms = arrival_time_ms  # momentul sosirii în ms
        # următorul slot când așteptăm feedback (RTT HARQ)
        self.due_slot = start_slot + HARQ_RTT_SLOTS

    def advance_round(self, current_slot, ue_distance, bw_mhz, scs_khz):
        """
        Încercare nouă de retransmisie:
        - Incrementăm numărul de rundă
        - Recalculăm SINR, CQI, MCS și TBS pentru a doua transmisie
        - Setăm noul slot de feedback (current + RTT)
        """
        # Dacă am atins numărul maxim de runde, nu mai retry-uim
        if self.round_idx + 1 >= HARQ_MAX_ROUNDS:
            return False

        # Avansăm o rundă HARQ
        self.round_idx += 1
        # 1) Recalcul SINR pentru aceleași resurse PRB
        sinr_db = compute_sinr(
            ue_distance, self.n_prbs, bw_mhz, scs_khz,
            model='log_distance'
        )
        # 2) Mapăm în CQI și alegem noul MCS
        cqi = sinr_to_cqi(sinr_db)
        new_mcs = select_mcs(cqi).index
        # 3) Calculăm noul TBS pe 14 simboluri de slot
        num_symbols = 14
        mcs_params = select_mcs(new_mcs)
        new_tbs = compute_tbs(self.n_prbs, mcs_params, num_symbols)
        # 4) Actualizăm parametrii procesului
        self.mcs_idx = new_mcs
        self.tbs_bits = new_tbs
        self.due_slot = current_slot + HARQ_RTT_SLOTS
        return True

    def compute_latency_dict(self, ue_distance, slot_duration_ms):
        """
        Calculează componentele latenței pentru procesul curent:
        - t_queue: timp așteptare în coadă (nu modelăm efectiv aici)
        - t_transmission: numărul de sloturi * durata fiecărui slot
        - t_harq: timp suplimentar din retransmiteri HARQ
        - t_propagation: întârziere de propagare mărgină
        - t_total: sumă
        """
        ack_slot = self.due_slot
        t_queue = 0.0
        t_transmission = (ack_slot - self.start_slot + 1) * slot_duration_ms
        t_harq = self.round_idx * (HARQ_RTT_SLOTS * slot_duration_ms)
        t_propagation = (ue_distance / 3e8) * 1000.0  # în ms
        t_total = t_queue + t_transmission + t_harq + t_propagation
        return {
            "t_queue_ms": t_queue,
            "t_transmission_ms": t_transmission,
            "t_harq_ms": t_harq,
            "t_propagation_ms": t_propagation,
            "t_total_ms": t_total
        }

# Clasa care gestionează toate procesele HARQ active
class HarqManager:

    def __init__(self, n_ues, symbol_duration_ms, num_symbols_per_tx, full_slot_ms):
        self.active = {}  # dict ue_id -> HarqProcess activ
        self.n_ues = n_ues
        self.symbol_duration_ms = symbol_duration_ms
        self.num_symbols_per_tx = num_symbols_per_tx
        self.full_slot_ms = full_slot_ms
        self.latency_records = []  # lista dict-urilor cu statistici de latență

    def start_harq_tx(self, ue_id, slot, n_prbs, mcs_idx, tbs_bits, arrival_time_ms):
        """
        Inițiază primul proces HARQ pentru un UE dacă nu există deja unul activ.
        """
        if ue_id in self.active:
            return False
        proc = HarqProcess(ue_id, slot, n_prbs, mcs_idx, tbs_bits, arrival_time_ms)
        self.active[ue_id] = proc
        return True

    def check_feedback(self, slot_idx, ue_distances, bw_mhz, scs_khz, buffers, arrival_times):
        """
        La fiecare slot complet, verificăm feedback-ul pentru toate procesele care așteaptă:
        - Calculăm BLER actual și generăm un rand() pentru ACK/NACK
        - Dacă ACK: logăm latența și ștergem pachet din buffer
        - Dacă NACK și mai putem retry: advance_round()
        - Dacă NACK și am atins max rounds: drop + log
        """
        to_remove = []
        for ue_id, proc in list(self.active.items()):
            # sărim până când ajungem la slot-ul când trebuie feedback
            if proc.due_slot != slot_idx:
                continue
            # 1) Calcul SINR real și BLER pentru această rundă
            d_m = ue_distances[ue_id]
            sinr_db = compute_sinr(d_m, proc.n_prbs, bw_mhz, scs_khz, model='log_distance')
            bler = estimate_bler(sinr_db, proc.mcs_idx)
            rnd = random.random()
           # print(f"[HARQ DEBUG] UE{ue_id} slot={slot_idx} rnd={rnd:.3f} BLER={bler:.3f}")
            # 2) Decizie ACK/NACK
            if rnd > bler:
            #    print(f"[HARQ DEBUG]   → UE{ue_id} ACK at slot {slot_idx}")
                lat_dict = proc.compute_latency_dict(d_m, self.full_slot_ms)
                # Logăm record-ul de latență (fără câmp dropped)
                self.latency_records.append({
                    "ue_id": ue_id,
                    "start_slot": proc.start_slot,
                    "ack_slot": slot_idx,
                    "arrival_time_ms": arrival_times.get(ue_id, 0.0),
                    **lat_dict
                })
                # Scoatem pachetul din buffer dacă există
                if buffers.get(ue_id) and buffers[ue_id]:
                    buffers[ue_id].popleft()
                to_remove.append(ue_id)
            else:
                # 3) NACK: încercăm retransmisie sau drop dacă s-au epuizat runde HARQ
                can_retx = proc.advance_round(slot_idx, d_m, bw_mhz, scs_khz)
                if not can_retx:
                  #  print(f"[HARQ DEBUG]   → UE{ue_id} NACK, max rounds reached – dropping")
                    lat_dict = proc.compute_latency_dict(d_m, self.full_slot_ms)
                    lat_dict["dropped"] = True
                    self.latency_records.append({
                        "ue_id": ue_id,
                        "start_slot": proc.start_slot,
                        "ack_slot": slot_idx,
                        "arrival_time_ms": arrival_times.get(ue_id, 0.0),
                        **lat_dict
                    })
                    if buffers.get(ue_id) and buffers[ue_id]:
                        buffers[ue_id].popleft()
                    to_remove.append(ue_id)
        # 4) Eliminăm procesele terminate din lista activă
        for ue_id in to_remove:
            self.active.pop(ue_id, None)

    def has_pending(self) -> bool:
        # Returnează True dacă mai există procese HARQ active
        return len(self.active) > 0

    def get_latency_stats(self):
        # Returnează lista completă de înregistrări latență (ACK/NACK/drop)
        return self.latency_records
