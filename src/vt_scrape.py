#!/usr/bin/env python3
"""
vt_scrape.py - Scrape VirusTotal GUI sem API via Playwright headless + network interception
Bypassa CORS, extrai stats X/Y
"""
import re, time, json

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

VT_URL = "https://www.virustotal.com/gui/file/{hash}"

def scrape_vt(hash_str: str, timeout_ms: int = 18000, headless: bool = True):
    if not PLAYWRIGHT_AVAILABLE:
        return {"error": "playwright não instalado. pip install playwright && playwright install chromium", "available": False}
    if not hash_str or len(hash_str) != 64 or not all(c in "0123456789abcdefABCDEF" for c in hash_str):
        return {"error": f"hash inválido: {hash_str}", "available": False}
    url = VT_URL.format(hash=hash_str)
    start = time.time()
    browser = None
    captured = {}
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless, args=["--no-sandbox","--disable-blink-features=AutomationControlled","--disable-dev-shm-usage"])
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                viewport={"width":1280,"height":900}, locale="en-US",
            )
            context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            page = context.new_page()
            page.set_default_timeout(timeout_ms)

            # Intercepta respostas de API que a GUI faz - filtra pelo hash para pegar stats correto
            def handle_response(resp):
                try:
                    u = resp.url
                    # só captura se URL contém o hash que estamos buscando (evita pegar stats de outro arquivo)
                    if hash_str.lower() not in u.lower():
                        return
                    if "/api/v3/files/" in u or "/ui/files/" in u or "file_behaviour" in u or "analysis" in u:
                        try:
                            j = resp.json()
                            if isinstance(j, dict):
                                data = j.get("data", j)
                                attrs = data.get("attributes", data) if isinstance(data, dict) else {}
                                stats = attrs.get("last_analysis_stats") or j.get("last_analysis_stats")
                                if stats and isinstance(stats, dict) and "malicious" in stats:
                                    # só sobrescreve se stats for mais completo (malicious >0) ou ainda não temos
                                    if "stats" not in captured or stats.get("malicious",0) > captured["stats"].get("malicious",0):
                                        captured["stats"] = stats
                                        captured["results"] = attrs.get("last_analysis_results", {})
                        except:
                            pass
                        try:
                            txt = resp.text()
                            if '"last_analysis_stats"' in txt:
                                m = re.search(r'"last_analysis_stats"\s*:\s*\{([^}]+)\}', txt)
                                if m:
                                    inner = "{"+m.group(1)+"}"
                                    d={}
                                    for k,v in re.findall(r'"([\w-]+)"\s*:\s*(\d+)', inner):
                                        d[k]=int(v)
                                    if d and d.get("malicious",0) > captured.get("stats",{}).get("malicious",-1):
                                        captured["stats"]=d
                        except:
                            pass
                except:
                    pass
            page.on("response", handle_response)

            resp = page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            if resp and resp.status in (403,503,429):
                html = page.content()
                if "Cloudflare" in html or "captcha" in html.lower():
                    return {"error": f"VT Cloudflare bloqueou (status {resp.status}). Use API key.", "available": False, "cloudflare": True}

            # Espera até capturar stats ou ver texto
            for _ in range(12):  # 12*1.5s = 18s max
                if "stats" in captured:
                    break
                # checa texto na página como fallback
                try:
                    txt = page.evaluate("() => document.body.innerText.slice(0,8000)")
                    if "No security vendors" in txt:
                        m = re.search(r'(\d+)\s*security vendors', txt, re.I)
                        total = int(m.group(1)) if m else 72
                        captured["stats"] = {"malicious":0,"undetected":total,"harmless":0,"suspicious":0,"timeout":0}
                        break
                    m = re.search(r'(\d+)\s*/\s*(\d+)', txt)
                    if m and "security vendors" in txt.lower():
                        # verifica se é o placar
                        if captured.get("stats") is None:
                            # tenta confirmar que é detection - procura perto de "flagged"
                            if "flagged" in txt.lower() or "detected" in txt.lower():
                                detected = int(m.group(1)); total=int(m.group(2))
                                # só usa se total ~70 e detected <= total
                                if 30 <= total <= 80 and detected <= total:
                                    captured["stats"] = {"malicious":detected,"undetected":total-detected,"harmless":0,"suspicious":0,"timeout":0}
                                    break
                except:
                    pass
                page.wait_for_timeout(1200)
                # também tenta parse html direto
                try:
                    html = page.content()
                    m = re.search(r'"last_analysis_stats"\s*:\s*\{([^}]+)\}', html)
                    if m:
                        inner="{"+m.group(1)+"}"
                        d={}
                        for k,v in re.findall(r'"([\w-]+)"\s*:\s*(\d+)', inner):
                            d[k]=int(v)
                        if d and "malicious" in d:
                            captured["stats"]=d
                            break
                except:
                    pass

            # Recomputa stats a partir dos results se stats estiver zerado mas results mostra maliciosos (captura de endpoint errado)
            if "stats" in captured and captured["stats"].get("malicious",0)==0 and captured.get("results"):
                try:
                    counts={"malicious":0,"suspicious":0,"undetected":0,"harmless":0,"timeout":0,"failure":0,"confirmed-timeout":0,"type-unsupported":0}
                    for v in captured["results"].values():
                        if isinstance(v, dict):
                            cat=v.get("category","undetected")
                            if cat in counts:
                                counts[cat]+=1
                            else:
                                # fallback: se categoria desconhecida mas result contém Unable, conta como type-unsupported
                                if "unable" in (v.get("result") or "").lower():
                                    counts["type-unsupported"]+=1
                                else:
                                    counts["undetected"]+=1
                    if counts["malicious"]>0:
                        captured["stats"]={
                            "malicious":counts["malicious"],"suspicious":counts["suspicious"],
                            "undetected":counts["undetected"],"harmless":counts["harmless"],
                            "timeout":counts["timeout"],"failure":counts["failure"],"confirmed-timeout":counts["confirmed-timeout"],"type-unsupported":counts["type-unsupported"]
                        }
                except:
                    pass

            elapsed = int((time.time()-start)*1000)
            if "stats" in captured:
                return {"available": True, "stats": captured["stats"], "results": captured.get("results",{}), "url": url, "time_ms": elapsed, "method": "playwright"}
            # Fallback: se VT mostra file not found
            try:
                html = page.content()
                if "File not found" in html:
                    return {"error": "Não encontrado no VT (nunca enviado)", "available": False, "time_ms": elapsed}
            except:
                pass
            return {"error": "Não conseguiu extrair stats (DOM mudou ou Cloudflare). Use API key para confiável.", "available": False, "time_ms": elapsed}
    except Exception as e:
        elapsed = int((time.time()-start)*1000)
        msg=str(e)
        if "Timeout" in msg: msg="Timeout VT (18s) - lento ou Cloudflare"
        return {"error": msg, "available": False, "time_ms": elapsed}
    finally:
        try:
            if browser: browser.close()
        except:
            pass

if __name__ == "__main__":
    import sys
    h = sys.argv[1] if len(sys.argv)>1 else "275a021bbfb6489e54d471899f7db9d1663fc695ec2fe2a2c4538aabf651fd0f"
    print(json.dumps(scrape_vt(h, headless=True), indent=2))
