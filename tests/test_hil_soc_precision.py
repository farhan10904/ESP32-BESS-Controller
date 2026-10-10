
import time
import unittest

import serial


PORT = "COM5"
BAUD_RATE = 115200


class TestHILSOCPrecision(unittest.TestCase):

    def setUp(self):
        self.esp32 = serial.Serial(
            PORT, BAUD_RATE,
            timeout=0.2,
            write_timeout=1.0
        )

        time.sleep(2)
        self.esp32.reset_input_buffer()

    def tearDown(self):
        self.esp32.close()

    def test_soc_boundaries(self):
        scenarios = [
            ("Minimum boundary", 20.0, 2.0, 1.0),
            ("Just above minimum", 20.001, 2.0, 1.0),
            ("Maximum boundary", 90.0, -2.0, 1.0),
            ("Just below maximum", 89.999, -2.0, 1.0),
            ("Long discharge step", 20.01, 2.0, 10.0),
            ("Long charge step", 89.99, -2.0, 10.0)
        ]

        for name, soc, requested, dt in scenarios:
            message = (
                f"DATA,{soc:.6f},25.0,"
                f"{requested:.6f},{dt:.6f}\n"
            )

            self.esp32.write(message.encode())
            self.esp32.flush()

            response = self.esp32.readline().decode().strip()
            parts = response.split(",")

            self.assertEqual(parts[0], "RESULT", response)
            self.assertEqual(parts[3], "NONE", response)

            approved = float(parts[1])
            self.assertLessEqual(abs(approved), 2.0)

            # Predict the SOC after applying ESP32 power
            if approved > 0:
                final_soc = soc - (
                    approved * dt /
                    (3600 * 10 * 0.95) * 100
                )
                self.assertGreaterEqual(final_soc, 20.0)

            elif approved < 0:
                final_soc = soc - (
                    approved * dt * 0.95 /
                    (3600 * 10) * 100
                )
                self.assertLessEqual(final_soc, 90.0)

            print(
                f"{name}: "
                f"Approved={approved:+.6f} kW | PASS"
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)

