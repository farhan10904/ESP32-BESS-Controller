
import sys
import time
import unittest
from pathlib import Path

import serial

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


PORT = "COM5"
BAUD_RATE = 115200


class TestHILFaults(unittest.TestCase):

    def setUp(self):
        self.esp32 = serial.Serial(
            PORT,
            BAUD_RATE,
            timeout=0.2,
            write_timeout=1.0
        )

        # Allow ESP32 to restart
        time.sleep(2)
        self.esp32.reset_input_buffer()

    def tearDown(self):
        self.esp32.close()

    def send_command(self, command):
        self.esp32.write(
            (command + "\n").encode("utf-8")
        )
        self.esp32.flush()

        deadline = time.monotonic() + 2.0

        while time.monotonic() < deadline:
            response = self.esp32.readline().decode(
                "utf-8", errors="replace"
            ).strip()

            if not response:
                continue

            if response.startswith("EVENT,"):
                print(f"ESP32 Event: {response}")
                continue

            return response

        self.fail(f"No response to command: {command}")

    def test_overtemperature_recovery(self):

        # 1. Normal operation
        response = self.send_command("DATA,60,25,2,1")
        self.assertEqual(
            response,
            "RESULT,2.000000,DISCHARGING,NONE"
        )
        print("Normal operation: PASS")

        # 2. Trigger overtemperature fault
        response = self.send_command("DATA,60,65,2,1")
        self.assertEqual(
            response,
            "RESULT,0.000000,FAULT,OVERTEMPERATURE"
        )
        print("Overtemperature shutdown: PASS")

        # 3. Try reset without recovery measurements
        response = self.send_command("RESET")
        self.assertEqual(response, "RESET,REJECTED")
        print("Reset without recovery data rejected: PASS")

        # 4. Supply fresh zero-power measurements
        response = self.send_command("DATA,60,58,0,1")
        self.assertEqual(
            response,
            "RESULT,0.000000,FAULT,OVERTEMPERATURE"
        )

        # Reset must fail while too hot
        response = self.send_command("RESET")
        self.assertEqual(response, "RESET,REJECTED")
        print("Unsafe temperature reset rejected: PASS")

        # 5. Supply safe recovery measurements
        response = self.send_command("DATA,60,50,0,1")
        self.assertEqual(
            response,
            "RESULT,0.000000,FAULT,OVERTEMPERATURE"
        )

        # Reset using stored validated measurements
        response = self.send_command("RESET")
        self.assertEqual(response, "RESET,OK")
        print("Safe recovery accepted: PASS")

        # 6. Confirm derated operation resumes
        response = self.send_command("DATA,60,50,2,1")
        self.assertEqual(
            response,
            "RESULT,1.000000,DERATED,NONE"
        )
        print("Derated operation restored: PASS")


if __name__ == "__main__":
    unittest.main(verbosity=2)