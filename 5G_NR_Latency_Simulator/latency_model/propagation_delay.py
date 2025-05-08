def calculate_propagation_delay(params):
    distanta = int(params.get('distanta', 100))  # Distanța default 100 metri
    c = 3e8  # Viteza luminii în m/s

    return (distanta / c) * 1000  # Conversie la milisecunde
