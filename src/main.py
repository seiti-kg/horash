#!/usr/bin/env python3
"""
main.py - Entrypoint para File Hasher .exe (ClamAV+YARA sempre ativo)
- Inicia server.py em thread
- Abre navegador padrão em http://localhost:8765
- Ao fechar janela, encerra server e limpa

Uso dev: python main.py
Build: pyinstaller FileHasher.spec
"""
import os
import sys
import threading
import time
import webbrowser
import socketserver
import http.server

# Garante que diretorio do exe/script é o cwd
# src/ -> project_root = parent de src
if hasattr(sys, '_MEIPASS'):
    base = sys._MEIPASS
    os.chdir(base)
    # Em bundle, server é módulo coletado pelo PyInstaller (PYZ), não arquivo em disco
    try:
        import server as server_mod
    except ImportError:
        import importlib.util
        server_path = os.path.join(base, "server.py")
        spec = importlib.util.spec_from_file_location("server", server_path)
        server_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(server_mod)
else:
    src_dir = os.path.dirname(os.path.abspath(__file__))  # src/
    project_root = os.path.dirname(src_dir)  # root
    os.chdir(project_root)
    # garante que src/ está no path para imports internos
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)
    base = src_dir
    import importlib.util
    server_path = os.path.join(src_dir, "server.py")
    spec = importlib.util.spec_from_file_location("server", server_path)
    server_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(server_mod)

PORT = 8765

def start_server():
    handler = server_mod.Handler
    httpd = server_mod.ThreadedTCPServer(("", PORT), handler)
    print(f"[*] File Hasher .exe - Servidor em http://localhost:{PORT}")
    try:
        info = server_mod.check_scanners()
        print(f"[*] ClamAV: {'OK' if info.get('clamav_available') else 'OFF'} - {info.get('clamav_path') or 'nao encontrado'}")
        print(f"[*] YARA: {'OK' if info.get('yara_available') else 'OFF'} - {info.get('yara_path') or 'nao encontrado'}")
    except Exception as e:
        print(f"[*] Scanner check: {e}")
    print("[*] Abrindo navegador...")
    # abre navegador apos 1s
    def open_browser():
        time.sleep(1.2)
        try:
            webbrowser.open(f"http://localhost:{PORT}")
            print("[*] Navegador aberto. Feche esta janela para encerrar.")
        except Exception as e:
            print(f"[!] Falha ao abrir navegador: {e}")
            print(f"    Abra manualmente http://localhost:{PORT}")
    threading.Thread(target=open_browser, daemon=True).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Encerrando...")
        httpd.shutdown()

if __name__ == "__main__":
    # Se rodar como .exe sem console, ainda mostra prints no log
    # Tenta abrir porta, se já em uso avisa
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("", PORT))
        s.close()
    except OSError:
        print(f"[!] Porta {PORT} já em uso. Tentando abrir navegador apenas...")
        webbrowser.open(f"http://localhost:{PORT}")
        sys.exit(0)
    start_server()
