
import unittest
import math

from controller.reference_controller import BatteryController


class TestFaultHandling(unittest.TestCase):

    def setUp(self):
        self.controller = BatteryController()

    def test_overtemperature_shutdown(self):
        approved, state = self.controller.update(
            soc=60,
            requested_power=2.0,
            temperature=60
        )

        self.assertEqual(approved, 0.0)
        self.assertEqual(state, "FAULT")
        self.assertTrue(self.controller.fault_latched)
        self.assertEqual(
            self.controller.fault_reason,
            "OVERTEMPERATURE"
        )

    def test_fault_latching_and_recovery(self):
        # Trigger fault
        self.controller.update(60, 2.0, 65)

        # Battery cools, but controller must stay in FAULT
        approved, state = self.controller.update(60, 2.0, 58)

        self.assertEqual(approved, 0.0)
        self.assertEqual(state, "FAULT")

        # Reset should fail above reset threshold
        reset_success = self.controller.reset_fault(60, 58)
        self.assertFalse(reset_success)

        # Reset should succeed below reset threshold
        reset_success = self.controller.reset_fault(60, 50)
        self.assertTrue(reset_success)

        # Normal operation resumes with thermal derating
        approved, state = self.controller.update(60, 2.0, 50)

        self.assertAlmostEqual(approved, 1.0)
        self.assertEqual(state, "DERATED")

    def test_invalid_sensor_data(self):
        approved, state = self.controller.update(
            soc=math.nan,
            requested_power=2.0,
            temperature=25
        )

        self.assertEqual(approved, 0.0)
        self.assertEqual(state, "FAULT")
        self.assertEqual(
            self.controller.fault_reason,
            "INVALID_INPUT"
        )

        # Even valid inputs cannot bypass the latched fault
        approved, state = self.controller.update(60, 2.0, 25)

        self.assertEqual(approved, 0.0)
        self.assertEqual(state, "FAULT")


if __name__ == "__main__":
    unittest.main()
