<p align="center">
  <img src="assets/logo.png" alt="horash" width="360">
</p>

<h1 align="center">horash</h1>

<p align="center">
  <em>triagem local de arquivos em lote: sha-256, virustotal + clamav/yara</em>
</p>

<p align="center">
  <a href="src/version.py"><img src="https://img.shields.io/badge/version-0.4.0--beta-blue" alt="version"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green" alt="license"></a>
  <a href="https://www.python.org"><img src="https://img.shields.io/badge/python-3.11-blue" alt="python"></a>
</p>

<p align="center">
  gera <strong>hash sha-256</strong>, consulta <strong>VirusTotal</strong> por hash e escaneia <strong>clamav + yara</strong> localmente<br>
  janela nativa via pywebview. Windows 10/11.
</p>

---

## REQUISITOS

- Windows 10/11 (o servidor e os engines são específicos de Windows).
- PowerShell 5.1+.
- Internet na primeira execução (dependências, ClamAV, YARA e regras).
- Python 3.11+ — o instalador baixa automaticamente se não encontrar um Python real.
- ~400 MB ou mais de disco depois do bootstrap (ClamAV + YARA full + regras compiladas).

## INSTALAR

Abra o **PowerShell** e cole:

```ps1
irm https://raw.githubusercontent.com/seiti-kg/horash/main/tools/install.ps1 | iex
```

O QUE FAZ:
- instala em `%localappdata%\horash` (o app é código; ClamAV ~300 MB + YARA full ~20 MB de regras + ~45 MB compilado vêm na primeira vez, 2–5 min)
- instala dependências Python no Python do usuário (`pywebview`, `playwright`); não cria venv
- baixa ClamAV e YARA via `tools/bootstrap.ps1`
- baixa o Chromium do Playwright (usado pelo scrape do VT quando não há API key)
- cria atalho na área de trabalho, no menu iniciar e o comando `horash`

DEPOIS:
```ps1
horash        # terminal, atalho ou duplo clique
```

Se o Python não existir, o instalador tenta `winget` e depois o instalador oficial do python.org.

PARA ATUALIZAR:
```ps1
irm https://raw.githubusercontent.com/seiti-kg/horash/main/tools/install.ps1 | iex
# preserva clamav/db e yara existentes
```

PARA DESINSTALAR:
```ps1
powershell -ExecutionPolicy Bypass -File "$env:LOCALAPPDATA\horash\tools\uninstall.ps1"
```

O desinstalador remove a pasta do app, atalhos e o `horash` do PATH. Ele **não** remove pacotes pip nem o cache de browsers do Playwright.

---

## FLUXO

1. **Hash local:** `SHA-256` no navegador (`WebCrypto` para <50 MB, `js-sha256` em streaming de 4 MB acima disso). O arquivo não é enviado para fora.
2. **VirusTotal por hash:** ao soltar um arquivo de até 650 MB, o hash é consultado automaticamente.
   - Com API key: `X / 72` na tabela via API oficial.
   - Sem key: scrape do site do VT com Playwright (mais lento e sujeito a Cloudflare).
   - Acima de 650 MB: o app não consulta o VT.
3. **Scan local:** se o VT não retornar resultado, `POST /scan` envia o arquivo para o servidor local, que roda **ClamAV + YARA** e apaga o temporário.
   - ClamAV cobre até **2000 MB**. Acima disso ele é ignorado e o resultado aparece como **⚠️ Parcial**.
   - Se um engine falhar, expirar ou não estiver instalado, o resultado também é **⚠️ Parcial** — nunca "Limpo" silencioso.

## ESTRUTURA

```
horash/
├── horash.bat              # launcher (chama python src/main.py)
├── src/
│   ├── main.py             # pywebview + servidor em thread
│   ├── server.py           # HTTP local (somente 127.0.0.1)
│   ├── scanner.py          # ClamAV + YARA e veredito agregado
│   ├── vt_incognito.py     # abre o VT em aba anônima
│   ├── vt_scrape.py        # scrape do VT com Playwright
│   └── version.py          # versão única
├── web/
│   ├── index.html
│   ├── style.css
│   ├── app.js
│   └── sha256.min.js
├── tests/                  # unittest (stdlib)
├── yara/
│   ├── fallback.yar        # 11 regras de emergência (versionadas)
│   ├── rules/full.yar      # YARA Forge full instalado (não versionado)
│   └── rules/full.yarc     # regras compiladas para scan rápido (não versionado)
├── tools/
│   ├── install.ps1
│   ├── uninstall.ps1
│   ├── bootstrap.ps1
│   ├── install_clamav.ps1
│   ├── install_yara.ps1
│   └── fix_yara.py
├── horash.spec             # build opcional com PyInstaller
└── .github/workflows/      # ci.yml + release.yml
```

## ENDPOINTS

O servidor escuta **apenas em `127.0.0.1:8765`** e rejeita `Host`/`Origin` que não sejam locais e requests cross-site.

| Método | Rota | Função |
|---|---|---|
| GET | `/ping` | health check (`{"status":"ok","version":"..."}`) |
| GET | `/health/scan` | presença de ClamAV/YARA, caminhos e DB |
| GET | `/open?hash=<sha256>` | abre `virustotal.com/gui/file/{hash}` em aba anônima |
| GET | `/vt-scrape?hash=<sha256>` | scrape do VT com Playwright |
| POST | `/scan` | header `X-Filename`, body com os bytes; retorna `infected`, `signatures`, `complete`, `warnings`, `clamav`, `yara` |

`/scan` aceita até 10 GB e rejeita upload truncado com `400`. O temporário é apagado ao fim do scan.

## PRIVACIDADE

- O hash é gerado localmente. Na consulta ao VirusTotal, **o hash** (não o arquivo) é enviado ao VT.
- Os bytes do arquivo vão apenas para o servidor local (`127.0.0.1`) e para o processo do ClamAV/YARA.
- ClamAV/YARA funcionam offline depois do `bootstrap.ps1`.
- Sem `localStorage` e sem cookies. A API key fica só em memória e é limpa ao fechar.
- O temporário é deletado após o scan; isso **não** é apagamento seguro (o arquivo pode ser recuperável no disco).
- A UI não carrega fontes/CDNs externos; só há tráfego externo quando uma consulta ao VT roda.

## REGRAS YARA

O bootstrap instala o pacote **full** do [YARA Forge](https://github.com/YARAHQ/yara-forge) (~11.800 regras) e o compila com `yarac` para scans rápidos. Para trocar o pacote:

```ps1
powershell -ExecutionPolicy Bypass -File tools/install_yara.ps1 -Package core
# opções: core, extended, full
```

O `core` é menor e tem menos falso positivo; `full` cobre mais famílias. As regras instaladas são ignoradas pelo Git e ficam em `yara/rules/`; `yara/fallback.yar` é usado só se o download falhar. O instalador confere o SHA-256 da release e usa a release `latest` do YARA Forge.

## LIMITES CONHECIDOS

- Windows 10/11; o servidor e os engines são específicos de Windows.
- ClamAV >2000 MB: ignorado; resultado parcial (YARA ainda roda).
- Acima de 650 MB o app não consulta o VT (o limite de upload do VT é 650 MB; o app usa apenas lookup por hash).
- Scan local de arquivos muito grandes depende de espaço em `%TEMP%` e pode levar minutos.
- Scrape do VT pode falhar por Cloudflare/rate limit; use API key para resultado confiável.
- Regras YARA são assinaturas estáticas: não desempacotam nem emulam. O pacote `full` aumenta a cobertura e também o risco de falso positivo; trate match YARA como suspeita, não como veredito de AV.

## RODAR DO CÓDIGO (DEV)

```ps1
git clone https://github.com/seiti-kg/horash.git
cd horash
python -m pip install -r requirements.txt

# baixa ClamAV + YARA full (~2-5 min). Sem isso, o scan local fica parcial.
powershell -ExecutionPolicy Bypass -File tools/bootstrap.ps1

python src/main.py                 # app com janela pywebview
# ou:
python src/server.py               # só o servidor; abra http://localhost:8765
# ou, no Explorer:
horash.bat
```

Para usar menos disco/regras: `powershell -ExecutionPolicy Bypass -File tools/install_yara.ps1 -Package core`.

O YARA instalado localmente fica em `yara/rules/full.yar` e `full.yarc` (ignorados pelo Git). O `yara/fallback.yar` versionado tem só 11 regras de emergência; o bootstrap baixa o pacote full.

## DEV / TESTES

```ps1
python -m unittest discover -s tests -v
pyinstaller horash.spec            # dist/horash.exe (opcional)
```

Os testes usam apenas a stdlib (`unittest`) e não precisam de ClamAV/YARA instalados; os limites e erros dos engines são testados com mocks. O CI roda em `windows-latest` a cada push/PR e também antes de releases por tag.

O `horash.spec` sem `HORASH_OFFLINE=1` não embute ClamAV/YARA no exe; nesse caso o app usa os engines instalados ao lado do executável (ou baixados pelo bootstrap).

## LICENÇA

MIT — veja [LICENSE](LICENSE).
