import unittest
from unittest.mock import MagicMock
from printboard import bambu, store

class TestBambuIntegration(unittest.TestCase):
    def test_bambu_state_normalization(self):
        st = bambu.BambuPrinterState(online=True, gcode_state="RUNNING", mc_percent=42)
        self.assertEqual(st.normalized_state(), "printing")
        st.gcode_state = "PAUSE"
        self.assertEqual(st.normalized_state(), "paused")
        st.gcode_state = "FINISH"
        self.assertEqual(st.normalized_state(), "complete")
        st.gcode_state = "FAILED"
        self.assertEqual(st.normalized_state(), "error")

    def test_fetch_bambu_offline(self):
        p = store.Printer(
            name="X1C",
            host="192.168.178.99",
            printer_type="bambu",
            bambu_serial="01P00A123456789",
            bambu_access_code="12345678"
        )
        res = bambu.fetch_bambu_status(p)
        self.assertTrue(res.get("is_bambu"))
        self.assertIn("temps", res)
        self.assertEqual(res.get("state"), "offline")


if __name__ == "__main__":
    unittest.main()
