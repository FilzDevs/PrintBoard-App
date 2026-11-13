import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

from printboard import spoolman
from printboard.store import Printer


class MockSpoolmanHandler(BaseHTTPRequestHandler):
    calls = []

    def _send(self, payload, status=200):
        raw = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _read_json(self):
        length = int(self.headers.get("Content-Length", 0))
        if not length:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def do_GET(self):
        path = self.path.split("?")[0]
        MockSpoolmanHandler.calls.append(("GET", self.path, None))
        if path == "/api/v1/info":
            self._send({"version": "0.27.1"})
        elif path == "/api/v1/spool":
            self._send([
                {
                    "id": 1,
                    "filament": {
                        "id": 1,
                        "name": "PLA Black",
                        "material": "PLA",
                        "color_hex": "000000",
                        "weight": 1000.0,
                        "vendor": {"id": 1, "name": "TECBEARS"},
                    },
                    "price": 12.0,
                    "remaining_weight": 850.0,
                    "used_weight": 150.0,
                    "archived": False,
                    "extra": {"card_uids": "\"04974B3FE22A81\""},
                }
            ])
        elif path == "/api/v1/filament":
            self._send([{"id": 1, "name": "PLA Black", "material": "PLA", "vendor": {"id": 1, "name": "TECBEARS"}}])
        elif path == "/api/v1/vendor":
            self._send([{"id": 1, "name": "TECBEARS"}])
        elif path == "/api/v1/location":
            self._send(["Regal A"])
        elif path == "/api/v1/material":
            self._send(["PLA", "PETG"])
        elif path == "/api/v1/external/filament/search":
            self._send([
                {
                    "id": "poly_pla_black",
                    "manufacturer": "Polymaker",
                    "name": "PolyLite PLA Black",
                    "material": "PLA",
                    "density": 1.24,
                    "diameter": 1.75,
                    "weight": 1000.0,
                    "spool_weight": 140.0,
                    "color_hex": "111111",
                    "extruder_temp": 210,
                    "bed_temp": 60,
                }
            ])
        else:
            self._send({}, 404)

    def do_POST(self):
        body = self._read_json()
        MockSpoolmanHandler.calls.append(("POST", self.path, body))
        if self.path == "/api/v1/vendor":
            self._send({"id": 2, "name": body.get("name", "Vendor")})
        elif self.path == "/api/v1/filament":
            self._send({"id": 2, **body})
        elif self.path == "/api/v1/spool":
            self._send({"id": 2, **body})
        elif self.path == "/api/v1/backup":
            self._send({"path": "/backups/spoolman.db", "created": True})
        else:
            self._send({"result": "ok"})

    def do_PATCH(self):
        body = self._read_json()
        MockSpoolmanHandler.calls.append(("PATCH", self.path, body))
        self._send({"id": 1, **body})

    def do_PUT(self):
        body = self._read_json()
        MockSpoolmanHandler.calls.append(("PUT", self.path, body))
        self._send({"id": 1, **body})

    def do_DELETE(self):
        MockSpoolmanHandler.calls.append(("DELETE", self.path, None))
        self._send({"message": "Success!"})

    def log_message(self, *args):
        pass


class SpoolmanTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = HTTPServer(("127.0.0.1", 0), MockSpoolmanHandler)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.url = f"http://127.0.0.1:{cls.srv.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def test_helpers(self):
        self.assertEqual(spoolman.normalize_url("192.168.178.170:7912/api/v1/"), "http://192.168.178.170:7912")
        self.assertEqual(spoolman.format_card_uid([4, 151, 75, 63, 226, 42, 129]), "04974B3FE22A81")
        dec = spoolman.decode_extra({"card_uids": "\"04974B3FE22A81\"", "variant": "\"Rapid\""})
        self.assertEqual(dec["card_uids"], "04974B3FE22A81")
        self.assertEqual(dec["variant"], "Rapid")
        self.assertEqual(spoolman.encode_extra_value("04974B3FE22A81"), "\"04974B3FE22A81\"")
        self.assertIsNone(spoolman.encode_extra_value(""))

    def test_crud_and_bundle(self):
        bundle = spoolman.fetch_bundle(self.url)
        self.assertEqual(bundle["info"]["version"], "0.27.1")
        self.assertEqual(len(bundle["spools"]), 1)
        self.assertEqual(spoolman.spool_display_name(bundle["spools"][0]), "#1 TECBEARS PLA Black [PLA]")

        # Create, update, weigh, use, delete spool
        created = spoolman.create_spool(self.url, {"filament_id": 1, "remaining_weight": 1000})
        self.assertEqual(created["id"], 2)
        updated = spoolman.update_spool(self.url, 1, {"location": "Drybox 1"})
        self.assertEqual(updated["location"], "Drybox 1")
        measured = spoolman.measure_spool(self.url, 1, 950.0)
        self.assertEqual(measured["weight"], 950.0)
        used = spoolman.use_spool(self.url, 1, use_weight=25.0)
        self.assertEqual(used["use_weight"], 25.0)
        spoolman.delete_spool(self.url, 2)

        # Backup
        bk = spoolman.trigger_backup(self.url)
        self.assertEqual(bk["path"], "/backups/spoolman.db")

    def test_external_import(self):
        results = spoolman.search_external_filaments(self.url, "polymaker")
        self.assertEqual(len(results), 1)
        imp = spoolman.import_external_filament(self.url, results[0], vendors=[{"id": 1, "name": "TECBEARS"}])
        self.assertEqual(imp["name"], "PolyLite PLA Black")
        self.assertEqual(imp["vendor_id"], 2)


if __name__ == "__main__":
    unittest.main()
