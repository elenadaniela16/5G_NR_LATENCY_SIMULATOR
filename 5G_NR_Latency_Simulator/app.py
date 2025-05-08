from flask import Flask, render_template, request

from latency_model.total_latency import calculate_total_latency  # import unic

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    result = {}
    if request.method == 'POST':
        params = request.form.to_dict()
        result = calculate_total_latency(params)
    return render_template('index.html', result=result)

if __name__ == '__main__':
    app.run(debug=True)
