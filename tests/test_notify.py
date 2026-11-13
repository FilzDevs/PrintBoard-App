import json
import unittest
from unittest.mock import patch, MagicMock
from printboard import notify


class TestNotify(unittest.TestCase):
    def test_send_discord_empty_url(self):
        with self.assertRaises(ValueError):
            notify.send_discord("")

    @patch("printboard.notify.urlopen")
    def test_send_discord_success(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.status = 204
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        res = notify.send_discord("https://discord.com/api/webhooks/123/xyz", "Test text")
        self.assertTrue(res)
        self.assertTrue(mock_urlopen.called)

        req = mock_urlopen.call_args[0][0]
        self.assertEqual(req.full_url, "https://discord.com/api/webhooks/123/xyz")
        data = json.loads(req.data.decode("utf-8"))
        self.assertEqual(data["content"], "Test text")

    @patch("printboard.notify.urlopen")
    def test_send_discord_error_status(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.status = 400
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        with self.assertRaises(RuntimeError):
            notify.send_discord("https://discord.com/api/webhooks/123/xyz")


if __name__ == "__main__":
    unittest.main()
