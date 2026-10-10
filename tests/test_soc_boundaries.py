
import unittest

from battery_model.battery import Battery
from controller.reference_controller import BatteryController


class TestSOCBoundaries(unittest.TestCase):

    def setUp(self):
        self.controller = BatteryController()

    def test_minimum_soc(self):
        battery = Battery(initial_soc=20.001)

        approved, state = self.controller.update(
            soc=battery.soc,
            requested_power=2.0,
            temperature=battery.temperature
        )

        battery.update(approved, dt=1.0)

        self.assertGreaterEqual(battery.soc, 20.0)

    def test_maximum_soc(self):
        battery = Battery(initial_soc=89.999)

        approved, state = self.controller.update(
            soc=battery.soc,
            requested_power=-2.0,
            temperature=battery.temperature
        )

        battery.update(approved, dt=1.0)

        self.assertLessEqual(battery.soc, 90.0)

    
    def test_different_time_steps(self):
        # Test discharge near minimum SOC
        battery = Battery(initial_soc=20.01)

        approved, state = self.controller.update(
            soc=battery.soc,
            requested_power=2.0,
            temperature=battery.temperature,
            dt=10.0
        )

        battery.update(approved, dt=10.0)

        self.assertGreaterEqual(battery.soc, 20.0)
        self.assertLess(approved, 2.0)

        # Test charging near maximum SOC
        battery = Battery(initial_soc=89.99)

        approved, state = self.controller.update(
            soc=battery.soc,
            requested_power=-2.0,
            temperature=battery.temperature,
            dt=10.0
        )

        battery.update(approved, dt=10.0)

        self.assertLessEqual(battery.soc, 90.0)
        self.assertGreater(approved, -2.0)



if __name__ == "__main__":
    unittest.main()
