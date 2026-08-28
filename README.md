<p align="center">
  <img src="assets/logo.png" alt="horash" width="360">
</p>

<h1 align="center">horash</h1>

<p align="center">
  <em>triage local de arquivos em lote: sha-256 sem upload, virustotal + clamav/yara, sem rastros.</em>
</p>

<p align="center">
  <a href="https://github.com/seiti-kg/horash/releases"><img src="https://img.shields.io/badge/release-v0.3.0--beta-blue" alt="release"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green" alt="license"></a>
  <a href="https://www.python.org"><img src="https://img.shields.io/badge/python-3.11-blue" alt="python"></a>
</p>

<p align="center">
  gera <strong>sha-256 sem upload</strong> (streaming 4mb, suporta gbs), consulta <strong>virustotal</strong> por hash e escaneia <strong>clamav + yara</strong> offline — sem limite de 650mb, sem rastros.<br>
  janela app nativa (pywebview), sem navegador.
</p>

---

## instalar

abra o **powershell** e cole:

```ps1
irm https://raw.githubusercontent.com/seiti-kg/horash/main/tools/install.ps1 | iex
```

o que faz:
- instala em `%localappdata%\horash` (~45mb app + ~300mb clamav + 7mb yara na primeira vez, 2-5 min)
- instala dependencias python (`pywebview`, `playwright`) se faltar
- baixa clamav/yara via `tools/bootstrap.ps1` automaticamente
- cria atalho na area de trabalho e `horash` no terminal

depois:
```ps1
horash        # no terminal
# ou duplo clique no atalho na area de trabalho
```

para atualizar:
```ps1
irm https://raw.githubusercontent.com/seiti-kg/horash/main/tools/install.ps1 | iex
# preserva clamav/db e yara existentes
```

para desinstalar:
```ps1
powershell -ExecutionPolicy Bypass -File "$env:LOCALAPPDATA\horash\tools\uninstall.ps1"
```

---

## uso dev

```ps1
git clone https://github.com/seiti-kg/horash.git
cd horash
powershell -ExecutionPolicy Bypass -File tools/bootstrap.ps1
python src/main.py
# abre janela app nativa em http://localhost:8765 (fallback navegador se webview2 faltar)
```

## estrutura

```
horash/
├── horash.bat            # launcher app (chama python src/main.py)
├── src/
│   ├── main.py           # app
│   ├── server.py         # servidor local
│   └── scanner.py        # clamav + yara
├── web/
│   └── index.html
├── yara/
│   └── rules.yar
└── tools/
    ├── install.ps1
    ├── uninstall.ps1
    └── bootstrap.ps1
```

## fluxo por tamanho

- `<= 650 mb`: sha-256 local → virustotal + scan local
- `> 650 mb`: so scan local

## endpoints

- `GET /health/scan` → `{"clamav_available":bool, "yara_available":bool}`
- `POST /scan` header `X-Filename`, body `bytes` → `{"infected":bool, "signatures":[]}`

## privacidade

- hash 100% local, sem upload, sem `localstorage`
- scan 100% offline apos `bootstrap.ps1`
- temp deletado apos scan
