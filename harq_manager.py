import random
from simulator.config import HARQ_MAX_ROUNDS, HARQ_RTT_SLOTS
from simulator.link_adaptation import estimate_bler, select_mcs, get_tbs_bits
from simulator.channel import sinr_to_cqi, compute_sinr

class HarqProcess:

    def __init__(self, ue_id, start_slot, n_prbs, mcs_idx, tbs_bits, arrival_time_ms):
        self.ue_id = ue_id
        self.round_idx = 0
        self.n_prbs = n_prbs
        self.mcs_idx = mcs_idx
        self.tbs_bits = tbs_bits
        self.start_slot = start_slot
        self.arrival_time_ms = arrival_time_ms
        self.due_slot = start_slot + HARQ_RTT_SLOTS

    def advance_round(self, current_slot, ue_distance, bw_mhz, scs_khz):

        if self.round_idx + 1 >= HARQ_MAX_ROUNDS:
            return False

        self.round_idx += 1
        sinr_db = compute_sinr(
            ue_distance,
            self.n_prbs,
            bw_mhz,
            scs_khz,
            model='log_distance'
        )
        cqi = sinr_to_cqi(sinr_db)
        new_mcs = select_mcs(cqi).index
        num_symbols = 14
        new_tbs = get_tbs_bits(new_mcs, self.n_prbs, num_symbols)
        self.mcs_idx = new_mcs
        self.tbs_bits = new_tbs
        self.due_slot = current_slot + HARQ_RTT_SLOTS
        return True

    def compute_latency_dict(self, ue_distance, slot_duration_ms):

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

class HarqManager:

    def __init__(self, n_ues, symbol_duration_ms, num_symbols_per_tx, full_slot_ms):
        self.active = {}
        self.n_ues = n_ues
        self.symbol_duration_ms = symbol_duration_ms
        self.num_symbols_per_tx = num_symbols_per_tx
        self.full_slot_ms = full_slot_ms
        self.latency_records = []

    def start_harq_tx(self, ue_id, slot, n_prbs, mcs_idx, tbs_bits, arrival_time_ms):

        if ue_id in self.active:
            return False
        proc = HarqProcess(ue_id, slot, n_prbs, mcs_idx, tbs_bits, arrival_time_ms)
        self.active[ue_id] = proc
        return True

    def check_feedback(self, slot_idx, ue_distances, bw_mhz, scs_khz, buffers, arrival_times):

        to_remove = []

        for ue_id, proc in list(self.active.items()):
            if proc.due_slot != slot_idx:
                continue

            d_m = ue_distances[ue_id]
            sinr_db = compute_sinr(d_m, proc.n_prbs, bw_mhz, scs_khz, model='log_distance')
            bler = estimate_bler(sinr_db, proc.mcs_idx)
            print(f"[HARQ DEBUG] UE{ue_id} slot={slot_idx} round={proc.round_idx + 1} BLER={bler:.3f}")
            if random.random() > bler:
                print(f"[HARQ DEBUG]   → UE{ue_id} ACK at slot {slot_idx}")
                lat_dict = proc.compute_latency_dict(d_m, self.full_slot_ms)

                self.latency_records.append({
                    "ue_id": ue_id,
                    "start_slot": proc.start_slot,
                    "ack_slot": slot_idx,
                    "arrival_time_ms": arrival_times.get(ue_id, 0.0),
                    **lat_dict
                })
                if buffers.get(ue_id) and len(buffers[ue_id]) > 0:
                    buffers[ue_id].popleft()
                to_remove.append(ue_id)
            else:
                can_retx = proc.advance_round(slot_idx, d_m, bw_mhz, scs_khz)
                if not can_retx:
                    print(f"[HARQ DEBUG]   → UE{ue_id} NACK, reached max rounds – dropping packet")
                    lat_dict = proc.compute_latency_dict(d_m, self.full_slot_ms)
                    lat_dict["dropped"] = True
                    self.latency_records.append({
                        "ue_id": ue_id,
                        "start_slot": proc.start_slot,
                        "ack_slot": slot_idx,
                        "arrival_time_ms": arrival_times.get(ue_id, 0.0),
                        **lat_dict
                    })
                    if buffers.get(ue_id) and len(buffers[ue_id]) > 0:
                        buffers[ue_id].popleft()
                    to_remove.append(ue_id)
        for ue_id in to_remove:
            self.active.pop(ue_id, None)

    def has_pending(self) -> bool:

        return len(self.active) > 0

    def get_latency_stats(self):

        return self.latency_records
