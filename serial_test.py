
import time
import serial

PORT = "COM5"
BAUD_RATE = 115200


def main():
    try:
        with serial.Serial(PORT, BAUD_RATE, timeout=2) as esp32:

            # Allow ESP32 to restart after serial connection
            time.sleep(2)

            # Clear any startup messages
            esp32.reset_input_buffer()

            message = "POWER:1.5\n"

            print(f"Sending: {message.strip()}")

            esp32.write(message.encode("utf-8"))
            esp32.flush()

            response = esp32.readline().decode(
                "utf-8", errors="replace"
            ).strip()

            print(f"ESP32 Response: {response}")

            if response == "RECEIVED:POWER:1.5":
                print("Communication test PASSED")
            else:
                print("Communication test FAILED")

    except serial.SerialException as error:
        print(f"Serial communication error: {error}")


if __name__ == "__main__":
    main()
