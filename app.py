import os
import sys
from flask import Flask, render_template, request, redirect, url_for
import pandas as pd
import matplotlib.pyplot as plt

project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)
sys.path.append(os.path.join(project_root, "simulator"))

from simulator.simulator import run_scenario

app = Flask(__name__)

images_dir = os.path.join(app.static_folder, "images")
os.makedirs(images_dir, exist_ok=True)


@app.route("/", methods=["GET", "POST"])
def index():

    if request.method == "POST":
        try:
            scs_mu = int(request.form.get("scs_mu", 1))
            bandwidth_mhz = float(request.form.get("bandwidth_mhz", 10.0))
            n_ues = int(request.form.get("n_ues", 10))
            sim_time_ms = float(request.form.get("sim_time_ms", 1000.0))
            traffic_type = request.form.get("traffic_type", "periodic")
            period_ms = float(request.form.get("period_ms", 10.0))
            packet_size_bits = int(request.form.get("packet_size_bits", 512))
            scheduler_mode = request.form.get("scheduler_mode", "dynamic")
            slot_type = request.form.get("slot_type", "full")
            coding_time_us = float(request.form.get("coding_time_us", 100.0))
            decoding_time_us = float(request.form.get("decoding_time_us", 200.0))
            feedback_delay_us = float(request.form.get("feedback_delay_us", 1000.0))
            retransmission_duration_us = float(request.form.get("retransmission_duration_us", 2000.0))

            mini_symbols = None
            if slot_type == "mini":
                mini_sym = int(request.form.get("mini_symbols", 4))
                mini_symbols = [mini_sym]
        except ValueError:
            return render_template("index.html", error="Parametri invalizi. Verifică valorile introduse.")

        sim_params = {
            "scs_mu": scs_mu,
            "bandwidth_mhz": bandwidth_mhz,
            "n_ues": n_ues,
            "sim_time_ms": sim_time_ms,
            "traffic_type": traffic_type,
            "packet_size_bits": packet_size_bits,
            "scheduler_mode": scheduler_mode,
            "slot_type": slot_type,
            "coding_time_us": coding_time_us,
            "decoding_time_us": decoding_time_us,
            "feedback_delay_us": feedback_delay_us,
            "retransmission_duration_us": retransmission_duration_us,
        }
        if mini_symbols is not None:
            sim_params["mini_symbols"] = mini_symbols

        return redirect(url_for("results", **sim_params))

    return render_template("index.html")


@app.route("/results")
def results():

    try:
        scs_mu = int(request.args.get("scs_mu", 1))
        bandwidth_mhz = float(request.args.get("bandwidth_mhz", 10.0))
        n_ues = int(request.args.get("n_ues", 10))
        sim_time_ms = float(request.args.get("sim_time_ms", 1000.0))
        traffic_type = request.args.get("traffic_type", "periodic")
        packet_size_bits = int(request.args.get("packet_size_bits", 512))
        scheduler_mode = request.args.get("scheduler_mode", "dynamic")
        slot_type = request.args.get("slot_type", "full")
        coding_time_us = float(request.args.get("coding_time_us", 100.0))
        decoding_time_us = float(request.args.get("decoding_time_us", 200.0))
        feedback_delay_us = float(request.args.get("feedback_delay_us", 1000.0))
        retransmission_duration_us = float(request.args.get("retransmission_duration_us", 2000.0))

        mini_symbols = None
        if slot_type == "mini":
            mini_sym = int(request.args.get("mini_symbols", 4))
            mini_symbols = [mini_sym]
    except ValueError:
        return render_template("index.html", error="Parametri invalizi la /results. Reîncearcă.")

    sim_params = {
        "scs_mu": scs_mu,
        "bandwidth_mhz": bandwidth_mhz,
        "n_ues": n_ues,
        "sim_time_ms": sim_time_ms,
        "traffic_type": traffic_type,
        "packet_size_bits": packet_size_bits,
        "scheduler_mode": scheduler_mode,
        "slot_type": slot_type,
        "coding_time_us": coding_time_us,
        "decoding_time_us": decoding_time_us,
        "feedback_delay_us": feedback_delay_us,
        "retransmission_duration_us": retransmission_duration_us,
    }
    if mini_symbols is not None:
        sim_params["mini_symbols"] = mini_symbols

    result = run_scenario(sim_params)


    total_model_lat = result.latencies

    total_pkts = len(result.latencies)
    first_count = sum(1 for f in result.first_tx if f)
    retrans_count = total_pkts - first_count
    first_pct = (first_count / total_pkts * 100.0) if total_pkts > 0 else 0.0
    retrans_pct = (retrans_count / total_pkts * 100.0) if total_pkts > 0 else 0.0

    summary = {
        "total": total_pkts,
        "first": first_count,
        "first_pct": first_pct,
        "retrans": retrans_count,
        "retrans_pct": retrans_pct
    }

    if total_pkts > 0:
        df_stats = pd.DataFrame(result.latencies, columns=["latență_ms"])
        descr = df_stats.describe().round(3).reset_index().rename(columns={"index": "statistică"})
        stats_table = descr.to_html(classes="table table-sm table-striped", index=False, justify="center")
    else:
        stats_table = pd.DataFrame(
            {"statistică": [], "latență_ms": []}
        ).to_html(classes="table table-sm table-striped", index=False, justify="center")

    if total_pkts > 0:
        plt.figure(figsize=(6, 4))
        plt.hist(result.latencies, bins=20, color="#007bff", edgecolor="black")
        plt.xlabel("Latență [ms]")
        plt.ylabel("Număr pachete")
        plt.title("Histogramă Latență")
        plt.tight_layout()
        hist_path = os.path.join(images_dir, "histogram.png")
        plt.savefig(hist_path, dpi=150)
        plt.close()

        plt.figure(figsize=(6, 4))
        plt.scatter(result.slot_indices, result.latencies, alpha=0.6, s=20, color="#28a745")
        plt.xlabel("Slot index")
        plt.ylabel("Latență [ms]")
        plt.title("Latență în Funcție de Sloturi")
        plt.tight_layout()
        scatter_path = os.path.join(images_dir, "scatter.png")
        plt.savefig(scatter_path, dpi=150)
        plt.close()
    else:
        open(os.path.join(images_dir, "histogram.png"), "wb").close()
        open(os.path.join(images_dir, "scatter.png"), "wb").close()


    logs = result.delivered_logs

    return render_template(
        "results.html",
        summary=summary,
        stats_table=stats_table,
        total_model_lat=total_model_lat,
        logs=logs
    )


if __name__ == "__main__":
    app.run(debug=True)
