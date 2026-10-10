
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


RESULTS_DIR = Path(__file__).resolve().parent / "results"

SCENARIOS = {
    "normal": "hil_normal.csv",
    "thermal_derating": "hil_thermal_derating.csv"
}


def plot_scenario(name, filename):
    data = pd.read_csv(RESULTS_DIR / filename)

    time_minutes = data["time_s"] / 60

    # 1. State of charge
    fig, ax = plt.subplots(figsize=(9, 5))

    ax.plot(
        time_minutes,
        data["soc_percent"],
        linewidth=2
    )

    ax.set(
        xlabel="Simulation Time (minutes)",
        ylabel="State of Charge (%)",
        title=f"Battery SOC - {name.replace('_', ' ').title()}"
    )

    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    fig.savefig(
        RESULTS_DIR / f"{name}_soc.png",
        dpi=300
    )
    plt.close(fig)

    # 2. Battery temperature
    fig, ax = plt.subplots(figsize=(9, 5))

    ax.plot(
        time_minutes,
        data["temperature_c"],
        linewidth=2
    )

    ax.set(
        xlabel="Simulation Time (minutes)",
        ylabel="Battery Temperature (°C)",
        title=f"Battery Temperature - {name.replace('_', ' ').title()}"
    )

    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    fig.savefig(
        RESULTS_DIR / f"{name}_temperature.png",
        dpi=300
    )
    plt.close(fig)

    # 3. Requested versus approved power
    fig, ax = plt.subplots(figsize=(9, 5))

    # Ignore the initial placeholder row
    active_data = data[data["time_s"] > 0]

    active_time = active_data["time_s"] / 60

    ax.plot(
        active_time,
        active_data["requested_power_kw"],
        label="Requested Power",
        linestyle="--",
        linewidth=2
    )

    ax.plot(
        active_time,
        active_data["approved_power_kw"],
        label="ESP32 Approved Power",
        linewidth=2
    )

    ax.set(
        xlabel="Simulation Time (minutes)",
        ylabel="Power (kW)",
        title=f"Power Control - {name.replace('_', ' ').title()}"
    )

    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    fig.savefig(
        RESULTS_DIR / f"{name}_power.png",
        dpi=300
    )
    plt.close(fig)

    print(f"Generated graphs for: {name}")



def plot_dynamic_scenario():
    data = pd.read_csv(RESULTS_DIR / "hil_dynamic.csv")

    time_minutes = data["time_s"] / 60

    # 1. Requested versus approved power
    fig, ax = plt.subplots(figsize=(10, 5))

    ax.step(
        time_minutes,
        data["requested_power_kw"],
        where="post",
        label="Requested Power",
        linestyle="--",
        linewidth=2
    )

    ax.step(
        time_minutes,
        data["approved_power_kw"],
        where="post",
        label="ESP32 Approved Power",
        linewidth=2
    )

    ax.set(
        xlabel="Simulation Time (minutes)",
        ylabel="Power (kW)",
        title="Dynamic Power Control - ESP32 HIL Test"
    )

    ax.axhline(0, linewidth=1, color="gray")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    fig.savefig(
        RESULTS_DIR / "dynamic_power.png",
        dpi=300
    )
    plt.close(fig)

    # 2. Operating-state timeline
    state_mapping = {
        "IDLE": 0,
        "CHARGING": 1,
        "DISCHARGING": 2,
        "DERATED": 3,
        "FAULT": 4
    }

    state_values = data["state"].map(state_mapping)

    if state_values.isna().any():
        raise ValueError("Unknown controller state in CSV")

    fig, ax = plt.subplots(figsize=(10, 5))

    ax.step(
        time_minutes,
        state_values,
        where="post",
        linewidth=2
    )

    ax.set_yticks(list(state_mapping.values()))
    ax.set_yticklabels(list(state_mapping.keys()))

    ax.set(
        xlabel="Simulation Time (minutes)",
        ylabel="Controller State",
        title="ESP32 Operating-State Timeline"
    )

    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    fig.savefig(
        RESULTS_DIR / "dynamic_states.png",
        dpi=300
    )
    plt.close(fig)

    print("Generated dynamic_power.png")
    print("Generated dynamic_states.png")


def plot_fault_events():
    data = pd.read_csv(
        RESULTS_DIR / "hil_fault_events.csv"
    )

    if data.empty:
        raise ValueError("Fault event log is empty")

    if not data["result"].eq("PASS").all():
        raise ValueError("Fault event log contains failed tests")

    fig, ax = plt.subplots(figsize=(11, 6))

    event_labels = data["event"].str.replace(
        "_", " ", regex=False
    )

    positions = range(len(data))

    ax.scatter(
        data["elapsed_time_s"],
        positions,
        s=90,
        zorder=3
    )

    ax.plot(
        data["elapsed_time_s"],
        positions,
        linewidth=1.5,
        alpha=0.6
    )

    ax.set_yticks(list(positions))
    ax.set_yticklabels(event_labels)
    ax.invert_yaxis()

    ax.set(
        xlabel="Elapsed Test Time (seconds)",
        ylabel="Fault Test Events",
        title="ESP32 HIL Fault Injection and Recovery"
    )

    ax.grid(axis="x", alpha=0.3)
    fig.tight_layout()

    fig.savefig(
        RESULTS_DIR / "hil_fault_timeline.png",
        dpi=300
    )

    plt.close(fig)

    print("Generated hil_fault_timeline.png")


def main():
    for name, filename in SCENARIOS.items():
        plot_scenario(name, filename)

    plot_dynamic_scenario()
    plot_fault_events()

    print("\nAll HIL graphs generated successfully.")


if __name__ == "__main__":
    main()
