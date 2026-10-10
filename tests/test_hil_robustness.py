
import time
import unittest

import serial


PORT = "COM5"
BAUD_RATE = 115200


class TestHILRobustness(unittest.TestCase):

    def setUp(self):
        self.esp32 = serial.Serial(
            PORT,
            BAUD_RATE,
            timeout=0.2,
            write_timeout=1.0
        )

        # Opening the port normally resets the ESP32
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
                continue

            return response

        self.fail(f"No response to: {command}")

    def test_malformed_messages(self):

        scenarios = [
            (
                "Missing field",
                "DATA,60,25,2",
                "ERROR,INVALID_FORMAT"
            ),
            (
                "Extra field",
                "DATA,60,25,2,1,99",
                "ERROR,INVALID_FORMAT"
            ),
            (
                "Invalid number",
                "DATA,abc,25,2,1",
                "ERROR,INVALID_DATA"
            ),
            (
                "NaN measurement",
                "DATA,nan,25,2,1",
                "ERROR,INVALID_DATA"
            ),
            (
                "Negative time step",
                "DATA,60,25,2,-1",
                "ERROR,INVALID_DATA"
            ),
            (
                "SOC above 100%",
                "DATA,150,25,2,1",
                "ERROR,INVALID_DATA"
            )
        ]

        for name, command, expected in scenarios:
            with self.subTest(scenario=name):

                response = self.send_command(command)

                self.assertEqual(response, expected)

                print(f"{name}: PASS")

        # Verify that invalid sensor data caused a latched fault
        response = self.send_command("DATA,60,25,2,1")

        self.assertEqual(
            response,
            "RESULT,0.000000,FAULT,INVALID_INPUT"
        )

        print("Fault latching after invalid inputs: PASS")


if __name__ == "__main__":
    unittest.main(verbosity=2)
