
import sys
import time
import unittest
from pathlib import Path

import serial

# Allow execution from the repository root
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from controller.reference_controller import BatteryController


PORT = "COM5"
BAUD_RATE = 115200
POWER_TOLERANCE = 0.0001


class TestHILController(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        try:
            cls.esp32 = serial.Serial(
                PORT,
                BAUD_RATE,
                timeout=0.2,
                write_timeout=1.0
            )

            time.sleep(2)
            cls.esp32.reset_input_buffer()

        except serial.SerialException as error:
            raise RuntimeError(
                f"Cannot connect to ESP32: {error}"
            ) from error

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "esp32"):
            cls.esp32.close()

    def setUp(self):
        self.reference = BatteryController()

    def get_esp32_result(self, soc, temperature, power, dt=1.0):
        message = (
            f"DATA,{soc:.6f},{temperature:.6f},"
            f"{power:.6f},{dt:.6f}\n"
        )

        self.esp32.write(message.encode("utf-8"))
        self.esp32.flush()

        deadline = time.monotonic() + 2.0

        while time.monotonic() < deadline:
            response = self.esp32.readline().decode(
                "utf-8", errors="replace"
            ).strip()

            if not response or response.startswith("EVENT,"):
                continue

            parts = response.split(",")

            if len(parts) != 4 or parts[0] != "RESULT":
                self.fail(f"Unexpected ESP32 response: {response}")

            try:
                approved = float(parts[1])
            except ValueError:
                self.fail(f"Invalid power: {response}")

            return approved, parts[2], parts[3]

        self.fail("ESP32 response timeout")

    def test_reference_equivalence(self):
        scenarios = [
            ("Normal discharge", 60, 25, 1.5),
            ("Power limiting", 60, 25, 3.0),
            ("Normal charging", 60, 25, -1.5),
            ("Maximum SOC", 95, 25, -2.0),
            ("Minimum SOC", 15, 25, 2.0),
            ("Thermal derating", 60, 50, 2.0),
            ("Derated charging", 60, 50, -2.0),
            ("Idle", 60, 25, 0.0)
        ]

        for name, soc, temp, requested in scenarios:
            with self.subTest(scenario=name):

                expected_power, expected_state = (
                    self.reference.update(
                        soc=soc,
                        requested_power=requested,
                        temperature=temp,
                        dt=1.0
                    )
                )

                actual_power, actual_state, fault = (
                    self.get_esp32_result(
                        soc, temp, requested
                    )
                )

                self.assertAlmostEqual(
                    actual_power,
                    expected_power,
                    delta=POWER_TOLERANCE
                )

                self.assertEqual(actual_state, expected_state)
                self.assertEqual(fault, "NONE")

                print(
                    f"{name}: "
                    f"Python={expected_power:+.2f} kW | "
                    f"ESP32={actual_power:+.2f} kW | "
                    f"{actual_state} | PASS"
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
