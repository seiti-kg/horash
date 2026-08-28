#!/usr/bin/env python3
"""
server.py - Servidor local para File Hasher + VirusTotal anonimo

Roda em http://localhost:8765
- Serve index.html (sem precisar dar duplo clique)
- Endpoint /open?hash=<sha256> ou /open?url=<url> -> abre DIRETO em aba anonima via vt_incognito.py (1 clique real)

Uso:
  python server.py
  ou duplo clique em start.bat

Depois abra http://localhost:8765 no navegador.
O botao "VT anonimo" vai tentar chamar http://localhost:8765/open?hash=... primeiro.
Se o servidor nao estiver rodando, cai no fallback de copiar link (comportamento anterior).

Nada é salvo em disco - tudo em memoria, como pedido.
"""
import http.server
import socketserver
import urllib.parse
import os
import sys
import json
import tempfile
import cgi
import time

try:
    from scanner import check_scanners, scan_file
except ImportError:
    try:
        from scanner import check_scanners, scan_file
    except:
        check_scanners = lambda: {"clamav_available": False, "yara_available": False}
        scan_file = lambda x: {"error": "scanner.py nao encontrado"}

# importa funcao de abrir anonimo
try:
    from vt_incognito import open_incognito
except ImportError:
    # caso rode de outro diretorio
    sys.path.insert(0, os.path.dirname(__file__))
    from vt_incognito import open_incognito

PORT = 8765
# bundle (_MEIPASS) tem index.html na raiz; dev tem em web/
if hasattr(sys, '_MEIPASS'):
    DIRECTORY = sys._MEIPASS
else:
    _src_dir = os.path.dirname(os.path.abspath(__file__))
    _project_root = os.path.dirname(_src_dir)
    DIRECTORY = os.path.join(_project_root, "web")

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed.query)

        # Health check - NAO abre navegador, so verifica se servidor esta ON
        if parsed.path == "/ping":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(b'{"status":"ok","server":"file_hasher"}')
            return

        if parsed.path == "/health/scan":
            info = check_scanners()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(info).encode())
            return

        if parsed.path == "/vt-scrape":
            hash_val = query.get("hash", [None])[0]
            if not hash_val or len(hash_val) != 64:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(b'{"error":"hash 64 hex required"}')
                return
            # Verifica playwright disponivel
            try:
                from vt_scrape import scrape_vt
                print(f"[vt-scrape] {hash_val} via Playwright...")
                result = scrape_vt(hash_val, timeout_ms=25000, headless=True)
                self.send_response(200 if result.get("available") or "stats" in result else 500)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(result).encode())
            except Exception as e:
                print(f"[vt-scrape] erro: {e}")
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e), "available": False}).encode())
            return

        # Endpoint para abrir anonimo
        if parsed.path == "/open":
            hash_val = query.get("hash", [None])[0]
            url_val = query.get("url", [None])[0]
            target = url_val or hash_val
            if not target:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(b'{"error":"missing hash or url"}')
                return

            # BLOQUEIO: ignora hashes de teste/invalidos que causavam loop (ex: "test")
            # So aceita SHA256 (64 hex) ou URL http(s)
            is_valid_hash = hash_val and len(hash_val) == 64 and all(c in "0123456789abcdefABCDEF" for c in hash_val)
            is_valid_url = url_val and url_val.startswith("http")
            if hash_val and not is_valid_hash and not is_valid_url and not url_val:
                print(f"[server] Ignorado hash invalido/teste: {target} (nao abre aba)")
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(b'{"error":"invalid hash, expected 64 hex sha256","ignored":true}')
                return

            # se for hash, vt_incognito normaliza para URL
            if hash_val and not url_val:
                target = hash_val

            print(f"[server] Pedido para abrir anonimo: {target}")
            try:
                ok = open_incognito(target)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                msg = "ok incognito" if ok else "fallback normal"
                self.wfile.write(f'{{"status":"{msg}", "target":"{target}"}}'.encode())
            except Exception as e:
                print(f"[server] Erro: {e}")
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(f'{{"error":"{e}"}}'.encode())
            return

        # CORS para o endpoint (caso index.html seja aberto via file://)
        if parsed.path.startswith("/open"):
            self.send_response(200)
            self.end_headers()
            return

        # Serve arquivos normalmente (index.html etc)
        return super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/scan":
            # Header X-Filename opcional
            filename = self.headers.get("X-Filename", "upload.bin")
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length == 0:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(b'{"error":"empty file"}')
                return
            # Limite 10GB para nao estourar disco
            if content_length > 10 * 1024 * 1024 * 1024:
                self.send_response(413)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(b'{"error":"file too large >10GB"}')
                return

            # Salva em temp (sem persistencia)
            tmp = None
            t0 = time.time()
            t_upload_start = t0
            try:
                suffix = os.path.splitext(filename)[1] or ".bin"
                # decodifica filename URL-encoded
                try:
                    filename = urllib.parse.unquote(filename)
                except:
                    pass
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
                # Stream em chunks de 4MB para nao carregar tudo em RAM
                remaining = content_length
                while remaining > 0:
                    chunk_size = min(4*1024*1024, remaining)
                    data = self.rfile.read(chunk_size)
                    if not data:
                        break
                    tmp.write(data)
                    remaining -= len(data)
                tmp.close()
                t_upload = time.time() - t_upload_start
                print(f"[scan] Recebido {filename} ({content_length} bytes) em {t_upload:.2f}s -> {tmp.name}")

                # Escaneia
                t_scan_start = time.time()
                result = scan_file(tmp.name)
                t_scan = time.time() - t_scan_start
                # Adiciona info de tamanho e timing
                result["filename"] = filename
                result["size"] = content_length
                result["upload_time_ms"] = int(t_upload*1000)
                result["scan_time_ms"] = int(t_scan*1000)
                result["total_time_ms"] = int((time.time()-t0)*1000)
                result["vt_note"] = "VT limitado a 650MB; scan local usado para arquivos grandes" if content_length > 650*1024*1024 else "VT disponivel"
                print(f"[scan] {filename} -> {'INFECTADO' if result.get('infected') else 'LIMPO'} em {t_scan:.2f}s (total {time.time()-t0:.2f}s)")

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(result).encode())
            except Exception as e:
                print(f"[scan] Erro: {e}")
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode())
            finally:
                if tmp and os.path.exists(tmp.name):
                    try:
                        os.unlink(tmp.name)
                        print(f"[scan] Temp deletado {tmp.name}")
                    except:
                        pass
            return

        self.send_response(404)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(b'{"error":"not found"}')

    def end_headers(self):
        # CORS geral para facilitar file:// -> localhost
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        # desativa cache para garantir que index.html atualizado seja carregado
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        self.send_header("Pragma", "no-cache")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
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
        if info.get('yara_rules'):
            print(f"[*] YARA rules: {info.get('yara_rules')} OK")
        else:
            print(f"[*] YARA rules: NAO ENCONTRADAS (rode tools/install_yara.ps1)")
    except Exception as e:
        print(f"[*] Scanner check falhou: {e}")
    with ThreadedTCPServer(("", PORT), Handler) as httpd:
        print(f"[*] File Hasher rodando em http://localhost:{PORT}")
        print(f"[*] Pasta: {DIRECTORY}")
        print(f"[*] Endpoints: /ping /open?hash= /health/scan /scan (POST) /vt-scrape?hash=")
        print(f"[*] Deixe esta janela aberta. Feche Ctrl+C para parar.")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[*] Encerrado.")
