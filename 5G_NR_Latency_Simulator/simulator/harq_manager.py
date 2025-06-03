# simulator/harq_manager.py

import random

from simulator.config import HARQ_MAX_ROUNDS, HARQ_RTT_SLOTS
from simulator.link_adaptation import estimate_bler, select_mcs, get_tbs_bits
from simulator.channel import sinr_to_cqi, compute_sinr


class HarqProcess:
    """
    Reține starea unei transmisiuni HARQ active pentru un singur pachet (UE).
    - ue_id: id-ul UE-ului
    - round_idx: 0, 1, 2, ... până la HARQ_MAX_ROUNDS-1
    - due_slot: slotul la care trebuie să procesăm feedback-ul
    - n_prbs: câte PRB-uri au fost alocate la ultima rundă
    - mcs_idx: indicele MCS folosit ultima oară
    - tbs_bits: câți biți conținea TBS-ul transmis ultima oară
    - start_slot: slotul primei transmiteri (= runda 0)
    """
    def __init__(self, ue_id, start_slot, n_prbs, mcs_idx, tbs_bits):
        self.ue_id = ue_id
        self.round_idx = 0
        self.n_prbs = n_prbs
        self.mcs_idx = mcs_idx
        self.tbs_bits = tbs_bits
        self.start_slot = start_slot
        self.due_slot = start_slot + HARQ_RTT_SLOTS

    def advance_round(self, current_slot, ue_distance, bw_mhz, scs_khz):
        """
        Se apelează când feedback-ul a fost NACK și mai sunt runde disponibile.
        Recalculează MCS, TBS și setează due_slot pentru următorul RTT.
        Returnează True dacă s-a programat o nouă rundă, False dacă s-au epuizat runde.
        """
        if self.round_idx + 1 >= HARQ_MAX_ROUNDS:
            return False

        # Incrementăm runda
        self.round_idx += 1

        # Recalculăm SINR și CQI la momentul retransmiterii
        sinr_db = compute_sinr(
            ue_distance,
            self.n_prbs,
            bw_mhz,
            scs_khz,
            model='log_distance'
        )
        cqi = sinr_to_cqi(sinr_db)
        new_mcs = select_mcs(cqi).index

        # Presupunem 14 simboluri per slot (dacă folosești full-slot)
        num_symbols = 14
        new_tbs = get_tbs_bits(new_mcs, self.n_prbs, num_symbols)

        self.mcs_idx = new_mcs
        self.tbs_bits = new_tbs

        # Programăm următorul feedback (slot + HARQ_RTT_SLOTS)
        self.due_slot = current_slot + HARQ_RTT_SLOTS
        return True

    def compute_latency_dict(self, ue_distance):
        """
        Când pachetul este ACK-ed, calculăm latența totală:
         - t_queue = 0 (pentru simplificare)
         - t_transmission = (ack_slot - start_slot + 1) * slot_duration
         - t_harq = round_idx * (HARQ_RTT_SLOTS * slot_duration)
         - t_propagation = ue_distance / c
         - t_total = total
        Returnează un dict cu sub-latențele și totalul.
        """
        slot_duration_ms = 1.0  # µ=0 => 1 ms; altfel: 1.0/(2**µ)
        ack_slot = self.due_slot

        t_queue = 0.0
        t_transmission = (ack_slot - self.start_slot + 1) * slot_duration_ms
        t_harq = self.round_idx * (HARQ_RTT_SLOTS * slot_duration_ms)
        t_propagation = (ue_distance / 3e8) * 1000  # în ms

        t_total = t_queue + t_transmission + t_harq + t_propagation
        return {
            "t_queue_ms": t_queue,
            "t_transmission_ms": t_transmission,
            "t_harq_ms": t_harq,
            "t_propagation_ms": t_propagation,
            "t_total_ms": t_total
        }


class HarqManager:
    def __init__(self, n_ues):
        # Un singur HarqProcess activ per UE (simplificare: un pachet per UE).
        self.active = {}         # dict: ue_id -> HarqProcess
        self.n_ues = n_ues
        self.latency_records = []  # Lista de dict-uri cu statistici HARQ

    def start_harq_tx(self, ue_id, slot, n_prbs, mcs_idx, tbs_bits):
        """
        Inițiază prima transmisiune HARQ pentru pachetul UE-ului dat,
        doar dacă UE-ul nu are deja un proces HARQ activ.
        Returnează True dacă s-a pornit cu succes, False dacă UE-ul are deja HARQ în curs.
        """
        if ue_id in self.active:
            return False

        proc = HarqProcess(ue_id, slot, n_prbs, mcs_idx, tbs_bits)
        self.active[ue_id] = proc
        return True

    def check_feedback(self, slot_idx, ue_distances, bw_mhz, scs_khz, buffers):
        """
        La începutul fiecărui slot, verificăm dacă vreun proces HARQ
        așteaptă feedback la `slot_idx`. Dacă da, calculăm BLER și decidem ACK/NACK.
        - ue_distances: dict[ue_id] -> distanță (m)
        - buffers: dict[ue_id] -> deque de pachete (pentru a elimina pachetul la ACK)
        """
        to_remove = []

        for ue_id, proc in list(self.active.items()):
            if proc.due_slot != slot_idx:
                continue

            d_m = ue_distances[ue_id]
            sinr_db = compute_sinr(d_m, proc.n_prbs, bw_mhz, scs_khz, model='log_distance')
            bler = estimate_bler(sinr_db, proc.mcs_idx)

            if random.random() > bler:
                # ACK: calculăm latența și îl scoatem din coadă, doar dacă există element
                lat_dict = proc.compute_latency_dict(d_m)
                self.latency_records.append({
                    "ue_id": ue_id,
                    "start_slot": proc.start_slot,
                    "ack_slot": slot_idx,
                    **lat_dict
                })
                if buffers.get(ue_id) and len(buffers[ue_id]) > 0:
                    buffers[ue_id].popleft()
                to_remove.append(ue_id)
            else:
                # NACK: dacă mai sunt runde HARQ disponibile, programăm retrimiterea
                can_retx = proc.advance_round(slot_idx, d_m, bw_mhz, scs_khz)
                if not can_retx:
                    # Nu mai există runde → drop
                    lat_dict = proc.compute_latency_dict(d_m)
                    lat_dict["dropped"] = True
                    self.latency_records.append({
                        "ue_id": ue_id,
                        "start_slot": proc.start_slot,
                        "ack_slot": slot_idx,
                        **lat_dict
                    })
                    if buffers.get(ue_id) and len(buffers[ue_id]) > 0:
                        buffers[ue_id].popleft()
                    to_remove.append(ue_id)

        # Ștergem procesele finalizate (ACK sau drop)
        for ue_id in to_remove:
            self.active.pop(ue_id, None)

    def has_pending(self) -> bool:
        """
        Returnează True dacă mai există procese HARQ active (așteaptă feedback sau retransmit).
        """
        return len(self.active) > 0

    def get_latency_stats(self):
        """
        La sfârșitul simulării, poți apela asta pentru a obține lista completă de latențe HARQ.
        """
        return self.latency_records
