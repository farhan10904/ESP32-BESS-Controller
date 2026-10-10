
import time
import math
import serial

from battery_model.battery import Battery


PORT = "COM5"
BAUD_RATE = 115200

SIMULATION_STEPS = 60
DT = 1.0
REQUESTED_POWER = 3.0

# Wall-clock pacing, separate from simulated time
REAL_STEP_DELAY = 0.2


def get_controller_response(esp32, soc, temperature, power, dt):
    message = (
        f"DATA,{soc:.6f},{temperature:.6f},"
        f"{power:.6f},{dt:.6f}\n"
    )

    esp32.write(message.encode("utf-8"))
    esp32.flush()

    # Read until we receive a controller result or timeout
    deadline = time.monotonic() + 2.0

    while time.monotonic() < deadline:
        response = esp32.readline().decode(
            "utf-8", errors="replace"
        ).strip()

        if not response:
            continue

        if response.startswith("EVENT,"):
            print(f"ESP32 event: {response}")
            continue

        parts = response.split(",")

        if len(parts) != 4 or parts[0] != "RESULT":
            raise RuntimeError(
                f"Unexpected ESP32 response: {response}"
            )

        try:
            approved_power = float(parts[1])
        except ValueError as error:
            raise RuntimeError(
                f"Invalid power response: {response}"
            ) from error

        state = parts[2]
        fault = parts[3]

        valid_states = {
            "IDLE", "CHARGING", "DISCHARGING",
            "DERATED", "FAULT"
        }

        if (
            not math.isfinite(approved_power)
            or abs(approved_power) > 2.000001
            or state not in valid_states
            or not fault
        ):
            raise RuntimeError(
                f"Invalid controller response: {response}"
            )

        if state == "FAULT" or fault != "NONE":
            if approved_power != 0.0:
                raise RuntimeError(
                    "Fault response approved nonzero power"
                )

            raise RuntimeError(
                f"Controller fault: {fault}"
            )

        if (
            abs(approved_power) > abs(power) + 0.000001
            or (power > 0 and approved_power < 0)
            or (power < 0 and approved_power > 0)
            or (power == 0 and approved_power != 0)
        ):
            raise RuntimeError(
                "Controller response violates request limits"
            )

        return approved_power, state

    raise TimeoutError("ESP32 response timeout")


def main():
    battery = Battery()

    print("Starting ESP32 Hardware-in-the-Loop Test")
    print(f"Serial Port: {PORT}")
    print(f"Initial SOC: {battery.soc:.2f}%")
    print(f"Initial Temperature: {battery.temperature:.2f} C\n")

    try:
        with serial.Serial(
            PORT,
            BAUD_RATE,
            timeout=0.2,
            write_timeout=1.0
        ) as esp32:

            # Opening the port may reset the ESP32
            time.sleep(2)
            esp32.reset_input_buffer()

            for step in range(SIMULATION_STEPS):

                approved_power, state = get_controller_response(
                    esp32,
                    soc=battery.soc,
                    temperature=battery.temperature,
                    power=REQUESTED_POWER,
                    dt=DT
                )

                # Apply ONLY approved power
                battery.update(
                    power_kw=approved_power,
                    dt=DT
                )

                if (step + 1) % 10 == 0:
                    print(
                        f"Time: {step + 1:3d}s | "
                        f"SOC: {battery.soc:.3f}% | "
                        f"Temp: {battery.temperature:.2f} C | "
                        f"Approved: {approved_power:.2f} kW | "
                        f"State: {state}"
                    )

                time.sleep(REAL_STEP_DELAY)

        print("\nHIL test completed successfully.")

    except (serial.SerialException, TimeoutError,
            RuntimeError, ValueError) as error:

        # Fail-safe simulation behaviour:
        # Do not reuse an earlier approved power command
        print(f"\nHIL TEST ABORTED: {error}")
        print("No further power commands applied.")
        print("Simulation stopped.")


if __name__ == "__main__":
    main()
