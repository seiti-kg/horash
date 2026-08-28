#!/usr/bin/env python3
# vt_incognito.py - Abre URL do VirusTotal direto em aba anonima/privada
# Uso: python vt_incognito.py <hash_ou_url>
#      python vt_incognito.py e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
import sys
import os
import shutil
import subprocess
import platform

try:
    import winreg
except ImportError:
    winreg = None

VT_URL = "https://www.virustotal.com/gui/file/{hash}"

def normalize_input(arg: str) -> str:
    arg = arg.strip()
    if arg.startswith("http"):
        return arg
    # bloqueia teste/invalido
    if arg == "test" or len(arg) < 10:
        raise ValueError(f"hash invalido/teste ignorado: {arg}")
    if len(arg) == 64 and all(c in "0123456789abcdefABCDEF" for c in arg):
        return VT_URL.format(hash=arg.lower())
    # se nao for sha256 valido, assume que ja e URL ou retorna como esta mas valida
    if len(arg) != 64:
        raise ValueError(f"hash deve ter 64 hex (SHA256), recebido: {arg}")
    return arg

def find_chrome_path():
    candidates = [
        os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ]
    for p in candidates:
        if os.path.isfile(p):
            return p
    # tenta via registry
    if winreg:
        for key_path in [r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe",
                         r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe"]:
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as k:
                    val, _ = winreg.QueryValueEx(k, "")
                    if os.path.isfile(val):
                        return val
            except OSError:
                pass
    # tenta via PATH
    which = shutil.which("chrome") or shutil.which("chrome.exe") or shutil.which("google-chrome")
    if which:
        return which
    return None

def find_edge_path():
    candidates = [
        os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
    ]
    for p in candidates:
        if os.path.isfile(p):
            return p
    which = shutil.which("msedge") or shutil.which("msedge.exe")
    if which:
        return which
    return None

def find_firefox_path():
    candidates = [
        os.path.expandvars(r"%ProgramFiles%\Mozilla Firefox\firefox.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Mozilla Firefox\firefox.exe"),
    ]
    for p in candidates:
        if os.path.isfile(p):
            return p
    which = shutil.which("firefox") or shutil.which("firefox.exe")
    if which:
        return which
    return None

def open_incognito(url: str) -> bool:
    url = normalize_input(url)
    print(f"[vt_incognito] Abrindo: {url}")

    # 1. Tenta Chrome --incognito
    chrome = find_chrome_path()
    if chrome:
        try:
            print(f"[vt_incognito] Usando Chrome: {chrome}")
            subprocess.Popen([chrome, "--incognito", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception as e:
            print(f"Falha Chrome: {e}")

    # 2. Tenta Edge --inprivate
    edge = find_edge_path()
    if edge:
        try:
            print(f"[vt_incognito] Usando Edge: {edge}")
            subprocess.Popen([edge, "--inprivate", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception as e:
            print(f"Falha Edge: {e}")

    # 3. Tenta Firefox --private-window
    firefox = find_firefox_path()
    if firefox:
        try:
            print(f"[vt_incognito] Usando Firefox: {firefox}")
            subprocess.Popen([firefox, "--private-window", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception as e:
            print(f"Falha Firefox: {e}")

    # 4. Fallback: tenta via start (usa navegador padrao mas sem flag - melhor que nada)
    try:
        if platform.system() == "Windows":
            # start chrome --incognito funciona se chrome for padrao ou estiver no PATH
            subprocess.Popen(f'start "" chrome --incognito "{url}"', shell=True)
            return True
    except Exception as e:
        print(f"Fallback falhou: {e}")

    print("[vt_incognito] Nenhum navegador com modo anonimo encontrado. Abrindo normal...")
    import webbrowser
    webbrowser.open(url)
    return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python vt_incognito.py <hash_sha256_ou_url>")
        print("Ex:  python vt_incognito.py e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")
        sys.exit(1)
    arg = sys.argv[1]
    ok = open_incognito(arg)
    sys.exit(0 if ok else 2)
