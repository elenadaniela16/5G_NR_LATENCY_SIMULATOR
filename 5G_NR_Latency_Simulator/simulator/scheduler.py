from collections import deque
import math

from simulator.config      import default_params
from simulator.channel     import compute_sinr, sinr_to_cqi
from simulator.link_adaptation import select_mcs

def allocate_rb(buffers, ue_distances, total_prbs, frame_params, mode='dynamic'):
    """
    Allocate PRBs per UE according to 'dynamic' or 'semi' scheduler.
    buffers: dict[ue_id] -> deque of packet events
    ue_distances: dict[ue_id] -> distance in meters
    total_prbs: total # of PRBs in cell
    frame_params: FrameParams (has scs_khz)
    mode: 'dynamic' or 'semi'
    """
    bw_mhz   = default_params['bandwidth_mhz']
    scs_khz  = frame_params.scs_khz

    # find backlogged UEs
    backlogged = [ue for ue, buf in buffers.items() if buf]
    N = len(backlogged)
    allocation = {ue: 0 for ue in buffers}

    if N == 0:
        return allocation

    if mode == 'semi':
        # each backlogged UE gets an equal slice
        share = total_prbs // N
        for ue in backlogged:
            allocation[ue] = share
        return allocation

    # dynamic: compute metric = Qm·code_rate for each UE
    metrics = {}
    total_metric = 0.0
    for ue in backlogged:
        # compute SINR with new signature
        sinr_db = compute_sinr(
            ue_distances[ue],
            total_prbs,          # PRB count for CQI estimation
            bw_mhz,
            scs_khz,
            model='long_distance'
        )
        cqi = sinr_to_cqi(sinr_db)
        mcs = select_mcs(cqi)
        metric = mcs.Qm * mcs.code_rate
        metrics[ue] = metric
        total_metric += metric

    # allocate proportionally to metric
    if total_metric > 0:
        for ue, metric in metrics.items():
            allocation[ue] = int((metric / total_metric) * total_prbs)

    return allocation
