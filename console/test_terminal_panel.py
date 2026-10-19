"""Panelens beteende kan verifieras utan externa bibliotek."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from terminal_panel import render


class PanelTests(unittest.TestCase):
    def setUp(self):
        self.entries = [{"name": "Alexander", "device_id": "alexander-esp32"}]

    def test_three_nodes_are_enough(self):
        text = render(self.entries, {"Alexander": {
            "DeviceId": "alexander-esp32", "Value": 22.5, "Unit": "C"}})
        self.assertIn("22.50", text)
        self.assertIn("C", text)
        self.assertIn("Anslutna: 1", text)
        self.assertNotIn("AKTUELLT", text)

    def test_pending_connection(self):
        self.assertIn("Ansluter...", render(self.entries, {}))

    def test_error_does_not_display_old_value(self):
        text = render(self.entries, {"Alexander": {"error": "Timeout"}})
        self.assertIn("Ej ansluten", text)
        self.assertIn("Timeout", text)
        self.assertIn("Anslutna: 0", text)

    def test_invalid_values(self):
        for value in (True, "22.5", None, float("nan"), float("inf")):
            with self.subTest(value=value):
                self.assertIn("Felaktig data", render(self.entries, {"Alexander": {
                    "DeviceId": "alexander-esp32", "Value": value, "Unit": "C"}}))

    def test_gateway_initial_value(self):
        text = render(self.entries, {"Alexander": {"DeviceId": "alexander-esp32",
                                                   "Value": 0.0, "Unit": ""}})
        self.assertIn("Väntar på data", text)
        self.assertNotIn("0.00", text)

    def test_zero_is_a_valid_measurement(self):
        self.assertIn("0.00", render(self.entries, {"Alexander": {
            "DeviceId": "alexander-esp32", "Value": 0.0, "Unit": "C"}}))

    def test_empty_server_list(self):
        self.assertIn("Inga servrar", render([], {}))

    def test_multiple_devices_and_units(self):
        entries = self.entries + [{"name": "Medlem 2", "device_id": "member2"}]
        text = render(entries, {
            "Alexander": {"DeviceId": "alexander-esp32", "Value": -5.25, "Unit": "C"},
            "Medlem 2": {"DeviceId": "member2", "Value": 50, "Unit": "%"}})
        self.assertIn("Servrar: 2 | Anslutna: 2", text)
        self.assertIn("-5.25", text)
        self.assertIn("50.00", text)

    def test_control_characters_removed_and_long_text_shortened(self):
        entries = [{"name": "A\nB", "device_id": "x" * 100}]
        text = render(entries, {"A\nB": {"error": "Oops\x1b[2J\nend"}})
        self.assertNotIn("\x1b", text)
        self.assertIn("A B", text)
        self.assertIn("...", text)


if __name__ == "__main__":
    unittest.main()
