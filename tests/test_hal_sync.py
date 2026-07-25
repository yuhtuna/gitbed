import unittest
from gitbed.hal_sync import build_multi_file_patch_bundle, generate_devicetree_overlay, generate_gpio_driver_cpp


class TestHALSync(unittest.TestCase):

    def test_generate_devicetree_overlay(self):
        diff_data = {"signal_name": "STATUS_LED", "new_pin": "PB7"}
        dts = generate_devicetree_overlay(diff_data)
        self.assertIn("status_led_led: status_led", dts)
        self.assertIn("gpios = <&gpiob 7 GPIO_ACTIVE_HIGH>;", dts)

    def test_generate_gpio_driver_cpp(self):
        diff_data = {"signal_name": "STATUS_LED", "new_pin": "PB7"}
        cpp = generate_gpio_driver_cpp(diff_data)
        self.assertIn("void init_gpio_status_led()", cpp)
        self.assertIn("gpio_init.Pin = STATUS_LED_PIN;", cpp)

    def test_build_multi_file_patch_bundle(self):
        diff_data = {"signal_name": "STATUS_LED", "new_pin": "PB7"}
        header = "#define STATUS_LED_PIN PB7"
        bundle = build_multi_file_patch_bundle(diff_data, header)
        self.assertIn("pin_config.h", bundle)
        self.assertIn("boards/app.overlay", bundle)
        self.assertIn("src/gpio_driver.cpp", bundle)
        self.assertEqual(bundle["pin_config.h"], header)


if __name__ == "__main__":
    unittest.main()
