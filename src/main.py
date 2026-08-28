#!/usr/bin/env python3
"""
main.py - entrypoint horash app (pywebview + fallback browser)
- sobe server.py em thread em http://localhost:8765
- tenta abrir janela nativa pywebview (WebView2), fallback para navegador
- uso dev: python src/main.py
- build: pyinstaller horash.spec
"""
import os
import sys
import threading
import time
import webbrowser
import socket

# garante que diretorio do exe/script e o cwd
if hasattr(sys, '_MEIPASS'):
    base = sys._MEIPASS
    os.chdir(base)
    try:
        import server as server_mod
    except ImportError:
        import importlib.util
        server_path = os.path.join(base, "server.py")
        spec = importlib.util.spec_from_file_location("server", server_path)
        server_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(server_mod)
else:
    src_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(src_dir)
    os.chdir(project_root)
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)
    base = src_dir
    import importlib.util
    server_path = os.path.join(src_dir, "server.py")
    spec = importlib.util.spec_from_file_location("server", server_path)
    server_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(server_mod)

PORT = 8765

def is_port_in_use(port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("", port))
        s.close()
        return False
    except OSError:
        return True

def wait_server(host="127.0.0.1", port=PORT, timeout=10):
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return True
        except:
            time.sleep(0.15)
    return False

def start_server_blocking():
    handler = server_mod.Handler
    httpd = server_mod.ThreadedTCPServer(("", PORT), handler)
    print(f"[*] horash - servidor em http://localhost:{PORT}")
    try:
        info = server_mod.check_scanners()
        print(f"[*] clamav: {'ok' if info.get('clamav_available') else 'off'} - {info.get('clamav_path') or 'nao encontrado'}")
        print(f"[*] yara: {'ok' if info.get('yara_available') else 'off'} - {info.get('yara_path') or 'nao encontrado'}")
    except Exception as e:
        print(f"[*] scanner check: {e}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] encerrando...")
        httpd.shutdown()

if __name__ == "__main__":
    if is_port_in_use(PORT):
        print(f"[!] porta {PORT} ja em uso, abrindo navegador...")
        try:
            webbrowser.open(f"http://localhost:{PORT}")
        except:
            pass
        sys.exit(0)

    # sobe server em thread daemon
    t = threading.Thread(target=start_server_blocking, daemon=True)
    t.start()

    if not wait_server():
        print("[!] falha ao subir servidor")
        sys.exit(1)

    url = f"http://localhost:{PORT}"
    # tenta pywebview (janela nativa)
    try:
        import webview
        print("[*] abrindo janela nativa (pywebview/WebView2)...")
        # webview precisa estar no main thread
        window = webview.create_window(
            "horash",
            url,
            width=1120,
            height=760,
            min_size=(900, 600),
            text_select=True,
            zoomable=True,
        )
        # sem console, sem menu extra
        webview.start()
        print("[*] janela fechada, encerrando...")
        os._exit(0)
    except Exception as e:
        print(f"[!] pywebview falhou ({e}), fallback navegador")
        print(f"[*] abrindo {url} no navegador...")
        try:
            webbrowser.open(url)
            print("[*] navegador aberto. feche esta janela para encerrar. ctrl+c para parar.")
        except Exception as e2:
            print(f"[!] falha navegador: {e2}")
            print(f"    abra manualmente {url}")
        # mantem server vivo no main thread
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[*] encerrando...")
            os._exit(0)
