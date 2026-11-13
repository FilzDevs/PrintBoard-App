import json
import tempfile
import threading
import unittest
import urllib.request
from pathlib import Path

from printboard import api, costs, library, server, sim


class TestStudioFeatures(unittest.TestCase):
    def test_simulation_fleet_telemetry_and_control(self):
        printers = sim.DEMO_PRINTERS
        self.assertGreaterEqual(len(printers), 3)
        p = printers[0]
        data = api.fetch(p)
        self.assertIn("state", data)
        self.assertIn("temps", data)
        self.assertIn("bed_mesh", data)
        self.assertIn("exclude_object", data)
        self.assertIn("speed_factor", data)
        self.assertIn("extrude_factor", data)

        # Test speed, flow, and exclude_object control on simulated printer
        api.set_speed(p, 125)
        api.set_flow(p, 98)
        objs = data["exclude_object"]["objects"]
        if objs:
            first_name = objs[0]["name"]
            api.control(p, "exclude_object", name=first_name)
            updated = api.fetch(p)
            self.assertIn(first_name, updated["exclude_object"]["excluded_objects"])

    def test_quote_calculator(self):
        res = costs.calculate_quote(
            grams=120.0,
            hours=4.5,
            eur_per_kg=25.0,
            eur_per_kwh=0.30,
            watts=150.0,
            wear_per_h=0.20,
            prep_mins=15.0,
            labor_eur_h=24.0,
            fail_risk_pct=10.0,
            margin_pct=35.0,
            vat_pct=19.0,
            copies=2,
            waste_pct=5.0,
        )
        self.assertEqual(res["copies"], 2)
        self.assertGreater(res["unit_gross_eur"], res["unit_net_eur"])
        self.assertGreater(res["unit_net_eur"], res["unit_production_eur"])
        self.assertAlmostEqual(res["gross_price_eur"], round(res["unit_gross_eur"] * 2, 2), places=1)

    def test_gcode_layer_analyzer_and_demo_generator(self):
        demo = library.generate_demo_gcode_layers("Voron_Cube_v2.gcode")
        self.assertGreater(demo["total_layers"], 10)
        self.assertTrue(len(demo["layers"]) > 0)

        with tempfile.TemporaryDirectory() as tmp:
            gfile = Path(tmp) / "test_part.gcode"
            gfile.write_text(
                "G28\n"
                ";LAYER_CHANGE\n"
                "G1 Z0.20 F1200\n"
                "G1 X50 Y50 F6000\n"
                "G1 X100 Y50 E2.5 F2400\n"
                "G1 X100 Y100 E5.0 F2400\n"
                ";LAYER_CHANGE\n"
                "G1 Z0.40 F1200\n"
                "G1 X60 Y60 E7.5 F2400\n",
                encoding="utf-8",
            )
            parsed = library.analyze_gcode_layers(str(gfile))
            self.assertGreaterEqual(parsed["total_layers"], 1)
            self.assertGreater(len(parsed["layers"][0]["segments"]), 0)

    def test_http_server_endpoints(self):
        httpd, engine = server.create_http_server(port=0, host="127.0.0.1")
        port = httpd.server_port
        t = threading.Thread(target=httpd.serve_forever, daemon=True)
        t.start()
        base = f"http://127.0.0.1:{port}"
        try:
            # 1. GET / index.html and static assets
            with urllib.request.urlopen(f"{base}/", timeout=5) as r:
                html = r.read().decode("utf-8")
                self.assertIn("PrintBoard Studio", html)
            with urllib.request.urlopen(f"{base}/styles.css", timeout=5) as r:
                css = r.read().decode("utf-8")
                self.assertIn("--bg-root", css)
            with urllib.request.urlopen(f"{base}/app.js", timeout=5) as r:
                js = r.read().decode("utf-8")
                self.assertIn("drawGcodeLayerCanvas", js)

            # 2. GET /api/state
            with urllib.request.urlopen(f"{base}/api/state", timeout=5) as r:
                state = json.loads(r.read())
                self.assertIn("mode", state)
                self.assertIn("printers", state)
                self.assertIn("drying_presets", state)

            # 3. POST /api/mode (switch Easy / Advanced & Theme)
            req = urllib.request.Request(
                f"{base}/api/mode",
                data=json.dumps({"mode": "advanced", "theme": "carbon"}).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=5) as r:
                res = json.loads(r.read())
                self.assertTrue(res["ok"])
                self.assertEqual(res["state"]["mode"], "advanced")
                self.assertEqual(res["state"]["theme"], "carbon")

            # 4. POST /api/costs/quote
            req_q = urllib.request.Request(
                f"{base}/api/costs/quote",
                data=json.dumps({"grams": 85, "hours": 3.0, "copies": 3}).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req_q, timeout=5) as r:
                q_res = json.loads(r.read())
                self.assertTrue(q_res["ok"])
                self.assertEqual(q_res["quote"]["copies"], 3)

            # 5. GET /api/gcode/analyze
            with urllib.request.urlopen(f"{base}/api/gcode/analyze?filename=BenchTest.gcode", timeout=5) as r:
                g_res = json.loads(r.read())
                self.assertGreater(g_res["total_layers"], 5)
        finally:
            engine.running = False
            httpd.shutdown()
            httpd.server_close()


if __name__ == "__main__":
    unittest.main()
