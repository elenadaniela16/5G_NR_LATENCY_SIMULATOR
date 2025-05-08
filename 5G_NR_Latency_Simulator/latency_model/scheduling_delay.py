def calculate_scheduling_delay(params):
    mu =int( params.get('numerologie', 0)) #ia valoarea din dictionar pentru cheia numerologie, dar daca nu exista, pune 0
    k = int(params.get('k_sloturi', 1))
    tip_slot = params.get('tip_slot', 'slot')
    tip_ordonare = params.get('tip_ordonare', 'RR')

    n_symbs_str = params.get('n_symbs_mini_slot', '')
    n_symbs = int(n_symbs_str) if n_symbs_str.isdigit() else 2  # default la 2 dacă e gol

    T_symb=1/(15*1000*(2**mu))*1e3 #convertim in ms
    if tip_slot=='slot':
        durata_slot=14*T_symb
    elif tip_slot =='mini_slot':
        durata_slot=n_symbs*T_symb
    else:
        durata_slot=14*T_symb #fallback

    factori = {
        'RR':1,
        'BestCQI':0.8,
        'PF':0.9,
        'WFQ':0.7
    }   #deefinim un dictionar care asociaza fiecare algoritm de scheduling cu un factor de eficienta, cu cat factorul de mai mic, cu atat delay-ul etse mai mic
    factor= factori.get(tip_ordonare,1)

    return k*durata_slot*factor