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

CLAMAV_MAX_MB = 2000
CLAMAV_MAX_BYTES = CLAMAV_MAX_MB * 1024 * 1024
CLAMAV_TIMEOUT_S = 600
YARA_TIMEOUT_S = 300


def _short(text, limit=200):
    """Uma linha curta para exibir em erro/aviso sem despejar o output inteiro."""
    line = " ".join(str(text or "").split())
    return line[:limit]


def get_bundle_base():
    # PyInstaller extrai para sys._MEIPASS; dev: project_root (parent de src/)
    if hasattr(sys, '_MEIPASS'):
        return sys._MEIPASS
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_exe_dir():
    # quando instalado via horash_setup.exe, engines ficam ao lado do exe em {app}, nao em _MEIPASS
    try:
        if hasattr(sys, '_MEIPASS'):
            # sys.executable = C:\Users\...\horash\horash.exe
            exe_dir = os.path.dirname(os.path.abspath(sys.executable))
            if os.path.isdir(exe_dir):
                return exe_dir
        # fallback: cwd ou project root
        return os.getcwd()
    except:
        return os.getcwd()

def find_binary(name_variants):
    """Tenta achar binario em bundle, exe_dir, PATH e locais comuns Windows"""
    bases = [get_bundle_base(), get_exe_dir(), os.getcwd(), os.path.dirname(os.path.abspath(__file__))]
    # dedup
    seen = []
    for b in bases:
        if b and b not in seen:
            seen.append(b)
    # 1. bundle / exe_dir / cwd
    for base in seen:
        for variant in name_variants:
            for sub in ["clamav", "yara", "bin", ""]:
                cand = os.path.join(base, sub, variant)
                if os.path.isfile(cand):
                    return cand
            cand2 = os.path.join(base, variant)
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
    bases = [get_bundle_base(), get_exe_dir(), os.getcwd(), os.path.dirname(os.path.abspath(__file__))]
    seen = []
    for b in bases:
        if b and b not in seen:
            seen.append(b)
    candidates = []
    for base in seen:
        candidates.extend([
            os.path.join(base, "yara", "rules", "full.yar"),
            os.path.join(base, "yara", "rules", "extended.yar"),
            os.path.join(base, "yara", "rules", "core.yar"),
            os.path.join(base, "yara", "rules.yar"),
            os.path.join(base, "yara", "fallback.yar"),
            os.path.join(base, "rules.yar"),
            os.path.join(base, "rules", "index.yar"),
        ])
    for p in candidates:
        if os.path.isfile(p):
            return p
    # busca recursiva por .yar
    for base in seen:
        for root in [os.path.join(base, "yara")]:
            if os.path.isdir(root):
                files = sorted(glob.glob(os.path.join(root, "**", "*.yar"), recursive=True))
                if files:
                    return files[0]
    return None


def find_yara_compiled(rules_path):
    """Retorna o .yarc compilado se for mais novo que o .yar de origem."""
    if not rules_path or not os.path.isfile(rules_path):
        return None
    try:
        rules_mtime = os.path.getmtime(rules_path)
    except OSError:
        return None
    candidates = [os.path.splitext(rules_path)[0] + ".yarc", rules_path + "c"]
    for candidate in candidates:
        if os.path.isfile(candidate):
            try:
                if os.path.getmtime(candidate) >= rules_mtime:
                    return candidate
            except OSError:
                continue
    return None

def get_clamav_db_path():
    bases = [get_bundle_base(), get_exe_dir(), os.getcwd(), os.path.dirname(os.path.abspath(__file__))]
    seen = []
    for b in bases:
        if b and b not in seen:
            seen.append(b)
    for base in seen:
        for cand in [os.path.join(base, "clamav", "db"), os.path.join(base, "db")]:
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
        "yara_compiled": find_yara_compiled(rules),
    }

def scan_with_clamav(file_path):
    """Retorna dict com status: clean|infected|error|unavailable|skipped."""
    clamscan = find_clamscan()
    if not clamscan:
        return {
            "available": False,
            "status": "unavailable",
            "infected": False,
            "reason": "ClamAV nao encontrado",
            "error": "ClamAV nao encontrado. Instale via tools/install_clamav.ps1 ou bundle no .exe",
        }

    # O ClamAV nao consegue abrir arquivos acima de 2 GiB; com --max-filesize ele
    # pularia o arquivo e retornaria "OK", escondendo a cobertura parcial.
    try:
        size = os.path.getsize(file_path)
    except OSError as e:
        return {
            "available": True,
            "status": "error",
            "infected": False,
            "reason": f"nao foi possivel ler o arquivo: {e}",
            "error": str(e),
            "time_ms": 0,
        }
    if size > CLAMAV_MAX_BYTES:
        return {
            "available": True,
            "status": "skipped",
            "infected": False,
            "signature": None,
            "reason": f"arquivo maior que {CLAMAV_MAX_MB} MB (limite do ClamAV)",
            "output": "",
            "time_ms": 0,
        }

    db = get_clamav_db_path()
    cmd = [clamscan, "--no-summary", "--stdout"]
    if db:
        cmd.extend(["--database", db])
    cmd.extend([f"--max-filesize={CLAMAV_MAX_MB}M", f"--max-scansize={CLAMAV_MAX_MB}M"])
    cmd.append(file_path)
    t0 = time.time()

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=CLAMAV_TIMEOUT_S)
        elapsed = int((time.time() - t0) * 1000)
        output = (result.stdout or "") + (result.stderr or "")
        # clamscan exit code: 0 clean, 1 infected, 2 error
        if result.returncode == 1:
            sig = "Desconhecido"
            for line in output.splitlines():
                if "FOUND" in line:
                    parts = line.split(":")
                    if len(parts) >= 2:
                        sig = parts[-1].replace("FOUND", "").strip()
                    break
            return {
                "available": True,
                "status": "infected",
                "infected": True,
                "signature": sig,
                "output": output.strip(),
                "time_ms": elapsed,
            }
        if result.returncode == 0:
            return {
                "available": True,
                "status": "clean",
                "infected": False,
                "signature": None,
                "output": "OK",
                "time_ms": elapsed,
            }
        return {
            "available": True,
            "status": "error",
            "infected": False,
            "reason": _short(output) or f"exit {result.returncode}",
            "error": output.strip() or f"exit {result.returncode}",
            "time_ms": elapsed,
        }
    except subprocess.TimeoutExpired:
        return {
            "available": True,
            "status": "error",
            "infected": False,
            "reason": f"timeout (>{CLAMAV_TIMEOUT_S // 60} min)",
            "error": "Timeout scan (>10min) - arquivo muito grande ou travado",
            "time_ms": int((time.time() - t0) * 1000),
        }
    except Exception as e:
        return {
            "available": True,
            "status": "error",
            "infected": False,
            "reason": _short(e),
            "error": str(e),
            "time_ms": int((time.time() - t0) * 1000),
        }

def scan_with_yara(file_path):
    """Retorna dict com status: clean|infected|error|unavailable."""
    yara = find_yara()
    rules = find_yara_rules()
    if not yara:
        return {
            "available": False,
            "status": "unavailable",
            "infected": False,
            "reason": "YARA nao encontrado",
            "error": "YARA nao encontrado",
        }
    if not rules:
        return {
            "available": True,
            "status": "error",
            "infected": False,
            "reason": "regras YARA nao encontradas (yara/rules.yar)",
            "error": "Regras YARA nao encontradas (yara/rules.yar)",
        }
    t0 = time.time()

    if os.path.isdir(rules):
        yar_files = glob.glob(os.path.join(rules, "**", "*.yar"), recursive=True)
        if not yar_files:
            return {
                "available": True,
                "status": "error",
                "infected": False,
                "reason": "nenhuma regra .yar encontrada",
                "error": "Nenhuma regra .yar encontrada",
                "time_ms": int((time.time() - t0) * 1000),
            }
        hits = []
        failures = 0
        for rf in yar_files[:50]:
            try:
                r = subprocess.run(
                    [yara, rf, file_path],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                if r.stdout.strip():
                    hits.append(r.stdout.strip())
            except Exception:
                failures += 1
        elapsed = int((time.time() - t0) * 1000)
        if hits:
            return {
                "available": True,
                "status": "infected",
                "infected": True,
                "signature": "; ".join(hits)[:500],
                "output": "\n".join(hits)[:2000],
                "time_ms": elapsed,
            }
        if failures:
            return {
                "available": True,
                "status": "error",
                "infected": False,
                "reason": f"falha em {failures} arquivo(s) de regras",
                "error": f"Falha ao executar YARA em {failures} arquivo(s) de regras",
                "time_ms": elapsed,
            }
        return {
            "available": True,
            "status": "clean",
            "infected": False,
            "output": "OK",
            "time_ms": elapsed,
        }

    compiled = find_yara_compiled(rules)
    cmd = [yara, "-C", compiled, file_path] if compiled else [yara, rules, file_path]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=YARA_TIMEOUT_S)
        elapsed = int((time.time() - t0) * 1000)
        output = (result.stdout or "").strip()
        if result.returncode != 0:
            err = (result.stderr or output or f"exit {result.returncode}").strip()
            return {
                "available": True,
                "status": "error",
                "infected": False,
                "reason": _short(err),
                "error": err,
                "time_ms": elapsed,
            }
        if output:
            sigs = list(set([line.split()[0] for line in output.splitlines() if line.strip()]))
            return {
                "available": True,
                "status": "infected",
                "infected": True,
                "signature": ", ".join(sigs)[:500],
                "output": output[:2000],
                "time_ms": elapsed,
            }
        return {
            "available": True,
            "status": "clean",
            "infected": False,
            "output": "OK",
            "time_ms": elapsed,
        }
    except subprocess.TimeoutExpired:
        return {
            "available": True,
            "status": "error",
            "infected": False,
            "reason": f"timeout (>{YARA_TIMEOUT_S // 60} min)",
            "error": "Timeout YARA",
            "time_ms": int((time.time() - t0) * 1000),
        }
    except Exception as e:
        return {
            "available": True,
            "status": "error",
            "infected": False,
            "reason": _short(e),
            "error": str(e),
            "time_ms": int((time.time() - t0) * 1000),
        }

def _engine_warning(name, result):
    status = result.get("status")
    if status in ("clean", "infected"):
        return None
    reason = result.get("reason") or result.get("error") or "falha"
    if status == "skipped":
        return f"{name}: ignorado ({reason})"
    if status == "unavailable":
        return f"{name}: indisponivel"
    return f"{name}: erro ({reason})"


def scan_file(file_path):
    """Roda ClamAV + YARA e retorna veredito agregado com cobertura explicita."""
    clam = scan_with_clamav(file_path)
    yara = scan_with_yara(file_path)

    infected = bool(clam.get("infected") or yara.get("infected"))
    signatures = []
    if clam.get("infected") and clam.get("signature"):
        signatures.append(f"ClamAV:{clam['signature']}")
    if yara.get("infected") and yara.get("signature"):
        signatures.append(f"YARA:{yara['signature']}")

    warnings = [
        warning
        for warning in (
            _engine_warning("ClamAV", clam),
            _engine_warning("YARA", yara),
        )
        if warning
    ]
    ran = [
        result
        for result in (clam, yara)
        if result.get("status") in ("clean", "infected")
    ]
    complete = (
        clam.get("status") in ("clean", "infected")
        and yara.get("status") in ("clean", "infected")
    )

    if infected:
        summary = "; ".join(signatures) or "Detectado"
        if not complete:
            summary += " (parcial)"
    elif complete:
        summary = "Limpo"
    else:
        summary = "Parcial" + (": " + "; ".join(warnings) if warnings else "")

    result = {
        "infected": infected,
        "signatures": signatures,
        "clamav": clam,
        "yara": yara,
        "complete": complete,
        "warnings": warnings,
        "summary": summary,
    }
    if not ran:
        result["error"] = "Nenhum engine concluiu o scan"
    return result


if __name__ == "__main__":
    import sys
    print("Check:", check_scanners())
    if len(sys.argv) > 1:
        print(scan_file(sys.argv[1]))
