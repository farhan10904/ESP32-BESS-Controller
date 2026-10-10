
import time
import unittest

import serial


PORT = "COM5"
BAUD_RATE = 115200
WATCHDOG_TIMEOUT = 3.0


class TestHILWatchdog(unittest.TestCase):

    def setUp(self):
        self.esp32 = serial.Serial(
            PORT,
            BAUD_RATE,
            timeout=0.2,
            write_timeout=1.0
        )

        time.sleep(2)
        self.esp32.reset_input_buffer()

    def tearDown(self):
        self.esp32.close()

    def read_response(self, timeout=2.0):
        deadline = time.monotonic() + timeout

        while time.monotonic() < deadline:
            response = self.esp32.readline().decode(
                "utf-8", errors="replace"
            ).strip()

            if response:
                return response

        self.fail("ESP32 response timeout")

    def send_command(self, command):
        self.esp32.write(
            (command + "\n").encode("utf-8")
        )
        self.esp32.flush()

        return self.read_response()

    def test_communication_timeout(self):

        # 1. Verify normal operation
        response = self.send_command("DATA,60,25,2,1")

        self.assertEqual(
            response,
            "RESULT,2.000000,DISCHARGING,NONE"
        )
        print("Normal operation: PASS")

        # 2. Stop communication and wait for watchdog
        start_time = time.monotonic()

        response = self.read_response(timeout=4.0)

        elapsed = time.monotonic() - start_time

        self.assertEqual(
            response,
            "EVENT,COMMUNICATION_TIMEOUT"
        )

        self.assertGreaterEqual(elapsed, 2.5)
        self.assertLessEqual(elapsed, 4.0)

        print(f"Watchdog triggered after {elapsed:.2f}s: PASS")

        # 3. Verify fault remains latched
        response = self.send_command("DATA,60,25,2,1")

        self.assertEqual(
            response,
            "RESULT,0.000000,FAULT,COMMUNICATION_TIMEOUT"
        )
        print("Fault latching: PASS")

        
        # 4. Supply fresh zero-power recovery measurements
        response = self.send_command("DATA,60,25,0,1")

        self.assertEqual(
            response,
            "RESULT,0.000000,FAULT,COMMUNICATION_TIMEOUT"
        )
        print("Recovery measurements accepted: PASS")

        # 5. Reset using stored measurements
        response = self.send_command("RESET")

        self.assertEqual(response, "RESET,OK")
        print("Fault reset: PASS")


        # 5. Verify operation resumes
        response = self.send_command("DATA,60,25,2,1")

        self.assertEqual(
            response,
            "RESULT,2.000000,DISCHARGING,NONE"
        )
        print("Normal operation restored: PASS")


if __name__ == "__main__":
    unittest.main(verbosity=2)
