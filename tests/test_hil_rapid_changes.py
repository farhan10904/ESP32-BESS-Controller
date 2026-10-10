
import math
import time
import unittest

import serial

from controller.reference_controller import BatteryController


PORT = "COM5"
BAUD_RATE = 115200


class TestRapidPowerChanges(unittest.TestCase):

    def test_rapid_power_changes(self):
        reference = BatteryController()

        power_requests = [
            2.0, -2.0, 0.0, 3.0, -3.0,
            1.5, -1.5, 0.0, 2.5, -2.5
        ] * 10

        with serial.Serial(
            PORT,
            BAUD_RATE,
            timeout=0.2,
            write_timeout=1.0
        ) as esp32:

            time.sleep(2)
            esp32.reset_input_buffer()

            start = time.monotonic()

            for index, requested in enumerate(power_requests):
                message = (
                    f"DATA,60,25,{requested:.6f},1.0\n"
                )

                esp32.write(message.encode("utf-8"))
                esp32.flush()

                deadline = time.monotonic() + 1.0
                response = ""

                while time.monotonic() < deadline:
                    response = esp32.readline().decode(
                        "utf-8", errors="replace"
                    ).strip()

                    if response:
                        break

                parts = response.split(",")

                self.assertEqual(len(parts), 4, response)
                self.assertEqual(parts[0], "RESULT", response)

                approved = float(parts[1])
                state = parts[2]
                fault = parts[3]

                expected_power, expected_state = reference.update(
                    soc=60,
                    requested_power=requested,
                    temperature=25,
                    dt=1.0
                )

                self.assertTrue(math.isfinite(approved))
                self.assertAlmostEqual(
                    approved, expected_power, delta=0.0001
                )
                self.assertEqual(state, expected_state)
                self.assertEqual(fault, "NONE")

            elapsed = time.monotonic() - start

            print(
                f"{len(power_requests)} rapid requests: PASS"
            )
            print(f"Elapsed wall-clock time: {elapsed:.3f}s")


if __name__ == "__main__":
    unittest.main(verbosity=2)
