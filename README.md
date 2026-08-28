<p align="center">
  <img src="assets/logo.png" alt="horash" width="360">
</p>

<h1 align="center">horash</h1>

<p align="center">
  <em>triage local de arquivos em lote: sha-256 sem upload, virustotal + clamav/yara, sem rastros.</em>
</p>

<p align="center">
  <a href="https://github.com/seiti-kg/horash/releases"><img src="https://img.shields.io/badge/release-v0.1.1--beta-blue" alt="release"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green" alt="license"></a>
  <a href="https://www.python.org"><img src="https://img.shields.io/badge/python-3.11-blue" alt="python"></a>
  <a href="https://github.com/seiti-kg/horash/blob/main/.github/workflows/release.yml"><img src="https://img.shields.io/badge/build-windows-lightgrey" alt="build"></a>
</p>

<p align="center">
  gera <strong>sha-256 sem upload</strong> (streaming 4mb, suporta gbs), consulta <strong>virustotal</strong> por hash e escaneia <strong>sempre com clamav + yara</strong> — sem limite de 650mb, sem persistencia, sem rastros.<br>
  quando o vt nao ve (arquivo novo, grande ou sensivel), o scan offline assume.
</p>

---

## estrutura

```
horash/
├── horash.spec           # pyinstaller leve (~45mb) - horash_setup usa
├── horash.bat            # duplo clique — bypass smart app control (recomendado)
├── requirements.txt
├── src/                  # python
│   ├── main.py           # entrypoint .exe (sobe server + abre navegador)
│   ├── server.py         # http://localhost:8765  /ping /open /health/scan /scan /vt-scrape
│   ├── scanner.py        # wrapper clamav + yara
│   ├── vt_incognito.py   # abre vt em --incognito
│   └── vt_scrape.py      # scrape vt via playwright (sem api key)
├── web/                  # frontend
│   ├── index.html
│   ├── favicon.ico       # icone do app e do .exe
│   └── sha256.min.js
├── yara/
│   ├── rules.yar         # regras (yara-forge core ~5k regras, fallback curado 12 regras)
│   └── rules/curated.yar # fallback leve
├── tools/
│   ├── bootstrap.ps1     # baixa clamav + yara sem git (usado pelo setup leve)
│   ├── install_clamav.ps1
│   ├── install_yara.ps1
│   ├── fix_yara.py       # gera regras curadas sem acionar antivirus
│   ├── horash_setup.iss          # setup leve (online, ~20mb)
│   └── horash_setup_offline.iss  # setup full offline (~400mb)
└── scripts/
    ├── build.bat         # gera dist/horash.exe leve
    ├── build_setup.bat   # gera horash_setup.exe + horash_setup_offline.exe
    └── start.bat         # dev: python src/server.py
```

`clamav/`, `build/`, `dist/` sao **ignorados no git** (`.gitignore`). baixe localmente ou pegue o setup em **releases**.

## uso rapido (amigos — sem git, sem build)

### baixe em releases (recomendado)

va em **releases** e escolha um:

| arquivo | tamanho | internet na instalacao | quando usar |
|---|---|---|---|
| `horash_setup.exe` | ~20 mb | sim (baixa ~300mb na instalacao, 2-5min) | recomendado, download rapido |
| `horash_setup_offline.exe` | ~400 mb | nao (ja vem com tudo) | sem internet / pendrive / airgap |

**passo a passo (horash_setup.exe):**

1. baixe `horash_setup.exe` em **releases > assets**
2. duplo clique → `onde instalar? [C:\Users\voce\AppData\Local\horash]` → pode mudar → `next`
3. escolha `[x] yara [x] clamav` (pode desmarcar) → `instalar` → se marcou, baixa com barrinha
4. `concluir` → abre `http://localhost:8765` automatico. atalho criado na area de trabalho.

> sem `git clone`, sem `powershell` manual, sem instalar python. so duplo clique.

<details>
<summary>sem setup? portable direto</summary>

- baixe `horash.exe` em releases (leve, ~12mb) → duplo clique → funciona para hash+vt. para scan local clique em `baixar protecoes` quando pedir, ou rode `tools/bootstrap.ps1`.

</details>

### bypass smart app control

se o windows bloquear `horash_setup.exe` (sac enforced), use o portable:

```bat
# sem setup, sem sac
horash.bat
# ou python src/main.py
# abre http://localhost:8765
```

instale python 3.11+ via [microsoft store](https://apps.microsoft.com/detail/9NRWMJP3717K) para o bypass funcionar.

## uso dev

```bat
powershell -ExecutionPolicy Bypass -File tools/bootstrap.ps1
# ou separado:
powershell -ExecutionPolicy Bypass -File tools/install_clamav.ps1
powershell -ExecutionPolicy Bypass -File tools/install_yara.ps1

scripts\start.bat
# ou
python src/server.py
# ou
python src/main.py
```

## gerar setups (voce)

local:

```bat
scripts\build.bat
# saida: dist\horash.exe (~45 mb leve)

scripts\build_setup.bat
# saida: dist\horash_setup.exe (~20 mb) + dist\horash_setup_offline.exe (~400 mb)

# so offline portable (um exe so com tudo dentro):
set HORASH_OFFLINE=1
python -m PyInstaller horash.spec --noconfirm --clean
# saida: dist\horash.exe (~400 mb)
```

publicar em **releases**:

**manual:**

```bat
gh release create v0.1.1-beta dist/horash_setup.exe dist/horash_setup_offline.exe dist/horash.exe --title "v0.1.1-beta" --notes "beta" --prerelease
```

**automatico (github actions):**

```bat
git tag v0.1.1-beta
git push origin v0.1.1-beta
# actions (.github/workflows/release.yml) builda tudo no windows e publica sozinho
```

## fluxo por tamanho

- `<= 650 mb`: sha-256 local → botoes `vt anonimo` (`virustotal.com/gui/file/{hash}`) + `api` (com key) + **scan local** clamav+yara automatico
- `> 650 mb`: vt mostra `n/a` (nao aceita upload), so scan local e valido

## endpoints

- `GET /ping` → `{"status":"ok"}`
- `GET /open?hash=SHA256` → abre vt em anonimo local
- `GET /health/scan` → `{"clamav_available":bool, "yara_available":bool, ...}`
- `GET /vt-scrape?hash=SHA256` → scrape vt via playwright (sem api key)
- `POST /scan` header `X-Filename`, body `bytes` → `{"infected":bool, "signatures":[], "clamav":{}, "yara":{}}`

## smart app control

sac bloqueia `.exe` nao assinado por ca reputada. solucoes:

- **recomendado**: `horash.bat` (chama `python.exe` assinado microsoft) — funciona com sac enforced
- **setup**: `horash_setup.exe` ja instala em `%localappdata%` sem precisar admin, mas pode pedir permissao se escolher `C:\Program Files`
- **assinar**: `powershell -ExecutionPolicy Bypass -File tools/sign_exe.ps1` (admin)
- **desativar**: windows security > app & browser control > smart app control > off

detalhes: `tools/disable_sac_instructions.txt`

## privacidade

- hash via `js-sha256` streaming **100% local**, sem upload, sem `localstorage`
- scan local **100% offline** apos `freshclam`
- tudo em memoria / temp deletado; `beforeunload` limpa `files` e `apiKey`
