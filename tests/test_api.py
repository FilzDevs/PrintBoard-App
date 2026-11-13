import base64, json, threading, unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from printboard import api
from printboard.store import Printer

DATA = {
    "/printer/objects/list": {"objects": ["print_stats", "display_status", "toolhead", "gcode_move", "extruder", "extruder1",
                                           "heater_bed", "temperature_sensor chamber", "gcode_macro X"]},
    "/printer/info": {"state": "ready", "hostname": "voron24"},
    "/server/webcams/list": {"webcams": [{"stream_url": "/webcam/?action=stream"}]},
    "/server/files/list": [{"path": "benchy.gcode", "size": 1024, "modified": 1700000000}],
    "/server/gcode_store": {"gcode_store": [{"message": "ok", "time": 1700000000, "type": "response"}]},
    "/server/files/metadata": {"thumbnails": [{"width": 32, "height": 32, "size": 10, "relative_path": ".thumbs/benchy.png"}]},
}
STATUS = {"status": {"print_stats": {"state": "printing", "filename": "a.gcode", "print_duration": 600},
                     "display_status": {"progress": 0.5},
                     "toolhead": {"homed_axes": "xyz", "position": [100.0, 110.0, 12.5, 0.0]},
                     "gcode_move": {"homing_origin": [0.0, 0.0, 0.05, 0.0]},
                     "extruder": {"temperature": 210.0, "target": 210.0}, "extruder1": {"temperature": 25.0, "target": 0},
                     "heater_bed": {"temperature": 60.0, "target": 60.0},
                     "temperature_sensor chamber": {"temperature": 35.0}}}


class H(BaseHTTPRequestHandler):
    queried = []
    posted = []
    deleted = []

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/printer/objects/query":
            H.queried.append(self.path)
            body = STATUS
        elif path == "/server/files/gcodes/.thumbs/benchy.png":
            out = b"THUMB_PNG"
            self.send_response(200)
            self.send_header("Content-Length", str(len(out)))
            self.end_headers()
            self.wfile.write(out)
            return
        elif path == "/server/files/gcodes/benchy.gcode":
            out = b"G28\n"
            self.send_response(200)
            self.send_header("Content-Length", str(len(out)))
            self.end_headers()
            self.wfile.write(out)
            return
        else:
            body = DATA.get(path)
        code = 200 if body is not None else 404
        out = json.dumps({"result": body if body is not None else {}}).encode()
        self.send_response(code)
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(raw)
        except Exception:
            payload = {}
        H.posted.append((self.path, payload))
        out = json.dumps({"result": "ok"}).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)

    def do_DELETE(self):
        H.deleted.append(self.path)
        out = json.dumps({"result": "deleted"}).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)

    def log_message(self, *a):
        pass


class ApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = HTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.p = Printer("t", "127.0.0.1", cls.srv.server_port)

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def test_fetch(self):
        r = api.fetch(self.p)
        self.assertEqual(r["state"], "printing")
        self.assertAlmostEqual(r["remaining"], 600)
        self.assertEqual([t[0] for t in r["temps"]], ["Düse", "extruder1", "Bett", "chamber"])
        self.assertEqual(r["position"], [100.0, 110.0, 12.5])
        self.assertAlmostEqual(r["z_offset"], 0.05)
        self.assertNotIn("gcode_macro", H.queried[-1])

    def test_webcam(self):
        self.assertTrue(api.webcam_url(self.p).endswith("/webcam/?action=stream"))

    def test_printer_webcams(self):
        cams = api.printer_webcams(self.p)
        self.assertEqual(len(cams), 1)
        self.assertEqual(cams[0]["printer"], "t")
        self.assertTrue(cams[0]["url"].endswith("/webcam/?action=stream"))

    def test_all_webcams(self):
        cams = api.all_webcams([self.p])
        self.assertEqual(len(cams), 1)
        self.assertEqual(cams[0]["printer"], "t")
        self.assertTrue(cams[0]["url"].endswith("/webcam/?action=stream"))

    def test_job_thumbnail(self):
        self.assertEqual(api.job_thumbnail(self.p, "benchy.gcode"), b"THUMB_PNG")

    def test_remote_files_and_console(self):
        files = api.remote_files(self.p)
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0]["path"], "benchy.gcode")
        store = api.gcode_store(self.p, 10)
        self.assertEqual(store[0]["message"], "ok")

    def test_controls_and_remote_actions(self):
        api.control(self.p, "emergency_stop")
        self.assertEqual(H.posted[-1][0], "/printer/emergency_stop")
        api.control(self.p, "home", axes="X Y")
        self.assertEqual(H.posted[-1][1]["script"], "G28 X Y")
        api.control(self.p, "jog", axis="X", dist=10, speed=3000)
        self.assertIn("G1 X+10.00 F3000", H.posted[-1][1]["script"])
        api.control(self.p, "z_offset", delta=-0.01)
        self.assertIn("Z_ADJUST=-0.010", H.posted[-1][1]["script"])
        api.start_print(self.p, "benchy.gcode")
        self.assertEqual(H.posted[-1], ("/printer/print/start", {"filename": "benchy.gcode"}))
        api.delete_remote_file(self.p, "benchy.gcode")
        self.assertEqual(H.deleted[-1], "/server/files/gcodes/benchy.gcode")

    def test_probe_discovery(self):
        info = api._probe_moonraker("127.0.0.1", self.srv.server_port)
        self.assertIsNotNone(info)
        self.assertEqual(info["name"], "voron24")

    def test_unreachable(self):
        with self.assertRaises(Exception):
            api.fetch(Printer("x", "127.0.0.1", 1))


class FeatureTest(unittest.TestCase):
    def test_costs(self):
        from printboard import costs
        self.assertAlmostEqual(costs.mm_to_g(1000), 2.98, places=1)
        self.assertAlmostEqual(costs.job_cost(100, 3600, 25, 150, 0.30, 0.10), 2.5 + 0.045 + 0.10, places=3)
        st = costs.stats([{"status": "completed", "total_duration": 3600, "filament_used": 1000, "start_time": 1700000000},
                          {"status": "error", "total_duration": 1800, "start_time": 1700000000}])
        self.assertEqual((st["count"], st["completed"], round(st["success"])), (2, 1, 50))
        self.assertTrue(len(st["per_month"]) >= 1)

    def test_control_validation(self):
        with self.assertRaises(ValueError):
            api.control(Printer("x", "h"), "macro", name="G28; M112")
        with self.assertRaises(ValueError):
            api.control(Printer("x", "h"), "temp", heater="extruder;X", target=1)
        with self.assertRaises(ValueError):
            api.control(Printer("x", "h"), "home", axes="X;M112")
        with self.assertRaises(ValueError):
            api.control(Printer("x", "h"), "jog", axis="Q", dist=5)

    def test_library_and_file_management(self):
        import tempfile, zipfile, pathlib
        from printboard import library
        d = pathlib.Path(tempfile.mkdtemp())
        with zipfile.ZipFile(d / "Benchy.3mf", "w") as z:
            z.writestr("Metadata/plate_1.png", b"PNG")
        (d / "a.stl").write_text("x")
        (d / "n.txt").write_text("x")
        self.assertEqual(len(library.scan(d)), 2)
        self.assertEqual([f.name for f in library.scan(d, "benchy")], ["Benchy.3mf"])
        self.assertEqual(library.thumbnail(d / "Benchy.3mf"), b"PNG")

        # Test G-code thumbnail extraction & metadata
        b64 = base64.b64encode(b"GCODE_PNG_BYTES").decode()
        gcode_path = d / "part.gcode"
        gcode_path.write_text(
            f"; generated by OrcaSlicer 2.0\n"
            f"; estimated printing time (normal mode) = 1h 25m\n"
            f"; thumbnail begin 64x64 {len(b64)}\n"
            f"; {b64}\n"
            f"; thumbnail end\nG28\n"
        )
        self.assertEqual(library.thumbnail(gcode_path), b"GCODE_PNG_BYTES")
        details = library.file_details(gcode_path)
        self.assertIn("OrcaSlicer", details["meta"].get("Slicer", ""))
        self.assertEqual(details["meta"].get("Druckzeit"), "1h 25m")

        # Test rename, duplicate, move, zip extract, delete
        renamed = library.rename_file(d / "a.stl", "b.stl")
        self.assertEqual(renamed.name, "b.stl")
        dup = library.duplicate_file(renamed)
        self.assertTrue(dup.exists())
        sub = d / "subfolder"
        moved = library.move_file(dup, sub)
        self.assertEqual(moved.parent, sub)
        library.delete_file(moved)
        self.assertFalse(moved.exists())

        zip_file = d / "pack.zip"
        with zipfile.ZipFile(zip_file, "w") as z:
            z.writestr("nested/cube.stl", b"solid cube")
        out_dir, extracted = library.extract_zip(zip_file)
        self.assertEqual(len(extracted), 1)
        self.assertEqual(extracted[0].name, "cube.stl")


if __name__ == "__main__":
    unittest.main()
