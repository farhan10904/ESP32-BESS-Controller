
import math


class BatteryController:
    def __init__(self, min_soc=20.0, max_soc=90.0,
                 max_power_kw=2.0,
                 derating_temp=40.0,
                 max_temp=60.0,
                 capacity_kwh=10.0,
                 efficiency=0.95,
                 reset_temp=55.0):

        if not (0 <= min_soc < max_soc <= 100):
            raise ValueError("Invalid SOC operating limits")

        if not math.isfinite(max_power_kw) or max_power_kw <= 0:
            raise ValueError("Invalid power limit")

        if not (derating_temp < reset_temp < max_temp):
            raise ValueError("Invalid temperature thresholds")

        if not math.isfinite(capacity_kwh) or capacity_kwh <= 0:
            raise ValueError("Invalid battery capacity")

        if not math.isfinite(efficiency) or not 0 < efficiency <= 1:
            raise ValueError("Invalid efficiency")

        self.min_soc = min_soc
        self.max_soc = max_soc
        self.max_power_kw = max_power_kw
        self.derating_temp = derating_temp
        self.max_temp = max_temp
        self.reset_temp = reset_temp
        self.capacity_kwh = capacity_kwh
        self.efficiency = efficiency

        # Fault memory
        self.fault_latched = False
        self.fault_reason = None

    def trigger_fault(self, reason):
        self.fault_latched = True
        self.fault_reason = reason
        return 0.0, "FAULT"

    def reset_fault(self, soc, temperature):
        # Reset only with valid measurements
        if not all(math.isfinite(v) for v in [soc, temperature]):
            return False

        if not 0 <= soc <= 100:
            return False

        # Require cooling below the reset threshold
        if temperature >= self.reset_temp:
            return False

        self.fault_latched = False
        self.fault_reason = None
        return True

    def update(self, soc, requested_power, temperature, dt=1.0):

        # 1. Validate incoming measurements
        if not all(math.isfinite(v) for v in
                   [soc, requested_power, temperature, dt]):
            return self.trigger_fault("INVALID_INPUT")

        if not 0 <= soc <= 100 or dt <= 0:
            return self.trigger_fault("INVALID_INPUT")

        # 2. Detect overtemperature
        if temperature >= self.max_temp:
            return self.trigger_fault("OVERTEMPERATURE")

        # 3. Remain in fault until explicitly reset
        if self.fault_latched:
            return 0.0, "FAULT"

        # 4. Apply rated power limit
        approved_power = max(
            -self.max_power_kw,
            min(requested_power, self.max_power_kw)
        )

        # 5. Apply thermal derating
        thermal_limit = self.max_power_kw

        if temperature > self.derating_temp:
            thermal_limit = self.max_power_kw * (
                (self.max_temp - temperature) /
                (self.max_temp - self.derating_temp)
            )

        derated = abs(approved_power) > thermal_limit

        approved_power = max(
            -thermal_limit,
            min(approved_power, thermal_limit)
        )

        # 6. Prevent SOC boundary overshoot
        margin = 1e-4

        if approved_power > 0:
            available_soc = max(
                0.0, soc - self.min_soc - margin
            )

            available_energy = (
                available_soc / 100 * self.capacity_kwh
            )

            max_discharge_power = (
                available_energy * 3600 *
                self.efficiency / dt
            )

            approved_power = min(
                approved_power, max_discharge_power
            )

        elif approved_power < 0:
            available_soc = max(
                0.0, self.max_soc - soc - margin
            )

            available_energy = (
                available_soc / 100 * self.capacity_kwh
            )

            max_charge_power = (
                available_energy * 3600 /
                (self.efficiency * dt)
            )

            approved_power = max(
                approved_power, -max_charge_power
            )

        # 7. Determine operating state
        if approved_power == 0:
            state = "IDLE"
        elif derated:
            state = "DERATED"
        elif approved_power > 0:
            state = "DISCHARGING"
        else:
            state = "CHARGING"

        return approved_power, state


if __name__ == "__main__":
    controller = BatteryController()

    # Normal operation
    print("Normal:", controller.update(60, 2.0, 25))

    # Trigger overtemperature fault
    print("Overtemperature:", controller.update(60, 2.0, 65))
    print("Fault reason:", controller.fault_reason)

    # Temperature drops, but fault remains latched
    print("Cooled to 58C:", controller.update(60, 2.0, 58))

    # Attempt reset above reset threshold
    print("Reset at 58C:", controller.reset_fault(60, 58))

    # Attempt reset below reset threshold
    print("Reset at 50C:", controller.reset_fault(60, 50))

    # Confirm normal operation resumes
    print("Recovered:", controller.update(60, 2.0, 50))
