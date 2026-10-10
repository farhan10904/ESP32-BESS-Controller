
import time
import unittest
import serial


class TestInvalidData(unittest.TestCase):

    def test_invalid_soc(self):
        with serial.Serial(
            "COM5",
            115200,
            timeout=1,
            write_timeout=1
        ) as esp32:

            time.sleep(2)
            esp32.reset_input_buffer()

            # Send an impossible SOC measurement
            esp32.write(b"DATA,150,25,2,1\n")

            response = esp32.readline().decode().strip()

            print(f"Invalid SOC response: {response}")

            self.assertEqual(
                response,
                "ERROR,INVALID_DATA"
            )

            # Send a valid measurement immediately afterwards
            esp32.write(b"DATA,60,25,2,1\n")

            response = esp32.readline().decode().strip()

            print(f"Following valid request: {response}")

            # Record current behaviour, without assuming a fault
            self.assertTrue(
                response.startswith("RESULT,")
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
