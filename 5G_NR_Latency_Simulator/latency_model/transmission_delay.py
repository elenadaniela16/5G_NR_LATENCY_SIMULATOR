def calculate_transmission_delay(params):
    n_bits =int( params.get('n_bits', 1000))
    mod_order = int(params.get('modulation_order', 2))
    mu = int(params.get('numerologie', 0))
    overhead=float(params.get('overhead',0.2))

    delta_f=15*1000*(2**mu)
    if mod_order == 0 or delta_f == 0:
        return float('inf') #evitam impartirea la 0
    transmission_time = (n_bits/(mod_order*delta_f))*(1+overhead)
    return transmission_time*1e3
