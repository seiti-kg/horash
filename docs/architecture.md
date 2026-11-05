# Arquitetura

[← Funcionalidades](features.md) · [README](../README.md) · [Desenvolvimento →](development.md)

## Visão geral

O horash é uma UI web local servida por um processo Python. Não há framework frontend nem banco de dados; o estado vive na memória do WebView/navegador e o servidor é stateless.

```
┌──────────────────────────────┐
│ web/ (HTML/CSS/JS)           │
│  - hash SHA-256 no browser   │
│  - tabela, progresso, config │
└──────────────┬───────────────┘
               │ fetch/XHR
               ▼
┌──────────────────────────────┐       ┌──────────────────┐
│ src/server.py                │──────▶│ VirusTotal API   │
│ 127.0.0.1:8765               │       │ (hash only)      │
│  - /ping /health/scan        │       └──────────────────┘
│  - /open /vt-scrape          │
│  - POST /scan                │       ┌──────────────────┐
└──────────────┬───────────────┘──────▶│ vt_scrape.py     │
               │                       │ Playwright       │
               ▼                       └──────────────────┘
┌──────────────────────────────┐
│ src/scanner.py               │
│  - clamscan + yara64         │
│  - veredito agregado         │
└──────────────────────────────┘
```

## Estrutura do repositório

```
horash/
├── horash.bat                  # launcher (python src/main.py)
├── horash.spec                 # build PyInstaller (leve/offline)
├── requirements.txt
├── src/
│   ├── main.py                 # pywebview + servidor em thread
│   ├── server.py               # HTTP local, validação de origem, upload
│   ├── scanner.py              # ClamAV + YARA e veredito agregado
│   ├── vt_incognito.py         # abre o VT em aba anônima
│   ├── vt_scrape.py            # scrape do VT com Playwright
│   └── version.py              # versão única do app
├── web/
│   ├── index.html              # bandeja, config, modal de ajuda
│   ├── style.css               # tema console P&B
│   ├── app.js                  # estado, hash, VT, scan local
│   └── sha256.min.js           # js-sha256 para streaming
├── tests/                      # unittest (stdlib), engines mockados
├── tools/
│   ├── install.ps1             # instalador via irm
│   ├── uninstall.ps1
│   ├── bootstrap.ps1           # baixa ClamAV + YARA
│   ├── install_clamav.ps1      # ClamAV fixado + checksum
│   ├── install_yara.ps1        # binário + YARA Forge
│   ├── fix_yara.py             # fallback curado
│   ├── horash_setup.iss        # Inno Setup online
│   └── horash_setup_offline.iss # Inno Setup offline
├── scripts/
│   ├── build.bat               # PyInstaller
│   └── build_setup.bat         # Inno Setup (online + offline)
├── docs/
│   ├── usage.md                # instalação, execução, CLI
│   ├── features.md             # escopo, status e limites
│   ├── architecture.md         # este documento
│   ├── development.md          # build, testes e CI
│   ├── security.md             # privacidade e modelo de ameaça
│   ├── reference/
│   │   ├── endpoints.md        # API HTTP local
│   │   └── engines.md          # ClamAV + YARA
│   └── adr/                    # decisões arquiteturais
├── yara/
│   ├── fallback.yar            # 11 regras versionadas
│   └── rules/                  # full.yar/.yarc gerados, ignorados
├── clamav/                     # baixado pelo bootstrap, ignorado
├── assets/                     # logo/favicons do README
└── .github/workflows/
    ├── ci.yml                  # compileall + unittest
    └── release.yml             # tag v* → scripts no Release
```

`build/`, `dist/`, `clamav/` e `yara/rules/*` não são versionados.

## Módulos

### `src/main.py`

- Verifica se a porta 8765 está ocupada. Se estiver, tenta abrir `http://localhost:8765` no navegador e sai.
- Sobe `server.ThreadedTCPServer` em uma thread daemon.
- Espera o servidor aceitar conexão (até 10 s).
- Tenta `pywebview`/WebView2 com janela 1120×760 (mínimo 900×600, texto selecionável).
- Se o pywebview falhar, abre o navegador padrão e mantém o processo vivo.

### `src/server.py`

- `SimpleHTTPRequestHandler` com `directory=web/`.
- `ThreadingMixIn` para não bloquear o scan.
- `_request_allowed` aplica Host/Origin/Sec-Fetch-Site.
- `do_GET` serve `/ping`, `/health/scan`, `/vt-scrape`, `/open` e estáticos.
- `do_POST` aceita apenas `/scan`, grava o corpo em chunks de 4 MiB, detecta truncamento, roda `scan_file` e remove o temporário no `finally`.
- `_send_json` centraliza JSON/UTF-8.
- `end_headers` adiciona CORS local e `no-store`.

### `src/scanner.py`

- Resolve binários em bundle (`sys._MEIPASS`), diretório do exe, cwd, `src/`, PATH e caminhos comuns do Windows.
- `scan_with_clamav`: limite de 2000 MiB, `clamscan`, timeout de 600 s, parsing de exit code/assinatura.
- `scan_with_yara`: regras `.yar`/`.yarc`, timeout de 300 s, parsing das linhas de match.
- `scan_file`: agrega `infected`, `signatures`, `complete`, `warnings`, `summary` e os resultados por engine.

### `src/vt_scrape.py`

- Playwright síncrono, Chromium headless.
- Intercepta respostas do site do VT e tenta extrair `last_analysis_stats`.
- Faz fallback de parsing por texto/HTML.
- Detecta Cloudflare/403/429 e retorna `available: false` com `error`.

### `src/vt_incognito.py`

- Normaliza hash/URL.
- Procura Chrome, Edge e Firefox em caminhos/registry/PATH.
- Abre com `--incognito`, `--inprivate` ou `--private-window`.
- Fallback: `webbrowser.open` no navegador padrão.

### `web/app.js`

- `files[]`: `{id, name, size, fileObj, rawFile, hash, status, progress, vt, local}`.
- Hash: `WebCrypto` < 50 MiB; `js-sha256` em chunks de 4 MiB acima.
- Após o hash, `delete fileObj`; `rawFile` fica para o scan local.
- Fluxo automático por arquivo: VT (se ≤ 650 MiB) → scan local se o VT não retornar stats.
- Pausa o re-render durante seleção de texto para não perder a seleção.
- `beforeunload` limpa `files` e a API key.

## Fluxo de uma consulta

1. O usuário solta um arquivo.
2. `app.js` calcula o SHA-256 local.
3. Se ≤ 650 MiB:
   - com key: `fetchVT` direto para `virustotal.com`;
   - sem key: `GET /vt-scrape` → `vt_scrape.py` → Playwright.
4. Se o VT não retornar stats: `POST /scan`.
5. `server.py` grava o temporário e chama `scanner.scan_file`.
6. `scanner.py` roda ClamAV e YARA; `scan_file` agrega.
7. `server.py` responde JSON e apaga o temporário.
8. `app.js` renderiza o veredito.

## Decisões de design

- **Loopback only e sem persistência**: o servidor não escuta em `0.0.0.0`; nada de banco, `localStorage`, cookies ou arquivos de configuração. Detalhes e consequências na [ADR 0001](adr/0001-loopback-sem-persistencia.md).
- **Cobertura honesta**: falha de engine nunca vira “Limpo”. Detalhes na [ADR 0002](adr/0002-veredito-parcial.md).
- **Hash-only no VT**: o arquivo nunca é enviado; o scrape também consulta por hash.
- **Sem CDN/fontes externas na UI**: o app não depende de rede para renderizar.
- **Versão única**: `src/version.py` alimenta `/ping` e `server_version`; os `.iss` mantêm `MyAppVersion` em sincronia.
- **Windows-first**: caminhos, engines e instaladores são específicos de Windows.

Índice de ADRs: [docs/adr/README.md](adr/README.md).

## Como estender

**Novo endpoint**: adicione o handler em `server.py` dentro de `do_GET`/`do_POST` (a validação de origem já cobre a request), valide a entrada antes de agir e adicione um teste em `tests/test_server.py`.

**Novo engine**: adicione uma função no `scanner.py` retornando `{available, status, infected, reason, signature, time_ms}`, inclua no `scan_file` para `complete`/`warnings` e teste o contrato de cobertura parcial.

**Nova ação na UI**: adicione o botão em `web/index.html`, o handler em `web/app.js` e mantenha o estado em memória (sem persistência).

Veja [desenvolvimento](development.md).
