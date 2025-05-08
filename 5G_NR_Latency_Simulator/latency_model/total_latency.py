from latency_model.access_delay import calculate_access_delay
from latency_model.scheduling_delay import calculate_scheduling_delay
from latency_model.transmission_delay import calculate_transmission_delay
from latency_model.processing_delay import calculate_processing_delay
from latency_model.harq_delay import calculate_harq_delay
from latency_model.propagation_delay import calculate_propagation_delay

def calculate_total_latency(params):
    access = calculate_access_delay(params)
    scheduling = calculate_scheduling_delay(params)
    transmission = calculate_transmission_delay(params)
    processing = calculate_processing_delay(params)
    harq = calculate_harq_delay(params)
    propagation = calculate_propagation_delay(params)

    total_latency = access + scheduling + transmission + processing + harq + propagation

    return {
        'Access Delay': round(access, 3),
        'Scheduling Delay': round(scheduling, 3),
        'Transmission Delay': round(transmission, 3),
        'Processing Delay': round(processing, 3),
        'HARQ Delay': round(harq, 3),
        'Propagation Delay': round(propagation, 3),
        'Total Latency': round(total_latency, 3)
    }

