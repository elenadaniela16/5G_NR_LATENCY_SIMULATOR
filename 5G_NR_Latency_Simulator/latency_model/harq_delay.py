def calculate_harq_delay(params):
    n_retx =int( params.get('n_retransmisii',0))
    feedback_delay =int( params.get('feedback_delay', 4))
    retrans_delay = int(params.get('retransmission_delay',8))

    return n_retx*(feedback_delay+retrans_delay)
