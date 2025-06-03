import os, sys
from flask import Flask, render_template, request, url_for


project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)
sys.path.append(os.path.join(project_root, 'simulator'))

from simulator.simulator import run_scenario
from simulator.analysis import build_dataframe, compute_statistics,plot_latency_histogram, plot_latency_over_slots

app = Flask(__name__)

# Director pentru grafice
images_dir = os.path.join(app.static_folder, 'images')
os.makedirs(images_dir, exist_ok=True)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Citire parametri formular
        scs_mu           = int(request.form.get('scs_mu', 1))
        bandwidth_mhz    = int(request.form.get('bandwidth_mhz', 10))
        n_ues            = int(request.form.get('n_ues', 10))
        sim_time_ms      = float(request.form.get('sim_time_ms', 1000))
        traffic_type     = request.form.get('traffic_type', 'periodic')
        period_ms        = float(request.form.get('period_ms', 10))
        packet_size_bits = int(request.form.get('packet_size_bits', 1200))
        scheduler_mode   = request.form.get('scheduler_mode', 'dynamic')
        slot_type        = request.form.get('slot_type', 'full')

        params = {
            'scs_mu':           scs_mu,
            'bandwidth_mhz':    bandwidth_mhz,
            'n_ues':            n_ues,
            'sim_time_ms':      sim_time_ms,
            'traffic_type':     traffic_type,
            'period_ms':        period_ms,
            'packet_size_bits': packet_size_bits,
            'scheduler_mode':   scheduler_mode,
            'slot_type':        slot_type
        }

        # Dacă mini-slot, citim și câte simboluri
        if slot_type == 'mini':
            mini_sym = int(request.form.get('mini_symbols', 4))
            params['mini_symbols'] = [mini_sym]

        # Rulăm simularea
        result = run_scenario(params)

        # Agregare și statistici
        df        = build_dataframe(result)
        stats_df  = compute_statistics(df)
        stats_table = stats_df.to_html(classes='table table-sm table-striped', border=0)

        # Histogramă latență
        hist_fig   = plot_latency_histogram(df)
        hist_path  = os.path.join('images', 'histogram.png')
        hist_fig.savefig(os.path.join(app.static_folder, hist_path))
        hist_url   = url_for('static', filename=hist_path)

        # Scatter latență vs slot
        scatter_fig  = plot_latency_over_slots(df)
        scatter_path = os.path.join('images', 'scatter.png')
        scatter_fig.savefig(os.path.join(app.static_folder, scatter_path))
        scatter_url  = url_for('static', filename=scatter_path)

        # Rată succes la prima încercare
        total       = len(result.first_tx)
        first       = sum(1 for x in result.first_tx if x)
        retrans     = total - first
        first_pct   = (first / total * 100) if total else 0
        retrans_pct = (retrans / total * 100) if total else 0

        summary = {
            'total':       total,
            'first':       first,
            'first_pct':   first_pct,
            'retrans':     retrans,
            'retrans_pct': retrans_pct
        }

        return render_template('results.html',
                               stats_table=stats_table,
                               hist_url=hist_url,
                               scatter_url=scatter_url,
                               summary=summary,
                               logs=result.delivered_logs)
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
