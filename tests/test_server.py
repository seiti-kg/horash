import http.client
import json
import socket
import sys
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

import server  # noqa: E402

server.Handler.log_message = lambda *args, **kwargs: None

SCAN_OK = {
    "infected": False,
    "signatures": [],
    "clamav": {"status": "clean"},
    "yara": {"status": "clean"},
    "complete": True,
    "warnings": [],
    "summary": "Limpo",
}
VALID_HASH = "a" * 64


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd = server.ThreadedTCPServer(("127.0.0.1", 0), server.Handler)
        cls.port = cls.httpd.server_address[1]
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.thread.join(timeout=5)

    def request(self, method, path, headers=None, body=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        try:
            conn.request(method, path, body=body, headers=headers or {})
            response = conn.getresponse()
            return response.status, response.read()
        finally:
            conn.close()

    def test_ping(self):
        status, body = self.request("GET", "/ping")
        self.assertEqual(status, 200)
        payload = json.loads(body)
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["server"], "horash")

    def test_index_is_served(self):
        status, body = self.request("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn(b"<title>Horash</title>", body)

    def test_non_local_host_is_rejected(self):
        status, _ = self.request("GET", "/ping", headers={"Host": "evil.example"})
        self.assertEqual(status, 403)

    def test_cross_site_origin_is_rejected(self):
        status, _ = self.request(
            "POST",
            "/scan",
            headers={"Origin": "http://evil.example", "Content-Length": "3"},
            body=b"abc",
        )
        self.assertEqual(status, 403)

    def test_cross_site_fetch_metadata_is_rejected(self):
        status, _ = self.request("GET", "/ping", headers={"Sec-Fetch-Site": "cross-site"})
        self.assertEqual(status, 403)

    def test_same_origin_scan_returns_contract(self):
        origin = f"http://127.0.0.1:{self.port}"
        with patch.object(server, "scan_file", return_value=dict(SCAN_OK)):
            status, body = self.request(
                "POST",
                "/scan",
                headers={"Origin": origin, "X-Filename": "teste.bin", "Content-Length": "3"},
                body=b"abc",
            )
        self.assertEqual(status, 200)
        payload = json.loads(body)
        self.assertTrue(payload["complete"])
        self.assertEqual(payload["filename"], "teste.bin")

    def test_empty_upload_is_rejected(self):
        status, _ = self.request("POST", "/scan", headers={"Content-Length": "0"}, body=b"")
        self.assertEqual(status, 400)

    def test_truncated_upload_is_rejected(self):
        with socket.create_connection(("127.0.0.1", self.port), timeout=10) as sock:
            sock.sendall(
                b"POST /scan HTTP/1.1\r\n"
                b"Host: 127.0.0.1\r\n"
                b"Content-Length: 100\r\n"
                b"Content-Type: application/octet-stream\r\n"
                b"\r\n"
                b"abc"
            )
            sock.shutdown(socket.SHUT_WR)
            response = b""
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response += chunk
        self.assertIn(b"400", response.split(b"\r\n", 1)[0])
        self.assertIn(b"upload incompleto", response)

    def test_open_rejects_url_parameter(self):
        status, _ = self.request("GET", "/open?url=http%3A%2F%2Fevil.example")
        self.assertEqual(status, 400)

    def test_open_rejects_invalid_hash(self):
        status, _ = self.request("GET", "/open?hash=zzz")
        self.assertEqual(status, 400)

    def test_open_valid_hash_uses_incognito(self):
        with patch.object(server, "open_incognito", return_value=True) as opener:
            status, body = self.request("GET", f"/open?hash={VALID_HASH}")
        self.assertEqual(status, 200)
        opener.assert_called_once_with(VALID_HASH)
        self.assertEqual(json.loads(body)["hash"], VALID_HASH)

    def test_vt_scrape_rejects_invalid_hash_before_playwright(self):
        status, _ = self.request("GET", "/vt-scrape?hash=zzz")
        self.assertEqual(status, 400)

    def test_unknown_post_is_404(self):
        status, _ = self.request("POST", "/nope", headers={"Content-Length": "0"}, body=b"")
        self.assertEqual(status, 404)


if __name__ == "__main__":
    unittest.main()
