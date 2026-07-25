import os
import unittest
from gitbed.bridge import BridgeCache, DEFAULT_RULES


class TestBridgeCache(unittest.TestCase):

    def setUp(self):
        self.test_cache_file = ".test_gitbed_rules.json"
        if os.path.exists(self.test_cache_file):
            os.remove(self.test_cache_file)

    def tearDown(self):
        if os.path.exists(self.test_cache_file):
            os.remove(self.test_cache_file)

    def test_apply_default_macro_pin_rule(self):
        cache = BridgeCache(cache_file=self.test_cache_file)
        code = "#define STATUS_LED_PIN PB6\nvoid init();"
        diff_data = {
            "signal_name": "STATUS_LED",
            "old_pin": "PB6",
            "new_pin": "PB7",
        }

        success, updated_code, rule_id = cache.apply_rules(code, diff_data)
        self.assertTrue(success)
        self.assertIn("#define STATUS_LED_PIN PB7", updated_code)
        self.assertEqual(rule_id, "standard_macro_pin")

    def test_apply_constexpr_pin_rule(self):
        cache = BridgeCache(cache_file=self.test_cache_file)
        code = "constexpr uint8_t STATUS_LED = PB6;"
        diff_data = {
            "signal_name": "STATUS_LED",
            "old_pin": "PB6",
            "new_pin": "PB7",
        }

        success, updated_code, rule_id = cache.apply_rules(code, diff_data)
        self.assertTrue(success)
        self.assertIn("constexpr uint8_t STATUS_LED = PB7;", updated_code)
        self.assertEqual(rule_id, "constexpr_pin_assignment")

    def test_add_and_persist_custom_rule(self):
        cache = BridgeCache(cache_file=self.test_cache_file)
        custom_rule = {
            "rule_id": "custom_gpio_struct",
            "match_pattern": r"(GPIO_PIN_{signal}\s*=\s*){old_pin}",
            "replace_pattern": r"\g<1>{new_pin}",
            "description": "Custom struct rule",
        }
        cache.add_rule(custom_rule)

        # Reload cache from disk
        reloaded_cache = BridgeCache(cache_file=self.test_cache_file)
        code = "GPIO_PIN_STATUS_LED = PB6;"
        diff_data = {
            "signal_name": "STATUS_LED",
            "old_pin": "PB6",
            "new_pin": "PB7",
        }

        success, updated_code, rule_id = reloaded_cache.apply_rules(code, diff_data)
        self.assertTrue(success)
        self.assertIn("GPIO_PIN_STATUS_LED = PB7;", updated_code)
        self.assertEqual(rule_id, "custom_gpio_struct")


if __name__ == "__main__":
    unittest.main()
