import unittest
from gitbed.conflict_checker import PinConflictChecker


class TestPinConflictChecker(unittest.TestCase):

    def setUp(self):
        self.checker = PinConflictChecker()

    def test_no_conflict_clean_code(self):
        code = "#define STATUS_LED_PIN PB7\n#define UART_TX_PIN PA9\n"
        clean, errs = self.checker.check_code_conflicts(code, "PB7", "STATUS_LED")
        self.assertTrue(clean)
        self.assertEqual(len(errs), 0)

    def test_duplicate_pin_assignment_conflict(self):
        code = "#define STATUS_LED_PIN PB7\n#define BUTTON_PIN PB7\n"
        clean, errs = self.checker.check_code_conflicts(code, "PB7", "STATUS_LED")
        self.assertFalse(clean)
        self.assertTrue(any("already assigned to signal" in e for e in errs))

    def test_peripheral_bus_collision(self):
        code = "#define ENABLE_I2C1 1\n#define STATUS_LED_PIN PB7\n"
        clean, errs = self.checker.check_code_conflicts(code, "PB7", "STATUS_LED")
        self.assertFalse(clean)
        self.assertTrue(any("Peripheral Conflict" in e for e in errs))


if __name__ == "__main__":
    unittest.main()
