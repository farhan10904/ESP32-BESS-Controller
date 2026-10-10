
import csv
import time
from pathlib import Path

import serial

from battery_model.battery import Battery
from hil_scenarios import get_controller_response


PORT = "COM5"
BAUD_RATE = 115200

DT = 1.0
REAL_STEP_DELAY = 0.02

RESULTS_DIR = Path(__file__).resolve().parent / "results"

# (Duration in seconds, Requested power in kW)
POWER_SCHEDULE = [
    (60, 2.0),
    (60, 0.0),
    (60, -2.0),
    (60, 3.0),
    (60, 0.0)
]


def main():
    battery = Battery()
    log = []

    RESULTS_DIR.mkdir(exist_ok=True)

    print("Starting Dynamic HIL Test\n")

    try:
        with serial.Serial(
            PORT,
            BAUD_RATE,
            timeout=0.2,
            write_timeout=1.0
        ) as esp32:

            time.sleep(2)
            esp32.reset_input_buffer()

            simulation_time = 0

            for duration, requested_power in POWER_SCHEDULE:

                print(
                    f"New request: {requested_power:+.1f} kW"
                )

                for step in range(duration):

                    approved, state, fault = (
                        get_controller_response(
                            esp32,
                            battery.soc,
                            battery.temperature,
                            requested_power,
                            DT
                        )
                    )

                    battery.update(approved, dt=DT)

                    simulation_time += DT

                    log.append({
                        "time_s": simulation_time,
                        "soc_percent": battery.soc,
                        "temperature_c": battery.temperature,
                        "requested_power_kw": requested_power,
                        "approved_power_kw": approved,
                        "state": state,
                        "fault": fault
                    })

                    time.sleep(REAL_STEP_DELAY)

                print(
                    f"Time: {simulation_time:.0f}s | "
                    f"SOC: {battery.soc:.3f}% | "
                    f"State: {state} | "
                    f"Approved: {approved:+.2f} kW\n"
                )

    except (
        serial.SerialException,
        TimeoutError,
        RuntimeError,
        ValueError
    ) as error:
        print(f"HIL test aborted: {error}")
        print("No further battery updates will be applied.")
        return

    filename = RESULTS_DIR / "hil_dynamic.csv"

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

    print("Dynamic HIL Test Complete")
    print(f"Final SOC: {battery.soc:.3f}%")
    print(f"Final Temperature: {battery.temperature:.2f} C")
    print(f"Results saved: {filename}")


if __name__ == "__main__":
    main()
