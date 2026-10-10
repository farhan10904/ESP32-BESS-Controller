
import math


class Battery:
    def __init__(
        self,
        capacity_kwh=10.0,
        initial_soc=60.0,
        efficiency=0.95,
        initial_temp=25.0,
        ambient_temp=25.0,
        thermal_capacity=60000.0,
        thermal_conductance=5.0
    ):

        if not math.isfinite(capacity_kwh) or capacity_kwh <= 0:
            raise ValueError("Battery capacity must be positive and finite")

        if not math.isfinite(initial_soc) or not 0 <= initial_soc <= 100:
            raise ValueError("Initial SOC must be between 0 and 100%")

        if not math.isfinite(efficiency) or not 0 < efficiency <= 1:
            raise ValueError("Efficiency must be between 0 and 1")

        if not all(math.isfinite(v) for v in
                   [initial_temp, ambient_temp,
                    thermal_capacity, thermal_conductance]):
            raise ValueError("Thermal parameters must be finite")

        if thermal_capacity <= 0 or thermal_conductance < 0:
            raise ValueError("Invalid thermal parameters")

        self.capacity_kwh = capacity_kwh
        self.soc = initial_soc
        self.efficiency = efficiency

        self.temperature = initial_temp
        self.ambient_temp = ambient_temp
        self.thermal_capacity = thermal_capacity
        self.thermal_conductance = thermal_conductance

    def update(self, power_kw, dt=1.0):

        if not math.isfinite(power_kw):
            raise ValueError("Power must be finite")

        if not math.isfinite(dt) or dt <= 0:
            raise ValueError("Time step must be positive and finite")

        # 1. Electrical energy balance
        energy_change = power_kw * dt / 3600

        if power_kw > 0:
            energy_change /= self.efficiency

        elif power_kw < 0:
            energy_change *= self.efficiency

        soc_change = (energy_change / self.capacity_kwh) * 100
        self.soc -= soc_change

        # 2. Heat generation from efficiency losses
        power_w = abs(power_kw) * 1000

        if power_kw > 0:
            heat_generated = power_w * (1 / self.efficiency - 1)

        elif power_kw < 0:
            heat_generated = power_w * (1 - self.efficiency)

        else:
            heat_generated = 0.0

        # 3. Heat transfer to surroundings
        heat_cooling = self.thermal_conductance * (
            self.temperature - self.ambient_temp
        )

        # 4. Temperature integration
        net_heat = heat_generated - heat_cooling

        temperature_change = (
            net_heat * dt / self.thermal_capacity
        )

        self.temperature += temperature_change


if __name__ == "__main__":
    battery = Battery()

    print(f"Initial SOC: {battery.soc:.2f}%")
    print(f"Initial Temperature: {battery.temperature:.2f} C")

    # Discharge at 2 kW for one hour
    for second in range(3600):
        battery.update(power_kw=2.0, dt=1.0)

    print(f"Final SOC: {battery.soc:.2f}%")
    print(f"Final Temperature: {battery.temperature:.2f} C")
    
    # Test 2: Battery cooling while idle
    print("\nStarting idle cooling test...")

    for second in range(3600):
        battery.update(power_kw=0.0, dt=1.0)

    print(f"SOC after cooling: {battery.soc:.2f}%")
    print(f"Temperature after cooling: {battery.temperature:.2f} C")

