#!/usr/bin/env python3
"""
server.py - Servidor local do horash (hash + VirusTotal + ClamAV/YARA)

Roda em http://localhost:8765, SOMENTE em loopback.
- Serve a UI em web/
- /open?hash=<sha256> abre o VirusTotal em aba anonima via vt_incognito.py
- /scan recebe bytes, grava temp, roda ClamAV/YARA e apaga o temp

Nada e persistido: o arquivo temporario e removido ao fim do scan.
"""
import http.server
import socketserver
import urllib.parse
import os
import sys
import json
import tempfile
import time

try:
    from scanner import check_scanners, scan_file
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        from scanner import check_scanners, scan_file
    except Exception:
        check_scanners = lambda: {"clamav_available": False, "yara_available": False}
        scan_file = lambda _path: {"error": "scanner.py nao encontrado", "complete": False}

try:
    from vt_incognito import open_incognito
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from vt_incognito import open_incognito

try:
    from version import __version__ as VERSION
except ImportError:
    VERSION = "dev"

PORT = 8765
HOST = "127.0.0.1"
MAX_UPLOAD_BYTES = 10 * 1024 * 1024 * 1024
ALLOWED_HOSTNAMES = frozenset({"localhost", "127.0.0.1", "::1"})


def is_sha256(value):
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(c in "0123456789abcdefABCDEF" for c in value)
    )


def _hostname(authority):
    """Extrai o hostname de um header Host/Origin sem confiar no valor."""
    if not authority:
        return None
    try:
        parsed = urllib.parse.urlsplit("//" + authority)
        return (parsed.hostname or "").lower() or None
    except ValueError:
        return None


def _origin_allowed(origin):
    if not origin or origin == "null":
        return False
    try:
        parsed = urllib.parse.urlsplit(origin)
    except ValueError:
        return False
    if parsed.scheme not in ("http", "https"):
        return False
    return (parsed.hostname or "").lower() in ALLOWED_HOSTNAMES


# encontra web dir que contem index.html (robusto para install, dev e bundle)
def _find_web_dir():
    candidates = []
    if hasattr(sys, "_MEIPASS"):
        candidates.append(sys._MEIPASS)
        candidates.append(os.path.join(sys._MEIPASS, "web"))
    try:
        candidates.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "web"))
        candidates.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    except Exception:
        pass
    try:
        candidates.append(os.path.join(os.getcwd(), "web"))
        candidates.append(os.getcwd())
    except Exception:
        pass
    try:
        exe_dir = os.path.dirname(os.path.abspath(sys.executable)) if hasattr(sys, "executable") else None
        if exe_dir:
            candidates.append(os.path.join(exe_dir, "web"))
            candidates.append(exe_dir)
    except Exception:
        pass
    for c in candidates:
        if not c:
            continue
        c = os.path.abspath(c)
        if os.path.isfile(os.path.join(c, "index.html")):
            return c
    for c in candidates:
        if c and os.path.isdir(os.path.join(c, "web")) and os.path.isfile(os.path.join(c, "web", "index.html")):
            return os.path.join(c, "web")
    if hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS
    _src_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(os.path.dirname(_src_dir), "web")


DIRECTORY = _find_web_dir()
try:
    print(f"[*] web dir: {DIRECTORY} (index exists={os.path.isfile(os.path.join(DIRECTORY, 'index.html'))})")
except Exception:
    pass


class Handler(http.server.SimpleHTTPRequestHandler):
    server_version = "horash/" + VERSION

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    # -- defesas de origem ------------------------------------------------
    def _request_allowed(self):
        """Aceita apenas requests locais (Host) e nao cross-site (Origin/Sec-Fetch-Site)."""
        host = self.headers.get("Host")
        if host and _hostname(host) not in ALLOWED_HOSTNAMES:
            return False
        origin = self.headers.get("Origin")
        if origin and not _origin_allowed(origin):
            return False
        site = (self.headers.get("Sec-Fetch-Site") or "").lower()
        if site in ("cross-site", "same-site"):
            return False
        return True

    def _send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _forbidden(self):
        self._send_json(403, {"error": "origem nao permitida"})

    # -- HTTP -------------------------------------------------------------
    def do_GET(self):
        if not self._request_allowed():
            self._forbidden()
            return

        parsed = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed.query)

        if parsed.path == "/ping":
            self._send_json(200, {"status": "ok", "server": "horash", "version": VERSION})
            return

        if parsed.path == "/health/scan":
            self._send_json(200, check_scanners())
            return

        if parsed.path == "/vt-scrape":
            hash_val = query.get("hash", [None])[0]
            if not is_sha256(hash_val):
                self._send_json(400, {"error": "hash sha256 (64 hex) obrigatorio"})
                return
            try:
                from vt_scrape import scrape_vt
                print(f"[vt-scrape] {hash_val} via Playwright...")
                result = scrape_vt(hash_val, timeout_ms=25000, headless=True)
                self._send_json(200 if result.get("available") or "stats" in result else 502, result)
            except Exception as e:
                print(f"[vt-scrape] erro: {e}")
                self._send_json(500, {"error": str(e), "available": False})
            return

        if parsed.path == "/open":
            hash_val = query.get("hash", [None])[0]
            if not is_sha256(hash_val):
                print(f"[server] hash invalido ignorado: {hash_val!r}")
                self._send_json(400, {"error": "hash sha256 (64 hex) obrigatorio", "ignored": True})
                return
            print(f"[server] abrindo VT anonimo: {hash_val}")
            try:
                ok = open_incognito(hash_val)
                self._send_json(200, {"status": "ok incognito" if ok else "fallback normal", "hash": hash_val})
            except Exception as e:
                print(f"[server] erro: {e}")
                self._send_json(500, {"error": str(e)})
            return

        if parsed.path in ("/", ""):
            index_path = os.path.join(DIRECTORY, "index.html")
            if os.path.isfile(index_path):
                self.path = "/index.html"
        return super().do_GET()

    def do_POST(self):
        if not self._request_allowed():
            self._forbidden()
            return

        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != "/scan":
            self._send_json(404, {"error": "not found"})
            return

        raw_name = self.headers.get("X-Filename", "upload.bin")
        try:
            filename = urllib.parse.unquote(raw_name)
        except Exception:
            filename = raw_name
        filename = os.path.basename(filename.replace("\\", "/")) or "upload.bin"
        filename = filename[:255]

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._send_json(400, {"error": "content-length invalido"})
            return
        if content_length <= 0:
            self._send_json(400, {"error": "arquivo vazio"})
            return
        if content_length > MAX_UPLOAD_BYTES:
            self._send_json(413, {"error": "arquivo acima de 10GB"})
            return

        tmp = None
        t0 = time.time()
        try:
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".bin")
            remaining = content_length
            while remaining > 0:
                chunk_size = min(4 * 1024 * 1024, remaining)
                data = self.rfile.read(chunk_size)
                if not data:
                    break
                tmp.write(data)
                remaining -= len(data)

            if remaining > 0:
                tmp.close()
                print(f"[scan] upload incompleto: faltaram {remaining} bytes de {filename}")
                self._send_json(400, {"error": "upload incompleto", "missing_bytes": remaining})
                return

            tmp.close()
            upload_time = time.time() - t0
            print(f"[scan] recebido {filename} ({content_length} bytes) em {upload_time:.2f}s -> {tmp.name}")

            t_scan_start = time.time()
            result = scan_file(tmp.name)
            scan_time = time.time() - t_scan_start

            result["filename"] = filename
            result["size"] = content_length
            result["upload_time_ms"] = int(upload_time * 1000)
            result["scan_time_ms"] = int(scan_time * 1000)
            result["total_time_ms"] = int((time.time() - t0) * 1000)
            print(
                f"[scan] {filename} -> {'INFECTADO' if result.get('infected') else 'LIMPO'}"
                f"{'' if result.get('complete') else ' (parcial)'} em {scan_time:.2f}s"
            )
            self._send_json(200, result)
        except Exception as e:
            print(f"[scan] erro: {e}")
            self._send_json(500, {"error": str(e)})
        finally:
            if tmp and os.path.exists(tmp.name):
                try:
                    os.unlink(tmp.name)
                    print(f"[scan] temp deletado {tmp.name}")
                except Exception:
                    pass

    def end_headers(self):
        # CORS somente para origens locais (a UI roda na mesma origem e nao precisa).
        origin = self.headers.get("Origin")
        if origin and _origin_allowed(origin):
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Filename")
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        self.send_header("Pragma", "no-cache")
        super().end_headers()

    def do_OPTIONS(self):
        if not self._request_allowed():
            self._forbidden()
            return
        self.send_response(204)
        self.end_headers()


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == "__main__":
    os.chdir(DIRECTORY)
    try:
        info = check_scanners()
        print(f"[*] ClamAV: {info.get('clamav_path') or 'NAO ENCONTRADO'} -> {'OK' if info.get('clamav_available') else 'FALTA (rode tools/install_clamav.ps1)'}")
        print(f"[*] YARA: {info.get('yara_path') or 'NAO ENCONTRADO'} -> {'OK' if info.get('yara_available') else 'FALTA'}")
        if info.get("yara_rules"):
            print(f"[*] YARA rules: {info.get('yara_rules')} OK")
        else:
            print("[*] YARA rules: NAO ENCONTRADAS (rode tools/install_yara.ps1)")
    except Exception as e:
        print(f"[*] scanner check falhou: {e}")
    with ThreadedTCPServer((HOST, PORT), Handler) as httpd:
        print(f"[*] horash {VERSION} rodando em http://localhost:{PORT} (loopback)")
        print(f"[*] pasta: {DIRECTORY}")
        print("[*] endpoints: /ping /health/scan /open?hash= /vt-scrape?hash= /scan (POST)")
        print("[*] deixe esta janela aberta; Ctrl+C para parar.")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[*] encerrado.")
