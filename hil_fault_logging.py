
import csv
import time
from pathlib import Path

import serial


PORT = "COM5"
BAUD_RATE = 115200

RESULTS_DIR = Path(__file__).resolve().parent / "results"

WATCHDOG_TIMEOUT = 3.0


def send_command(esp32, command, timeout=2.0):
    esp32.write((command + "\n").encode("utf-8"))
    esp32.flush()

    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        response = esp32.readline().decode(
            "utf-8", errors="replace"
        ).strip()

        if not response:
            continue

        if response.startswith("EVENT,"):
            print(f"Unsolicited ESP32 event: {response}")
            continue

        return response

    raise TimeoutError(f"No response to: {command}")


def main():
    RESULTS_DIR.mkdir(exist_ok=True)

    # Each scenario runs against actual ESP32 firmware
    scenarios = [
        (
            "NORMAL_DISCHARGE",
            "DATA,60,25,2,1",
            "RESULT,2.000000,DISCHARGING,NONE"
        ),
        (
            "OVERTEMPERATURE",
            "DATA,60,65,2,1",
            "RESULT,0.000000,FAULT,OVERTEMPERATURE"
        ),
        (
            "FAULT_LATCHED",
            "DATA,60,50,2,1",
            "RESULT,0.000000,FAULT,OVERTEMPERATURE"
        ),
        (
            "UNSAFE_RECOVERY_DATA",
            "DATA,60,58,0,1",
            "RESULT,0.000000,FAULT,OVERTEMPERATURE"
        ),
        (
            "RESET_REJECTED",
            "RESET",
            "RESET,REJECTED"
        ),
        (
            "SAFE_RECOVERY_DATA",
            "DATA,60,50,0,1",
            "RESULT,0.000000,FAULT,OVERTEMPERATURE"
        ),
        (
            "RESET_ACCEPTED",
            "RESET",
            "RESET,OK"
        ),
        (
            "DERATED_RECOVERY",
            "DATA,60,50,2,1",
            "RESULT,1.000000,DERATED,NONE"
        )
    ]

    records = []
    all_passed = True

    print("Starting ESP32 HIL Fault Logging\n")

    try:
        with serial.Serial(
            PORT,
            BAUD_RATE,
            timeout=0.2,
            write_timeout=1.0
        ) as esp32:

            # Opening COM5 normally resets the ESP32
            time.sleep(2)
            esp32.reset_input_buffer()

            start_time = time.monotonic()

            for event_name, command, expected in scenarios:

                response = send_command(esp32, command)

                elapsed = time.monotonic() - start_time
                passed = response == expected

                records.append({
                    "elapsed_time_s": round(elapsed, 3),
                    "event": event_name,
                    "command": command,
                    "expected_response": expected,
                    "actual_response": response,
                    "result": "PASS" if passed else "FAIL"
                })

                print(
                    f"{elapsed:6.3f}s | "
                    f"{event_name:<23} | "
                    f"{'PASS' if passed else 'FAIL'}"
                )

                if not passed:
                    print(f"  Expected: {expected}")
                    print(f"  Actual:   {response}")
                    all_passed = False
                    break

    except (
        serial.SerialException,
        TimeoutError,
        RuntimeError
    ) as error:
        all_passed = False
        print(f"\nTest interrupted: {error}")

    # Save actual recorded results, even after failure
    filename = RESULTS_DIR / "hil_fault_events.csv"

    fieldnames = [
        "elapsed_time_s",
        "event",
        "command",
        "expected_response",
        "actual_response",
        "result"
    ]

    with open(filename, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

    print(f"\nEvent log saved: {filename}")

    if all_passed and len(records) == len(scenarios):
        print("HIL FAULT LOGGING: PASS")
    else:
        print("HIL FAULT LOGGING: FAIL")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
