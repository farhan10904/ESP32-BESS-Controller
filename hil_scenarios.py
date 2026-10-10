
import csv
import math
import time
from pathlib import Path

import serial

from battery_model.battery import Battery


PORT = "COM5"
BAUD_RATE = 115200

DT = 1.0
SIMULATION_STEPS = 900
REQUESTED_POWER = 2.0

REAL_STEP_DELAY = 0.02

RESULTS_DIR = Path(__file__).resolve().parent / "results"


def get_controller_response(esp32, soc, temperature, power, dt):
    message = (
        f"DATA,{soc:.6f},{temperature:.6f},"
        f"{power:.6f},{dt:.6f}\n"
    )

    esp32.write(message.encode("utf-8"))
    esp32.flush()

    deadline = time.monotonic() + 2.0

    while time.monotonic() < deadline:
        response = esp32.readline().decode(
            "utf-8", errors="replace"
        ).strip()

        if not response:
            continue

        if response.startswith("EVENT,"):
            raise RuntimeError(f"ESP32 event: {response}")

        parts = response.split(",")

        if len(parts) != 4 or parts[0] != "RESULT":
            raise RuntimeError(
                f"Unexpected ESP32 response: {response}"
            )

        try:
            approved = float(parts[1])
        except ValueError as error:
            raise RuntimeError(
                f"Invalid power: {response}"
            ) from error

        state = parts[2]
        fault = parts[3]

        valid_states = {
            "IDLE", "CHARGING", "DISCHARGING",
            "DERATED", "FAULT"
        }

        if (
            not math.isfinite(approved)
            or abs(approved) > 2.000001
            or state not in valid_states
        ):
            raise RuntimeError(
                f"Invalid controller output: {response}"
            )

        if state == "FAULT" or fault != "NONE":
            raise RuntimeError(f"Controller fault: {fault}")

        if (
            abs(approved) > abs(power) + 0.000001
            or (power > 0 and approved < 0)
            or (power < 0 and approved > 0)
            or (power == 0 and approved != 0)
        ):
            raise RuntimeError(
                f"Approved power violates request: {response}"
            )

        return approved, state, fault

    raise TimeoutError("ESP32 response timeout")


def main():
    RESULTS_DIR.mkdir(exist_ok=True)

    battery = Battery(
    initial_soc=60.0,
    initial_temp=50.0,
    ambient_temp=25.0
)
    log = []

    print("Starting HIL data logging...")
    print(f"Simulation duration: {SIMULATION_STEPS} seconds")
    print(f"Requested power: {REQUESTED_POWER} kW\n")

    # Log initial conditions
    log.append({
        "time_s": 0,
        "soc_percent": battery.soc,
        "temperature_c": battery.temperature,
        "requested_power_kw": 0.0,
        "approved_power_kw": 0.0,
        "state": "INITIAL",
        "fault": "NONE"
    })

    try:
        with serial.Serial(
            PORT,
            BAUD_RATE,
            timeout=0.2,
            write_timeout=1.0
        ) as esp32:

            time.sleep(2)
            esp32.reset_input_buffer()

            for step in range(SIMULATION_STEPS):

                approved, state, fault = get_controller_response(
                    esp32,
                    battery.soc,
                    battery.temperature,
                    REQUESTED_POWER,
                    DT
                )

                battery.update(approved, dt=DT)

                log.append({
                    "time_s": (step + 1) * DT,
                    "soc_percent": battery.soc,
                    "temperature_c": battery.temperature,
                    "requested_power_kw": REQUESTED_POWER,
                    "approved_power_kw": approved,
                    "state": state,
                    "fault": fault
                })

                if (step + 1) % 100 == 0:
                    print(
                        f"Time: {step + 1:4d}s | "
                        f"SOC: {battery.soc:.3f}% | "
                        f"Temp: {battery.temperature:.2f} C | "
                        f"Power: {approved:.2f} kW | "
                        f"State: {state}"
                    )

                time.sleep(REAL_STEP_DELAY)

    except (
        serial.SerialException,
        TimeoutError,
        RuntimeError,
        ValueError
    ) as error:
        print(f"\nHIL run aborted: {error}")
        print("Saving available data for diagnosis.")

        filename = RESULTS_DIR / "hil_normal_partial.csv"
        save_csv(log, filename)
        print(f"Partial results saved: {filename}")
        return

    filename = RESULTS_DIR / "hil_thermal_derating.csv"
    save_csv(log, filename)

    print("\nSimulation complete.")
    print(f"Final SOC: {battery.soc:.3f}%")
    print(f"Final temperature: {battery.temperature:.2f} C")
    print(f"Data saved to: {filename}")


def save_csv(log, filename):
    fieldnames = [
        "time_s",
        "soc_percent",
        "temperature_c",
        "requested_power_kw",
        "approved_power_kw",
        "state",
        "fault"
    ]

    with open(filename, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(log)


if __name__ == "__main__":
    main()
