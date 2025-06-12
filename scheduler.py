from simulator.config         import default_params
from simulator.channel        import compute_sinr, sinr_to_cqi
from simulator.link_adaptation import select_mcs

def allocate_rb(buffers, ue_distances, total_prbs, frame_params, mode='dynamic'):

    bw_mhz  = default_params['bandwidth_mhz']
    scs_khz = frame_params.scs_khz
    backlogged = [ue for ue, buf in buffers.items() if buf]
    N = len(backlogged)

    allocation = {ue: 0 for ue in buffers}

    if N == 0:
        return allocation

    if mode == 'semi-persistent':
        share = total_prbs // N
        for ue in backlogged:
            allocation[ue] = share
        remainder = total_prbs - share * N
        for ue in backlogged[:remainder]:
            allocation[ue] += 1

        return allocation

    metrics = {}
    total_metric = 0.0
    eps = 1e-6
    for ue in backlogged:
        sinr_db = compute_sinr(
            ue_distances[ue],
            total_prbs,
            bw_mhz,
            scs_khz,
            model='log_distance'
        )
        cqi = sinr_to_cqi(sinr_db)
        mcs = select_mcs(cqi)
        se = mcs.Qm*mcs.code_rate
        metric = 1/(se+eps)
        metrics[ue] = metric
        total_metric += metric

    if total_metric > 0:
        used = 0
        for ue, metric in metrics.items():
            n_rb = int((metric / total_metric) * total_prbs)
            allocation[ue] = n_rb
            used += n_rb
        remainder = total_prbs - used
        sorted_ues = sorted(backlogged, key=lambda ue: metrics[ue], reverse=True)
        idx = 0
        while remainder > 0 and idx < len(sorted_ues):
            allocation[sorted_ues[idx]] += 1
            remainder -= 1
            idx += 1

    return allocation
