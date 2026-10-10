
from battery_model.battery import Battery
from controller.reference_controller import BatteryController


def main():
    battery = Battery()
    controller = BatteryController()

    simulation_time = 900  # 15 minutes
    dt = 1.0
    requested_power = 3.0  # kW discharge

    print("Starting BESS simulation...\n")

    for step in range(simulation_time):

        # 1. Controller reads battery measurements
        approved_power, state = controller.update(
            soc=battery.soc,
            requested_power=requested_power,
            temperature=battery.temperature,
            dt=dt
        )

        # 2. Apply approved power to battery model
        battery.update(
            power_kw=approved_power,
            dt=dt
        )

        # 3. Display results every 5 minutes
        if (step + 1) % 300 == 0:
            print(
                f"Time: {step + 1}s | "
                f"SOC: {battery.soc:.2f}% | "
                f"Temp: {battery.temperature:.2f} C | "
                f"Power: {approved_power:.2f} kW | "
                f"State: {state}"
            )

    print("\nSimulation complete.")


if __name__ == "__main__":
    main()
