<p align="center">
  <img src="assets/logo.png" alt="horash" width="360">
</p>

<h1 align="center">horash</h1>

<p align="center">
  <em>triagem local de arquivos em lote: sha-256, virustotal + clamav/yara</em>
</p>

<p align="center">
  <a href="https://github.com/seiti-kg/horash/releases"><img src="https://img.shields.io/badge/release-v0.3.0--beta-blue" alt="release"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green" alt="license"></a>
  <a href="https://www.python.org"><img src="https://img.shields.io/badge/python-3.11-blue" alt="python"></a>
</p>

<p align="center">
  gera <strong>hash sha-256</strong>, consulta <strong>VirusTotal</strong> por hash e escaneia <strong>clamav + yara</strong> offline<br>
  janela app nativa via pywebview.
</p>

---

## INSTALAR

Abra o **powershell** e cole:

```ps1
irm https://raw.githubusercontent.com/seiti-kg/horash/main/tools/install.ps1 | iex
```

O QUE FAZ:
- instala em `%localappdata%\horash` (~45mb app + ~300mb clamav + 7mb yara na primeira vez, 2-5 min)
- instala dependencias python (`pywebview`, `playwright`) se faltar
- baixa clamav/yara via `tools/bootstrap.ps1` automaticamente
- cria atalho na area de trabalho e `horash` no terminal

DEPOIS:
```ps1
horash        # no terminal ou duplo clique no atalho na area de trabalho
```

PARA ATUALIZAR:
```ps1
irm https://raw.githubusercontent.com/seiti-kg/horash/main/tools/install.ps1 | iex
# preserva clamav/db e yara existentes
```

PARA DESINSTALAR:
```ps1
powershell -ExecutionPolicy Bypass -File "$env:LOCALAPPDATA\horash\tools\uninstall.ps1"
```

---
## ESTRUTURA

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

## FLUXO POR TAMANHO

- `<= 650 mb`: sha-256 local → virustotal + scan local
- `> 650 mb`: so scan local

## ENDPOINTS

- `GET /health/scan` → `{"clamav_available":bool, "yara_available":bool}`
- `POST /scan` header `X-Filename`, body `bytes` → `{"infected":bool, "signatures":[]}`

## PRIVACIDADE

- Hash 100% local, sem upload, sem `localstorage`
- Scan 100% offline apos `bootstrap.ps1`
- Temp deletado apos scan
