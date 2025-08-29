# simulator/scheduler.py

from simulator.config          import default_params, slice_profiles
from simulator.channel         import compute_sinr, sinr_to_cqi
from simulator.link_adaptation import select_mcs

def _allocate_classic(buffers, ue_distances, total_prbs, frame_params, mode):
    """
    Funcție internă de alocare „clasică”:
      - mode == 'dynamic'         => alocare adaptivă bazată pe performanța canalului
      - mode == 'semi-persistent' => alocare egală și stabilă între UE-uri
    """
    bw_mhz  = default_params['bandwidth_mhz']
    scs_khz = frame_params.scs_khz

    # Lista UE-urilor care au pachete în buffer
    backlogged = [ue for ue, buf in buffers.items() if buf]
    N = len(backlogged)
    # Inițializăm alocarea cu 0 pentru toți UE-ii
    allocation = {ue: 0 for ue in buffers}
    if N == 0:
        return allocation  # nimeni de deservit

    if mode == 'semi-persistent':
        # Împărțire egală a PRB-urilor între toți UE-ii
        share = total_prbs // N
        for ue in backlogged:
            allocation[ue] = share
        # Redistribuim restul PRB-urilor, câte unul per UE, până se termină
        remainder = total_prbs - share * N
        for ue in backlogged[:remainder]:
            allocation[ue] += 1
        return allocation

    # --- mod dynamic ---
    # Calculăm un „metric” invers proporțional cu eficiența spectrală
    metrics = {}
    total_metric = 0.0
    eps = 1e-6
    for ue in backlogged:
        # Estimăm SINR și îl convertim în CQI → MCS → spectral efficiency
        sinr_db = compute_sinr(
            ue_distances[ue],
            total_prbs,
            bw_mhz,
            scs_khz,
            model='log_distance'
        )
        cqi     = sinr_to_cqi(sinr_db)
        mcs     = select_mcs(cqi)
        se      = mcs.Qm * mcs.code_rate
        # Metric invers proporțional cu se (vrem să favorizăm UE cu se mic)
        metric  = 1.0 / (se + eps)
        metrics[ue] = metric
        total_metric += metric

    used = 0
    if total_metric > 0:
        # Alocăm PRB-uri proporțional cu metric / total_metric
        for ue, metric in metrics.items():
            n_rb = int((metric / total_metric) * total_prbs)
            allocation[ue] = n_rb
            used += n_rb

        # Redistribuim restul PRB-urilor UE-urilor cu cei mai mari metric
        remainder = total_prbs - used
        for ue in sorted(backlogged, key=lambda u: metrics[u], reverse=True)[:remainder]:
            allocation[ue] += 1

    return allocation


def allocate_rb(buffers, ue_distances, total_prbs, frame_params, mode='dynamic'):
    """
    Scheduler principal:
      - dacă mode în {'dynamic','semi-persistent'} folosește _allocate_classic
      - dacă mode == 'slice'       → alocare per slice (network slicing)
    """
    if mode != 'slice':
        # mod clasic fără slicing
        return _allocate_classic(buffers, ue_distances, total_prbs, frame_params, mode)

    # --- Mod network slicing ---
    ue_slice_map = default_params['ue_slice_mapping']
    slice_shares = default_params['slice_prb_shares']
    profiles     = slice_profiles

    # 1) Calculăm exact câte PRB-uri primesc fiecare slice (float)
    exact      = {sl: total_prbs * share for sl, share in slice_shares.items()}
    # 2) Rotunjim în jos și păstrăm partea fracționară
    base_alloc = {sl: int(exact[sl]) for sl in exact}
    frac       = {sl: exact[sl] - base_alloc[sl] for sl in exact}

    # 3) Distribuim PRB-urile rămase către slice-urile cu cea mai mare fracțiune
    used      = sum(base_alloc.values())
    remainder = total_prbs - used
    for sl in sorted(frac, key=lambda s: frac[s], reverse=True)[:remainder]:
        base_alloc[sl] += 1

    # 4) Pentru fiecare slice, apelăm _allocate_classic pe sub-setul său de UE-uri
    allocation = {ue: 0 for ue in buffers}
    for sl, prbs_for_slice in base_alloc.items():
        # extragem UE-urile active în acest slice
        ues_in_slice = [
            ue for ue in buffers
            if ue_slice_map.get(ue) == sl and buffers[ue]
        ]
        if not ues_in_slice:
            continue

        # Construim dicționarele reduse pentru buffer și distanțe
        sub_bufs  = {ue: buffers[ue]       for ue in ues_in_slice}
        sub_dists = {ue: ue_distances[ue] for ue in ues_in_slice}

        # Preluăm politica slice-ului (dynamic/semi-persistent)
        policy   = profiles.get(sl, {})
        sub_mode = policy.get('scheduler_mode', 'dynamic')

        # Alocăm în interiorul slice-ului
        sub_alloc = _allocate_classic(
            sub_bufs,
            sub_dists,
            prbs_for_slice,
            frame_params,
            sub_mode
        )

        # Combinăm cu alocarea globală
        for ue, val in sub_alloc.items():
            allocation[ue] = val

    return allocation
