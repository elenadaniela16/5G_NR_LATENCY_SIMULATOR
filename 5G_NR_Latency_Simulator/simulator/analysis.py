import pandas as pd
import matplotlib.pyplot as plt
from simulator.simulator import SimulationResult


def build_dataframe(result: SimulationResult) -> pd.DataFrame:
    df = pd.DataFrame({
        'ue_id': result.ue_ids,
        'latency_ms': result.latencies,
        'slot_index': result.slot_indices
    })
    return df


def compute_statistics(df: pd.DataFrame) -> pd.DataFrame:
    stats = df.groupby('ue_id')['latency_ms'].agg(['mean', 'median', lambda x: x.quantile(0.95)]).rename(columns={'<lambda_0>': 'p95'})
    return stats


def plot_latency_histogram(df: pd.DataFrame, bins: int = 50) -> plt.Figure:
    fig, ax = plt.subplots()
    ax.hist(df['latency_ms'], bins=bins)
    ax.set_title('Histogram of Packet Latencies')
    ax.set_xlabel('Latency (ms)')
    ax.set_ylabel('Count')
    return fig


def plot_latency_over_slots(df: pd.DataFrame) -> plt.Figure:
    fig, ax = plt.subplots()
    ax.scatter(df['slot_index'], df['latency_ms'], s=10)
    ax.set_title('Packet Latency over Simulation Slots')
    ax.set_xlabel('Slot Index')
    ax.set_ylabel('Latency (ms)')
    return fig
