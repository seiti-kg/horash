<p align="center">
  <img src="assets/logo.png" alt="horash" width="360">
</p>

<h1 align="center">horash</h1>

<p align="center">
  <em>Triage local de arquivos em lote: SHA-256 sem upload, VirusTotal + ClamAV/YARA, sem rastros.</em>
</p>

<p align="center">
  <a href="https://github.com/seiti-kg/horash/releases"><img src="https://img.shields.io/badge/release-v0.1.1--beta-blue" alt="release"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green" alt="license"></a>
  <a href="https://www.python.org"><img src="https://img.shields.io/badge/python-3.11-blue" alt="python"></a>
  <a href="https://github.com/seiti-kg/horash/blob/main/.github/workflows/release.yml"><img src="https://img.shields.io/badge/build-windows-lightgrey" alt="build"></a>
</p>

<p align="center">
  Gera <strong>SHA-256 sem upload</strong> (streaming 4MB, suporta GBs), consulta <strong>VirusTotal</strong> por hash e escaneia <strong>sempre com ClamAV + YARA</strong> — sem limite de 650MB, sem persistência, sem rastros.<br>
  Quando o VT não vê (arquivo novo, grande ou sensível), o scan offline assume.
</p>

---

## Estrutura

```
horash/
├── Horash.bat            # duplo clique — bypass Smart App Control (recomendado)
├── Horash.spec           # PyInstaller onefile (FileHasher.spec = alias legado)
├── requirements.txt
├── src/                  # Python
│   ├── main.py           # entrypoint .exe (sobe server + abre navegador)
│   ├── server.py         # http://localhost:8765  /ping /open /health/scan /scan /vt-scrape
│   ├── scanner.py        # wrapper ClamAV + YARA
│   ├── vt_incognito.py   # abre VT em --incognito
│   └── vt_scrape.py      # scrape VT via Playwright (sem API key)
├── web/                  # frontend
│   ├── index.html
│   ├── favicon.ico       # ícone do app e do .exe
│   └── sha256.min.js
├── yara/
│   └── rules.yar         # regras (binários yara64.exe ignorados no git)
├── tools/
│   ├── bundle_all.ps1    # baixa ClamAV + YARA
│   ├── install_clamav.ps1
│   └── install_yara.ps1
└── scripts/
    ├── build.bat         # gera dist/Horash.exe
    ├── build_quick.bat   # gera ~10 MB sem ClamAV (teste)
    └── start.bat         # dev: python src/server.py
```

`clamav/`, `build/`, `dist/` são **ignorados no git** (`.gitignore`). Baixe localmente ou pegue o `.exe` pronto em **Releases**.

## Uso rápido (amigos — sem build)

### Opção A — .exe pronto (1 clique)

1. Baixe `Horash.exe` em **Releases** (Assets)
2. Duplo clique → abre `http://localhost:8765` com ClamAV+YARA já dentro

> Se o Windows bloquear (Smart App Control), use a **Opção B**.

### Opção B — sem .exe, bypass SAC (recomendado)

```bat
git clone https://github.com/seiti-kg/horash.git
cd horash

# 1. baixa scanners (1ª vez, ~300 MB, 2-5 min)
powershell -ExecutionPolicy Bypass -File tools/bundle_all.ps1

# 2. roda (duplo clique)
Horash.bat
# ou
python src/main.py
# abre http://localhost:8765
```

Instale Python 3.11+ via [Microsoft Store](https://apps.microsoft.com/detail/9NRWMJP3717K) para o bypass SAC funcionar.

## Uso dev

```bat
powershell -ExecutionPolicy Bypass -File tools/install_clamav.ps1
powershell -ExecutionPolicy Bypass -File tools/install_yara.ps1
# ou
powershell -ExecutionPolicy Bypass -File tools/bundle_all.ps1

scripts\start.bat
# ou
python src/server.py
# ou
python src/main.py
```

## Gerar .exe (você)

Local:
```bat
# precisa ter rodado tools/bundle_all.ps1 antes
scripts\build.bat
# saída: dist\Horash.exe (~350-400 MB com DB)
```

Publicar em **Releases**:

**Manual:**
```bat
gh release create v0.1.1-beta dist/Horash.exe --title "v0.1.1-beta" --notes "Beta" --prerelease
```

**Automático (GitHub Actions):**
```bat
git tag v0.1.1-beta
git push origin v0.1.1-beta
# Actions (.github/workflows/release.yml) builda o .exe no Windows e publica sozinho
```

Teste rápido sem bundle:

```bat
scripts\build_quick.bat
# dist\Horash_Quick.exe (~10 MB, scan local OFF)
```

## Fluxo por tamanho

- `≤ 650 MB`: SHA-256 local → botões `VT anônimo` (`virustotal.com/gui/file/{hash}`) + `API` (com key) + **Scan Local** ClamAV+YARA automático
- `> 650 MB`: VT mostra `N/A` (não aceita upload), só Scan Local é válido

## Endpoints

- `GET /ping` → `{"status":"ok"}`
- `GET /open?hash=SHA256` → abre VT em anônimo local
- `GET /health/scan` → `{"clamav_available":bool, "yara_available":bool, ...}`
- `GET /vt-scrape?hash=SHA256` → scrape VT via Playwright (sem API key)
- `POST /scan` header `X-Filename`, body `bytes` → `{"infected":bool, "signatures":[], "clamav":{}, "yara":{}}`

## Smart App Control

SAC bloqueia `.exe` não assinado por CA reputada. Soluções:

- **Recomendado**: `Horash.bat` (chama `python.exe` assinado Microsoft) — funciona com SAC Enforced
- **Assinar**: `powershell -ExecutionPolicy Bypass -File tools/sign_exe.ps1` (admin)
- **Desativar**: Windows Security > App & browser control > Smart App Control > Off

Detalhes: `tools/disable_sac_instructions.txt`

## Privacidade

- Hash via `js-sha256` streaming **100% local**, sem upload, sem `localStorage`
- Scan local **100% offline** após `freshclam`
- Tudo em memória / temp deletado; `beforeunload` limpa `files` e `apiKey`
