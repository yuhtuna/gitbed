"""Unit tests for gitbed.watcher module."""
import os
import tempfile
import unittest
from unittest.mock import patch

from gitbed.watcher import _load_baseline_pins, process_netlist_file


class TestWatcher(unittest.TestCase):

    def test_process_netlist_file_not_found(self):
        result = process_netlist_file("non_existent_file_path_12345.net")
        self.assertIsNone(result)

    @patch("gitbed.utils.fetch_github_file")
    def test_load_baseline_pins_success(self, mock_fetch):
        mock_fetch.return_value = "#define INA_SDA_PIN P4\n#define INA_SCL_PIN P5"
        with patch.dict(os.environ, {"GITHUB_TOKEN": "token_123", "GITHUB_REPO": "user/repo"}):
            pins = _load_baseline_pins()
            self.assertEqual(pins.get("INA_SDA"), "P4")
            self.assertEqual(pins.get("INA_SCL"), "P5")

    @patch("gitbed.watcher._load_baseline_pins")
    def test_process_netlist_file_detects_change(self, mock_load):
        mock_load.return_value = {"INA_SDA": "P4", "INA_SCL": "P5"}
        sample_altium = "(\n INA_SDA\n U2-6\n)\n(\n INA_SCL\n U2-5\n)"
        
        with tempfile.NamedTemporaryFile("w", suffix=".NET", delete=False) as f:
            f.write(sample_altium)
            f.flush()
            temp_path = f.name

        try:
            result = process_netlist_file(temp_path)
            self.assertIsNotNone(result)
            self.assertEqual(result["signal_name"], "INA_SDA")
            self.assertEqual(result["new_pin"], "P6")
            self.assertEqual(result["old_pin"], "P4")
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)


if __name__ == "__main__":
    unittest.main()
