def calculate_access_delay(params):
    if params.get('ordonare_dinamica', True):
        T_sr=2
        T_grant=2
        return T_sr + T_grant
    else:
        return 0

#am luat valori constante deocamdata pentru T_sr si T_grant

