# Uso

[← README](../README.md) · [Funcionalidades →](features.md) · [Endpoints](reference/endpoints.md)

O horash é instalado como código Python em `%LOCALAPPDATA%\horash`; não há `.exe` publicado nas releases. O instalador baixa o código de `main`, instala as dependências e baixa os engines.

## Requisitos

- Windows 10/11 x64.
- PowerShell 5.1+.
- Internet na primeira execução (Python, dependências, Chromium, ClamAV, YARA e regras).
- Python 3.11+ **ou** permissão para o instalador instalar o Python 3.11.9.
- ~500 MB de disco livre (pode passar de 600 MB com caches do pip/Playwright). Componentes:
  - ClamAV 1.5.4: ~225 MB de download, ~250–300 MB em disco com o banco.
  - YARA Forge full: ~20 MB de regras + ~45 MB compiladas.
  - Chromium do Playwright: ~150 MB.
  - Dependências Python e o app: dezenas de MB.

O servidor e os engines são específicos de Windows. O app não roda em Linux/macOS.

## Instalação rápida

Abra um **PowerShell novo** e cole:

```ps1
irm https://raw.githubusercontent.com/seiti-kg/horash/main/tools/install.ps1 | iex
```

Depois:

```ps1
horash
```

O comando `horash` só existe em um terminal aberto **depois** da instalação, porque o PATH da sessão atual não é recarregado. Também há atalhos na área de trabalho e no menu Iniciar.

## O que o instalador faz

1. Procura um Python real (`python`, `python3` ou `py`) e ignora o alias da Microsoft Store que só abre a loja.
2. Se não encontrar, tenta `winget install Python.Python.3.11`. Se falhar, baixa o instalador oficial `python-3.11.9-amd64.exe` e instala silenciosamente.
3. Baixa o zip de `https://github.com/seiti-kg/horash/archive/refs/heads/main.zip` e copia o app para `%LOCALAPPDATA%\horash`, preservando `clamav/` e `yara/` existentes.
4. Instala `requirements.txt` com `pip` no Python do usuário. Não cria venv. As dependências incluem `pywebview`, `playwright` e `pyinstaller`.
5. Baixa o Chromium do Playwright (usado pelo scrape do VirusTotal quando não há API key).
6. Roda `tools/bootstrap.ps1` **somente se** ClamAV, binário do YARA ou regras estiverem faltando.
7. Cria atalhos na área de trabalho e no menu Iniciar, além do shim `%LOCALAPPDATA%\horash\bin\horash.cmd` adicionado ao PATH do usuário.

O download do ClamAV é fixado em 1.5.4 e tem o SHA-256 conferido antes de substituir a instalação existente. O YARA Forge usa a release `latest`; o checksum é conferido quando a API do GitHub informa o digest.

## Executar

```ps1
horash                  # instalação via install.ps1 (terminal novo)
python src/main.py      # checkout de dev: janela pywebview
python src/server.py    # só o servidor; abra http://localhost:8765
horash.bat              # launcher no Explorer (ignora o alias da Store)
```

- O `main.py` verifica a porta 8765. Se estiver ocupada, tenta abrir `http://localhost:8765` no navegador em vez de subir outro servidor.
- O `server.py` sobe apenas em `127.0.0.1:8765` e serve a UI de `web/`.
- O `horash.bat` usa o diretório do próprio arquivo (não o cwd) e mantém a janela aberta ao sair.

## Bandeja

- Arraste arquivos para a área de drop, clique em **Selecionar** ou use **Ctrl+V**.
- Vários arquivos são aceitos; o hash de cada um aparece na tabela.
- **Copiar hashes** copia `nome  hash` por linha.
- **Limpar** esvazia a bandeja. Fechar ou recarregar a página também limpa tudo (sem `localStorage`).
- O arquivo precisa continuar na bandeja para o **Scan Local**. Depois de fechar/recarregar, selecione o arquivo de novo.

## 1. Hash local

O SHA-256 é calculado no seu dispositivo; o arquivo não é enviado ao VirusTotal.

- Arquivos **< 50 MiB**: `WebCrypto` (`crypto.subtle.digest`), com o arquivo inteiro em memória.
- Arquivos **≥ 50 MiB**: `js-sha256` em streaming de **4 MiB**, sem carregar o arquivo inteiro na RAM.
- O progresso aparece na coluna SHA-256; acima de 50 MiB também mostra bytes processados.

## 2. VirusTotal por hash

Ao terminar o hash de um arquivo **≤ 650 MiB**, a consulta ao VT começa automaticamente. O horash envia **apenas o hash**, nunca o arquivo.

| Modo | Como funciona |
|---|---|
| Com API key | Consulta `https://www.virustotal.com/api/v3/files/{hash}` direto do navegador. A tabela mostra `X / N` e os logs por engine. |
| Sem API key | O servidor local abre o site do VT com Playwright/Chromium headless e intercepta os stats. Mais lento (~25 s) e sujeito a Cloudflare. |
| Acima de 650 MiB | O VT não é consultado; o arquivo vai direto para o scan local. |

Detalhes:

- `N` é o total de engines que responderam naquele momento (hoje normalmente ~72); o número não é fixo.
- `404`/“Não encontrado no VT” significa que ninguém enviou aquele arquivo ao VT ainda. O horash não faz upload.
- A API pública tem limite de ~4 requisições/minuto. O botão **API VT** em lote espera ~16 s entre arquivos para respeitar o limite.
- Se a consulta ao VT falhar (404, 429, key inválida, Cloudflare), o scan local roda automaticamente.
- Se o VT retornar stats, o scan local é marcado como **“VT usado”** e não roda sozinho; o botão **Scan Local** continua disponível.
- O botão **VT anônimo** abre o relatório no Chrome (`--incognito`), Edge (`--inprivate`) ou Firefox (`--private-window`). Sem esses navegadores, abre no navegador padrão sem modo privado.

A API key fica apenas na memória do campo **Config → VirusTotal API** e é enviada direto para `virustotal.com`; o servidor local nunca a recebe. Ela é limpa ao fechar/recarregar a página. Veja [segurança e privacidade](security.md).

## 3. Scan local

O scan local roda quando:

- o VT não retornou resultado; ou
- o arquivo tem mais de 650 MiB; ou
- você clica em **Scan Local** (individual ou em lote).

O navegador envia os bytes para `POST http://localhost:8765/scan`; o servidor grava um temporário, roda **ClamAV + YARA** e apaga o temporário ao final. O arquivo não sai da máquina.

| Resultado | Significado |
|---|---|
| ✓ Limpo | ClamAV e YARA concluíram e nenhum detectou. |
| ⛔ Infectado | Pelo menos um engine detectou. Se o outro engine falhou, aparece “(parcial)”. |
| ⚠️ Parcial | Um engine foi ignorado, não estava instalado, deu erro ou estourou o timeout. A lista de avisos mostra qual. |
| ⚠️ Erro | Nenhum engine concluiu, ou o servidor local está desligado. A UI mostra a mensagem no lugar do veredito. |

Limites dos engines:

- ClamAV cobre até **2000 MiB (~2,1 GB)**. Acima disso ele é ignorado e o resultado fica parcial; o YARA ainda roda.
- Timeout: ClamAV 600 s; YARA 300 s.
- Se o ClamAV não estiver instalado e o YARA estiver, o resultado ainda é **parcial**, nunca “Limpo” silencioso.

O rodapé e a aba **Config** mostram a saúde de ClamAV/YARA (`/health/scan`). O servidor é verificado a cada 5 s e os engines a cada 7 s.

## Ações em lote

| Botão | Efeito |
|---|---|
| Copiar hashes | Copia todos os hashes no formato `nome  hash`. |
| Abrir VT | Abre todos os relatórios em abas anônimas via servidor, em sequência. Sem servidor, copia os links e tenta abrir popups. |
| API VT | Consulta todos via API key, com ~16 s entre requisições. |
| Scan local | Envia todos os arquivos para ClamAV + YARA, em sequência. |
| Limpar | Esvazia a bandeja. |

## Config

- **VirusTotal API**: campo de key (não persistido), status do servidor e limite de 4 req/min.
- **Scan Local**: saúde de ClamAV/YARA e caminho do banco do ClamAV. Comandos para instalar engines e atualizar o banco.
- **Privacidade & limites**: resumo do fluxo e dos limites.

## Automação e CLI

O horash é primariamente uma UI, mas expõe três pontos de automação:

### Servidor HTTP

Com `python src/server.py` (ou o app) rodando, use os endpoints locais. Catálogo completo em [reference/endpoints.md](reference/endpoints.md).

```ps1
curl.exe http://127.0.0.1:8765/ping
curl.exe http://127.0.0.1:8765/health/scan

curl.exe -X POST `
  -H "X-Filename: sample.bin" `
  --data-binary "@sample.bin" `
  http://127.0.0.1:8765/scan
```

### `src/scanner.py`

Roda ClamAV + YARA em um arquivo e imprime o JSON agregado:

```ps1
python src/scanner.py
python src/scanner.py caminho\do\arquivo.bin
```

Sem argumento, imprime os caminhos encontrados pelos engines. Não define código de saída explícito: retorna `0` no caminho normal e `1` em exceção não tratada.

### `src/vt_incognito.py`

Abre um hash SHA-256 ou URL do VirusTotal em aba anônima:

```ps1
python src/vt_incognito.py e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
python src/vt_incognito.py https://www.virustotal.com/gui/file/<sha256>
```

Códigos de saída:

| Código | Significado |
|---|---|
| `0` | Navegador aberto (anônimo ou fallback). |
| `1` | Uso incorreto, hash/URL inválido ou exceção não tratada. |
| `2` | Nenhum navegador conseguiu abrir a URL. |

### Códigos de saída dos executáveis

| Comando | Código | Quando |
|---|---|---|
| `python src/main.py` | `0` | Janela fechada, ou porta 8765 já ocupada (abre o navegador). |
| `python src/main.py` | `1` | O servidor não subiu dentro de 10 s. |
| `python src/server.py` | — | Processo de longa duração; `Ctrl+C` encerra. |
| `horash.bat` | `0` | Python encontrado e app executado. |
| `horash.bat` | `1` | Nenhum Python real encontrado. |

## Atualizar

O mesmo comando atualiza o código:

```ps1
irm https://raw.githubusercontent.com/seiti-kg/horash/main/tools/install.ps1 | iex
```

- O código em `%LOCALAPPDATA%\horash` é substituído.
- `clamav/` e `yara/` são preservados.
- Se os engines já existem, o instalador **não** baixa assinaturas/regras novas.

Para atualizar as assinaturas do ClamAV:

```ps1
$root = "$env:LOCALAPPDATA\horash"
& "$root\clamav\freshclam.exe" --datadir="$root\clamav\db"
```

Para atualizar as regras do YARA:

```ps1
powershell -ExecutionPolicy Bypass -File "$env:LOCALAPPDATA\horash\tools\install_yara.ps1" -Package full
```

`-Package` aceita `core`, `extended` ou `full`.

## Desinstalar

```ps1
powershell -ExecutionPolicy Bypass -File "$env:LOCALAPPDATA\horash\tools\uninstall.ps1"
```

O desinstalador remove:

- a pasta `%LOCALAPPDATA%\horash` (inclui ClamAV, YARA, docs e shim);
- os atalhos da área de trabalho e do menu Iniciar;
- o diretório do shim do PATH do usuário.

Ele **não** remove:

- o Python instalado;
- pacotes `pip` instalados no Python do usuário;
- o cache de browsers do Playwright (normalmente em `%LOCALAPPDATA%\ms-playwright`);
- arquivos temporários que tenham sobrado de um scan interrompido.

## Instaladores `.exe` (opcional, build local)

O repositório tem dois instaladores Inno Setup:

- `tools/horash_setup.iss`: setup leve (~12 MB), baixa os engines sob demanda.
- `tools/horash_setup_offline.iss`: setup offline (~400 MB), embute ClamAV/YARA.

Eles **não são publicados nas releases**; são artefatos de build local. Veja [desenvolvimento](development.md#build).

## Sessão e privacidade

- Sem `localStorage`, cookies ou telemetria.
- A bandeja e a API key vivem só na memória e são limpas em `beforeunload`.
- O hash vai ao VT; os bytes vão apenas para `127.0.0.1` e para os processos do ClamAV/YARA.
- O temporário é apagado no `finally` do `/scan`; isso **não** é apagamento seguro e uma queda do processo pode deixar o arquivo em `%TEMP%`.

Veja [funcionalidades e limites](features.md) e [segurança e privacidade](security.md).

## Problemas comuns

**`horash` não é reconhecido**

Abra um terminal novo. Confira se `%LOCALAPPDATA%\horash\bin` está no PATH do usuário; o shim é `horash.cmd`.

**`python` abre a Microsoft Store**

É o alias da Store, não um Python real. Instale o Python 3.11+ (winget, python.org ou Microsoft Store) e rode o instalador de novo. O `horash.bat` também ignora esse alias.

**Smart App Control bloqueia um `.exe` construído localmente**

O `.exe` não é assinado. Use `horash.bat` ou rode via Python; o `horash.bat` chama um `python.exe` assinado e costuma passar pelo SAC.

**ClamAV ou YARA aparecem como indisponíveis**

```ps1
powershell -ExecutionPolicy Bypass -File "$env:LOCALAPPDATA\horash\tools\bootstrap.ps1"
```

Verifique também `http://127.0.0.1:8765/health/scan` com o app aberto.

**O scrape do VirusTotal falha**

O scrape depende de Chromium, rede e do Cloudflare do VT. Reinstale o browser:

```ps1
python -m playwright install chromium
```

Para resultado confiável, use uma API key em **Config → VirusTotal API**. Veja [limitações](features.md#limitações-conhecidas).

**A porta 8765 já está em uso**

O `main.py` detecta a porta ocupada e tenta abrir `http://localhost:8765` no navegador em vez de subir outro servidor. Feche a instância antiga ou o processo que está na porta.

**Antivírus sinaliza o `horash.exe`**

O binário é unsigned e o PyInstaller às vezes gera falso positivo. Prefira a instalação via `install.ps1`/`horash.bat`. Não há assinatura de código no projeto.
