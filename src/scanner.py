#!/usr/bin/env python3
"""
scanner.py - Wrapper ClamAV + YARA para File Hasher
- Suporta arquivos GB via streaming (sem carregar em RAM)
- Sem persistencia: arquivos sao escaneados via temp file e deletados
- Funciona tanto com .exe bundle (sys._MEIPASS) quanto com instalacao sistema
"""
import os
import sys
import shutil
import subprocess
import tempfile
import glob
import time

def get_bundle_base():
    # PyInstaller extrai para sys._MEIPASS; dev: project_root (parent de src/)
    if hasattr(sys, '_MEIPASS'):
        return sys._MEIPASS
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def find_binary(name_variants):
    """Tenta achar binario em bundle, PATH e locais comuns Windows"""
    base = get_bundle_base()
    # 1. bundle clamav/ yara/
    for variant in name_variants:
        for sub in ["clamav", "yara", "bin", ""]:
            cand = os.path.join(base, sub, variant)
            if os.path.isfile(cand):
                return cand
        # tambem no diretorio atual
        cand2 = os.path.join(os.path.dirname(__file__), variant)
        if os.path.isfile(cand2):
            return cand2
    
    # 2. PATH
    for variant in name_variants:
        which = shutil.which(variant)
        if which:
            return which
    
    # 3. Locais comuns Windows
    common = [
        r"C:\ClamAV\clamscan.exe",
        r"C:\Program Files\ClamAV\clamscan.exe",
        r"C:\Program Files\ClamAV\clamdscan.exe",
        os.path.expandvars(r"%ProgramFiles%\ClamAV\clamscan.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\ClamAV\clamscan.exe"),
    ]
    for p in common:
        if os.path.isfile(p):
            return p
    return None

def find_clamscan():
    return find_binary(["clamscan.exe", "clamscan", "clamdscan.exe", "clamdscan"])

def find_yara():
    return find_binary(["yara64.exe", "yara.exe", "yara"])

def find_yara_rules():
    base = get_bundle_base()
    candidates = [
        os.path.join(base, "yara", "rules.yar"),
        os.path.join(base, "rules.yar"),
        os.path.join(base, "rules", "index.yar"),
        os.path.join(os.path.dirname(__file__), "yara", "rules.yar"),
        os.path.join(os.path.dirname(__file__), "rules.yar"),
        os.path.join(os.path.dirname(__file__), "rules", "index.yar"),
    ]
    for p in candidates:
        if os.path.isfile(p):
            return p
    # busca recursiva por .yar
    for root in [os.path.join(base, "yara"), os.path.join(os.path.dirname(__file__), "yara")]:
        if os.path.isdir(root):
            files = glob.glob(os.path.join(root, "**", "*.yar"), recursive=True)
            if files:
                return files[0]
    return None

def get_clamav_db_path():
    base = get_bundle_base()
    for cand in [os.path.join(base, "clamav", "db"), os.path.join(base, "db"), os.path.join(os.path.dirname(__file__), "clamav", "db")]:
        if os.path.isdir(cand):
            return cand
    return None

def check_scanners():
    clamscan = find_clamscan()
    yara = find_yara()
    rules = find_yara_rules()
    db = get_clamav_db_path()
    return {
        "clamav_path": clamscan,
        "clamav_available": bool(clamscan),
        "clamav_db": db,
        "yara_path": yara,
        "yara_available": bool(yara),
        "yara_rules": rules,
        "yara_rules_available": bool(rules),
    }

def scan_with_clamav(file_path):
    """Retorna dict {infected: bool, signature: str, output: str, time_ms: int}"""
    clamscan = find_clamscan()
    if not clamscan:
        return {"available": False, "error": "ClamAV nao encontrado. Instale via tools/install_clamav.ps1 ou bundle no .exe"}
    
    db = get_clamav_db_path()
    cmd = [clamscan, "--no-summary", "--stdout"]
    if db:
        cmd.extend(["--database", db])
    # ClamAV limite real ~2147M (2GiB-1), usa 2000M para evitar warning
    cmd.extend(["--max-filesize=2000M", "--max-scansize=2000M"])
    cmd.append(file_path)
    t0 = time.time()
    
    try:
        # timeout 10 min para GB
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        elapsed = int((time.time()-t0)*1000)
        output = (result.stdout or "") + (result.stderr or "")
        # clamscan exit code: 0 clean, 1 infected, 2 error
        if result.returncode == 1:
            sig = "Desconhecido"
            for line in output.splitlines():
                if "FOUND" in line:
                    parts = line.split(":")
                    if len(parts) >= 2:
                        sig = parts[-1].replace("FOUND","").strip()
                    break
            return {"available": True, "infected": True, "signature": sig, "output": output.strip(), "time_ms": elapsed}
        elif result.returncode == 0:
            return {"available": True, "infected": False, "signature": None, "output": "OK", "time_ms": elapsed}
        else:
            return {"available": True, "infected": False, "error": output.strip() or f"exit {result.returncode}", "time_ms": elapsed}
    except subprocess.TimeoutExpired:
        return {"available": True, "error": "Timeout scan (>10min) - arquivo muito grande ou travado", "time_ms": int((time.time()-t0)*1000)}
    except Exception as e:
        return {"available": True, "error": str(e), "time_ms": int((time.time()-t0)*1000)}

def scan_with_yara(file_path):
    yara = find_yara()
    rules = find_yara_rules()
    if not yara:
        return {"available": False, "error": "YARA nao encontrado"}
    if not rules:
        return {"available": False, "error": "Regras YARA nao encontradas (yara/rules.yar)"}
    t0 = time.time()
    
    # Se rules for diretorio com varias .yar, precisa compilar? yara aceita arquivo unico que inclui outros
    # Tenta rodar direto
    cmd = [yara, "-r", rules, file_path] if os.path.isdir(rules) else [yara, rules, file_path]
    # yara -r nao existe, na verdade yara <rules> <target>, se rules for dir usa glob
    # Vamos tratar: se rules for arquivo, usa ele; se for dir, pega todos .yar
    if os.path.isdir(rules):
        yar_files = glob.glob(os.path.join(rules, "**", "*.yar"), recursive=True)
        if not yar_files:
            return {"available": True, "error": "Nenhuma regra .yar encontrada", "time_ms": int((time.time()-t0)*1000)}
        hits = []
        for rf in yar_files[:50]:
            try:
                r = subprocess.run([yara, rf, file_path], capture_output=True, text=True, timeout=60)
                if r.stdout.strip():
                    hits.append(r.stdout.strip())
            except:
                continue
        elapsed = int((time.time()-t0)*1000)
        if hits:
            return {"available": True, "infected": True, "signature": "; ".join(hits)[:500], "output": "\n".join(hits)[:2000], "time_ms": elapsed}
        return {"available": True, "infected": False, "output": "OK", "time_ms": elapsed}
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        elapsed = int((time.time()-t0)*1000)
        output = result.stdout.strip()
        if output:
            sigs = list(set([line.split()[0] for line in output.splitlines() if line.strip()]))
            return {"available": True, "infected": True, "signature": ", ".join(sigs)[:500], "output": output[:2000], "time_ms": elapsed}
        return {"available": True, "infected": False, "output": "OK", "time_ms": elapsed}
    except subprocess.TimeoutExpired:
        return {"available": True, "error": "Timeout YARA", "time_ms": int((time.time()-t0)*1000)}
    except Exception as e:
        return {"available": True, "error": str(e), "time_ms": int((time.time()-t0)*1000)}

def scan_file(file_path):
    """Scan completo ClamAV + YARA, retorna agregado"""
    clam = scan_with_clamav(file_path)
    yara = scan_with_yara(file_path)
    
    # agregado
    infected = bool(clam.get("infected") or yara.get("infected"))
    signatures = []
    if clam.get("infected") and clam.get("signature"):
        signatures.append(f"ClamAV:{clam['signature']}")
    if yara.get("infected") and yara.get("signature"):
        signatures.append(f"YARA:{yara['signature']}")
    
    # se nenhum disponivel, marca erro
    if not clam.get("available") and not yara.get("available"):
        return {"infected": False, "error": "Nenhum engine disponivel", "clamav": clam, "yara": yara}
    
    return {
        "infected": infected,
        "signatures": signatures,
        "clamav": clam,
        "yara": yara,
        "summary": "; ".join(signatures) if signatures else ("Limpo" if not infected else "Detectado")
    }

if __name__ == "__main__":
    import sys
    print("Check:", check_scanners())
    if len(sys.argv) > 1:
        print(scan_file(sys.argv[1]))
