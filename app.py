import os
import sys
from flask import Flask, render_template, request
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Permitem import-uri din pachetul simulator
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)
sys.path.append(os.path.join(project_root, "simulator"))

from simulator.simulator import run_scenario, SimulationResult
from simulator.simulator_slice import run_scenario_slice, SliceSimulationResult

# Inițializare aplicație Flask și director pentru imagini
app = Flask(__name__)
images_dir = os.path.join(app.static_folder, "images")
os.makedirs(images_dir, exist_ok=True)


@app.route("/", methods=["GET", "POST"])
def index():
    error = None

    if request.method == "POST":
        # --- 1) Citire parametri comuni din formular ---
        scs_mu   = int(request.form["scs_mu"])
        bw       = float(request.form["bandwidth_mhz"])
        n_ues    = int(request.form["n_ues"])
        sim_time = float(request.form["sim_time_ms"])
        traffic  = request.form["traffic_type"]
        pkt_bits = int(request.form["packet_size_bits"])
        slot_type= request.form["slot_type"]
        coding   = float(request.form["coding_time_us"])
        decoding = float(request.form["decoding_time_us"])
        fb_delay = float(request.form["feedback_delay_us"])
        retx_dur = float(request.form["retransmission_duration_us"])
        mode     = request.form["scheduler_mode"]

        # Construim parametrii de bază
        base_params = {
            "scs_mu": scs_mu,
            "bandwidth_mhz": bw,
            "n_ues": n_ues,
            "sim_time_ms": sim_time,
            "traffic_type": traffic,
            "packet_size_bits": pkt_bits,
            "slot_type": slot_type,
            "coding_time_us": coding,
            "decoding_time_us": decoding,
            "feedback_delay_us": fb_delay,
            "retransmission_duration_us": retx_dur,
        }
        if slot_type == "mini":
            base_params["mini_symbols"] = [int(request.form["mini_symbols"])]

        # --- 2) Simulare clasică (fără slicing) ---
        if mode != "slice":
            sim_params: dict = {**base_params, "scheduler_mode": mode}
            res: SimulationResult = run_scenario(sim_params)

            # 2a) Statistici sumare: min/mean/max
            df = pd.DataFrame(res.latencies, columns=["latency_ms"])
            stats = (df.describe()
                       .loc[["min","mean","max"]]
                       .round(2)
                       .reset_index()
                       .rename(columns={"index":"stat"}))
            stats_html = stats.to_html(classes="table table-sm", index=False)

            # 2b) Rate de retransmisie
            total    = len(res.latencies)
            first_ok = sum(res.first_tx)
            retrans  = total - first_ok
            summary = {
                "total": total,
                "first": first_ok,
                "first_pct": round(first_ok/total*100,1) if total else 0.0,
                "retrans": retrans,
                "retrans_pct": round(retrans/total*100,1) if total else 0.0,
            }

            # 2c) Generare grafice și salvare
            # (păstrăm restul grafurilor existente...)
            plt.figure()
            plt.hist(res.latencies, bins=20, edgecolor="black")
            plt.title("Histogramă latență")
            plt.xlabel("ms"); plt.ylabel("count"); plt.tight_layout()
            plt.savefig(os.path.join(images_dir, "histogram.png")); plt.close()

            plt.figure(figsize=(6,4))
            plt.scatter(res.slot_indices, res.latencies, alpha=0.6)
            plt.title("Latență în funcție de sloturi")
            plt.xlabel("Slot index"); plt.ylabel("latență (ms)"); plt.tight_layout()
            plt.savefig(os.path.join(images_dir, "scatter.png")); plt.close()

            xs = np.sort(res.latencies)
            ys = np.arange(1, len(xs)+1)/len(xs)
            plt.figure(figsize=(6,4))
            plt.plot(xs, ys)
            plt.title("CDF latență")
            plt.xlabel("ms"); plt.ylabel("P(X ≤ x)"); plt.tight_layout()
            plt.savefig(os.path.join(images_dir, "cdf.png")); plt.close()

            dist = [d["distance_m"] for d in res.delivered_logs]
            plt.figure(figsize=(6,4))
            plt.scatter(dist, res.latencies, alpha=0.6)
            plt.title("Latență vs Distanță")
            plt.xlabel("m"); plt.ylabel("lat. ms"); plt.tight_layout()
            plt.savefig(os.path.join(images_dir, "lat_vs_dist.png")); plt.close()

            cqi = [d["cqi"] for d in res.delivered_logs]
            plt.figure(figsize=(6,4))
            plt.hist(cqi, bins=range(0,17), edgecolor="black", align="left")
            plt.title("Distribuție CQI")
            plt.xlabel("CQI"); plt.ylabel("count"); plt.tight_layout()
            plt.savefig(os.path.join(images_dir, "cqi_dist.png")); plt.close()

            max_slot = max(res.slot_indices) + 1
            prb_mat = np.zeros((len(res.ue_ids), max_slot))
            for uid, slot, rec in zip(res.ue_ids, res.slot_indices, res.delivered_logs):
                prb_mat[uid, slot] = rec["n_prbs"]
            plt.figure(figsize=(6,4))
            plt.imshow(prb_mat, aspect='auto', origin='lower')
            plt.colorbar(label="PRB alocate")
            plt.title("Heatmap PRB-uri")
            plt.xlabel("Slot"); plt.ylabel("UE ID"); plt.tight_layout()
            plt.savefig(os.path.join(images_dir, "prb_heatmap.png")); plt.close()

            # ——————— Evoluție distanță per UE ———————
            # presupunem că run_scenario a populat res.distance_log cu câte un rând
            # pentru fiecare slot (sau mini-slot) ca {'ue': ue, 'slot': slot, 'distance_m': dist}

            dist_df = pd.DataFrame(res.distance_log)

            # determinăm un pas de marcare la fiecare 10% din numărul total de puncte
            mark_step = max(1, len(dist_df) // 10)

            plt.figure(figsize=(10, 5))
            for ue in sorted(dist_df['ue'].unique()):
                sub = dist_df[dist_df['ue'] == ue]
                x = sub['slot'].values
                y = sub['distance_m'].values

                # linie continuă, cu un marker la fiecare al n-lea punct
                plt.plot(x, y,
                         linewidth=2,
                         label=f"UE{ue}",
                         markevery=mark_step,
                         marker='o', markersize=5)

                # etichetăm punctele cheie: început, mijloc, sfârșit
                mid_idx = len(x) // 2
                for idx in [0, mid_idx, -1]:
                    plt.text(x[idx], y[idx],
                             f"{y[idx]:.1f}",
                             fontsize=8,
                             va='bottom', ha='right')

            plt.xlabel("Slot index")
            plt.ylabel("Distanță [m]")
            plt.title("Evoluție distanță per UE")
            plt.grid(True, linestyle='--', alpha=0.4)
            plt.legend(bbox_to_anchor=(1.02, 1), loc='upper left', fontsize="small")
            plt.tight_layout()
            plt.savefig(os.path.join(images_dir, "distance_evolution.png"))
            plt.close()

            # Tabele latență și detalii
            lat_df = pd.DataFrame({
                "# Pachet": list(range(1, total+1)),
                "Latență [ms]": [round(x,3) for x in res.latencies]
            })
            lat_table = lat_df.to_html(classes="table table-sm", index=False)

            det_df = pd.DataFrame(res.delivered_logs).rename(columns={
                "ue":"UE","slot":"Slot","latency_ms":"Latență (ms)",
                "distance_m":"Distanță (m)","pathloss_db":"Pierdere cale (dB)",
                "sinr_db":"SINR (dB)","cqi":"CQI","mcs_idx":"MCS",
                "Qm":"Qm","code_rate":"Rată Cod","n_prbs":"PRB",
                "tbs_teoretic":"TBS teoretic","tbs_bits":"TBS (biți)",
                "first_tx":"1a TX?"
            })
            det_table = det_df.to_html(classes="table table-sm", index=False)

            # Returnăm pagina cu rezultate
            return render_template(
                "results.html",
                summary                = summary,
                stats_table            = stats_html,
                hist_image             = "images/histogram.png",
                scatter_image          = "images/scatter.png",
                cdf_image              = "images/cdf.png",
                latdist_image          = "images/lat_vs_dist.png",
                cqi_image              = "images/cqi_dist.png",
                heatmap_image          = "images/prb_heatmap.png",
                distance_evol_image    = "images/distance_evolution.png",
                lat_table              = lat_table,
                det_table              = det_table
            )



    # GET: afișăm pagina principală
    return render_template("index.html", error=error)


if __name__ == "__main__":
    app.run(debug=True)
