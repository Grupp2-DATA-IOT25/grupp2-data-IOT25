import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server_config import ConfigError, load_servers, validate_servers


class ConfigTests(unittest.TestCase):
    def setUp(self):
        self.entry = {"name": "Alexander", "device_id": "alexander-esp32",
                      "endpoint": "opc.tcp://192.168.1.50:4840/telemetry/"}

    def test_valid_ip_and_hostname(self):
        for endpoint in (self.entry["endpoint"], "opc.tcp://alexander-pi.local:4840/telemetry/",
                         "opc.tcp://[::1]:4840/telemetry/"):
            item = dict(self.entry, endpoint=endpoint)
            self.assertEqual(validate_servers([item]), [item])

    def test_invalid_top_level(self):
        for entries in ([], {}, None, "test", [1]):
            with self.subTest(entries=entries), self.assertRaises(ConfigError):
                validate_servers(entries)

    def test_missing_and_empty_fields(self):
        for field in self.entry:
            for value in (None, "", " ", 12, "bad\ntext"):
                with self.subTest(field=field, value=value), self.assertRaises(ConfigError):
                    validate_servers([dict(self.entry, **{field: value})])
            item = self.entry.copy()
            del item[field]
            with self.assertRaises(ConfigError):
                validate_servers([item])

    def test_duplicate_names(self):
        second = dict(self.entry, name="alexander", device_id="member2", endpoint="opc.tcp://192.168.1.51:4840/")
        with self.assertRaisesRegex(ConfigError, "name måste vara unikt"):
            validate_servers([self.entry, second])

    def test_duplicate_ids(self):
        second = dict(self.entry, name="Person 2", endpoint="opc.tcp://192.168.1.51:4840/")
        with self.assertRaisesRegex(ConfigError, "device_id måste vara unikt"):
            validate_servers([self.entry, second])

    def test_duplicate_endpoints(self):
        second = dict(self.entry, name="Person 2", device_id="member2")
        with self.assertRaisesRegex(ConfigError, "samma serveradress"):
            validate_servers([self.entry, second])

    def test_invalid_endpoint(self):
        addresses = ("http://192.168.1.50:4840/", "opc.tcp://192.168.1.50/", "opc.tcp://host:0/",
                     "opc.tcp://host:65536/", "opc.tcp://host:abc/", "opc.tcp://:4840/",
                     "opc.tcp://0.0.0.0:4840/", "opc.tcp://[::]:4840/", "opc.tcp://239.1.1.1:4840/",
                     "opc.tcp://BYT_TILL_PI_IP:4840/", "opc.tcp://host name:4840/",
                     "opc.tcp://user:pass@host:4840/", "opc.tcp://host:4840/?a=b",
                     "opc.tcp://host:4840/#node", "opc.tcp://999.999.1.1:4840/",
                     "opc.tcp://bad_host:4840/")
        for endpoint in addresses:
            with self.subTest(endpoint=endpoint), self.assertRaises(ConfigError):
                validate_servers([dict(self.entry, endpoint=endpoint)])

    def test_invalid_id(self):
        for device_id in ("Alexander-esp32", "alex esp32", "åke-esp32", "alex--esp32", "-alex"):
            with self.subTest(device_id=device_id), self.assertRaises(ConfigError):
                validate_servers([dict(self.entry, device_id=device_id)])

    def test_load_utf8_bom(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"servers.json"
            path.write_text(json.dumps([self.entry]),encoding="utf-8-sig")
            self.assertEqual(load_servers(path),[self.entry])

    def test_file_errors(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"servers.json"
            with self.assertRaises(ConfigError):
                load_servers(path)
            path.write_text('[{"name":',encoding="utf-8")
            with self.assertRaisesRegex(ConfigError,"rad"):
                load_servers(path)
            path.write_bytes(b'\xff\xff')
            with self.assertRaises(ConfigError):
                load_servers(path)

    def test_does_not_modify_entries(self):
        entries=[self.entry]
        before=copy.deepcopy(entries)
        validate_servers(entries)
        self.assertEqual(entries,before)


if __name__ == "__main__":
    unittest.main()
