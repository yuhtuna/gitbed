import unittest
from gitbed.parsers import parse_altium_netlist, parse_kicad_netlist


class TestEDAnetlistParsers(unittest.TestCase):

    def test_parse_kicad_netlist(self):
        kicad_sample = (
            '(export (version D)\n'
            '  (nets\n'
            '    (net (code 1) (name "STATUS_LED")\n'
            '      (node (ref U1) (pin 7)))\n'
            '  )\n'
            ')'
        )
        diffs = parse_kicad_netlist(kicad_sample)
        self.assertEqual(len(diffs), 1)
        self.assertEqual(diffs[0]["signal_name"], "STATUS_LED")
        self.assertEqual(diffs[0]["new_pin"], "P7")

    def test_parse_altium_xml_netlist(self):
        altium_sample = (
            '<Netlist><Net Name="STATUS_LED"><Node ComponentRef="U1" Pin="7"/></Net></Netlist>'
        )
        diffs = parse_altium_netlist(altium_sample)
        self.assertEqual(len(diffs), 1)
        self.assertEqual(diffs[0]["signal_name"], "STATUS_LED")
        self.assertEqual(diffs[0]["new_pin"], "P7")

    def test_parse_altium_text_netlist_fallback(self):
        altium_text = "(\n STATUS_LED\n U1-7\n)"
        diffs = parse_altium_netlist(altium_text)
        self.assertEqual(len(diffs), 1)
        self.assertEqual(diffs[0]["signal_name"], "STATUS_LED")
        self.assertEqual(diffs[0]["new_pin"], "P7")


if __name__ == "__main__":
    unittest.main()
