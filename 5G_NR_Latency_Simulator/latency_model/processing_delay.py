def calculate_processing_delay(params):
    return float(params.get('processing_delay', 0.2))  # Default 0.2 ms dacă nu e altă valoare
