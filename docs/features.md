# Funcionalidades e limites

[← Uso](usage.md) · [README](../README.md) · [Arquitetura →](architecture.md)

## Escopo atual

O horash faz triagem local de arquivos em lote no Windows:

- **Hash SHA-256 local** — `WebCrypto` abaixo de 50 MiB; `js-sha256` em streaming de 4 MiB acima disso. O arquivo não é enviado ao VT.
- **Consulta ao VirusTotal por hash** — automática até 650 MiB. Com API key usa a API oficial e mostra `X / N` + logs por engine; sem key usa Playwright no site do VT.
- **Scan local** — ClamAV + YARA via `POST /scan`, com veredito explícito **Limpo**, **Infectado** ou **Parcial**.
- **Bandeja em lote** — arrastar/soltar, Ctrl+V, ações em lote (copiar hashes, abrir VT, API VT, scan local).
- **UI nativa** — pywebview/WebView2, com fallback para o navegador.
- **Instalação sem `.exe`** — `install.ps1` baixa o código de `main`, instala dependências, Python (se faltar), Chromium, ClamAV e YARA.
- **Servidor loopback-only** — `127.0.0.1:8765`, sem persistência e sem telemetria.

Detalhes de operação: [uso](usage.md). Catálogo HTTP: [reference/endpoints.md](reference/endpoints.md). Engines: [reference/engines.md](reference/engines.md).

## Status atual

| Item | Estado |
|---|---|
| Versão em `main` | `0.4.0-beta` (`src/version.py`). |
| Última tag publicada | `v0.3.0-beta`. O código de `main` está 15 commits à frente dessa tag. |
| Plataforma | Windows 10/11 x64. |
| Distribuição | `install.ps1` via `irm`; as releases publicam apenas os scripts `.ps1`, não binários. |
| Instaladores `.exe` | Existem no repositório, mas são artefatos de build local; não são publicados nas releases. |
| Testes | `unittest` da stdlib; 36 testes no estado atual, com engines mockados. |
| Maturidade | Beta; sem assinatura de código e sem canal stable/beta separado. |

Atualize esta seção ao taguear uma release.

## Limitações conhecidas

### Limites numéricos

| Item | Limite | Efeito |
|---|---|---|
| Consulta ao VirusTotal | 650 MiB (~682 MB) | Acima disso o VT não é consultado; o arquivo vai direto para o scan local. |
| ClamAV | 2000 MiB (~2,1 GB) | Acima disso o ClamAV é ignorado; o YARA ainda roda e o resultado fica **Parcial**. |
| Upload para `/scan` | 10 GiB | Acima disso o servidor responde `413`. |
| Hash em memória | 50 MiB | Abaixo disso usa `WebCrypto` com o arquivo inteiro; acima, streaming de 4 MiB. |
| Timeout do ClamAV | 600 s | Vira `error` e o resultado fica parcial. |
| Timeout do YARA | 300 s | Vira `error` e o resultado fica parcial. |
| Scrape do VT | ~25 s por arquivo | Pode falhar por Cloudflare, rate limit ou mudança no DOM. |
| API pública do VT | ~4 req/min | O lote espera ~16 s entre consultas. |
| Upload do VT (site) | 650 MiB | O horash nunca envia o arquivo; só consulta por hash. |

`MiB` = 1024² bytes. A UI às vezes rotula como “MB/GB”.

### Limites de cobertura

- **VirusTotal por hash só encontra arquivos já vistos pelo VT.** Arquivo novo retorna 404; o horash então cai no scan local. Ele não faz upload para o VT.
- **ClamAV + YARA não são um sandbox.** Não desempacotam, não emulam, não executam o arquivo e não detectam comportamento em tempo real.
- **YARA é assinatura estática.** O pacote `full` cobre mais famílias e aumenta falsos positivos. Um match é suspeita, não veredito.
- **Banco do ClamAV pode estar velho.** O `freshclam` só roda no bootstrap/instalação ou quando você executa manualmente; o app não agenda atualização.
- **YARA sem `.yarc` fica mais lento.** O `.yarc` é usado quando existe e é mais novo que o `.yar`.
- **Scrape sem API key é frágil.** Cloudflare, rate limit, layout do site e rede podem derrubar a consulta. Use API key para resultado confiável.
- **Um engine só nunca dá “Limpo”.** Se ClamAV ou YARA estiver indisponível, o resultado é **Parcial**.
- **Arquivos muito grandes dependem de espaço em `%TEMP%`.** O `/scan` grava uma cópia temporária do tamanho do arquivo.
- **Batch é sequencial.** Vários arquivos grandes podem levar minutos; o progresso é por arquivo.
- **Não há cancelamento de scan em andamento.** Fechar o app/aba interrompe a UI, não necessariamente o subprocesso do engine.

### Limites de plataforma e sessão

- **Windows 10/11 x64.** Servidor, engines e instaladores são específicos de Windows.
- **Porta fixa `8765`.** Se estiver ocupada, o `main.py` não sobe outro servidor; tenta abrir a instância existente no navegador.
- **Sem persistência.** Bandeja e API key vivem na memória e são limpas em `beforeunload`. Recarregar/fechar a página perde o estado e exige reselecionar os arquivos para o scan local.
- **O servidor não tem autenticação.** Qualquer processo local pode chamar `127.0.0.1:8765`. A validação de `Host`/`Origin`/`Sec-Fetch-Site` protege contra páginas web, não contra código local malicioso.
- **Temporário não é apagado com segurança.** O `finally` remove o arquivo, mas uma queda do processo pode deixá-lo em `%TEMP%`, e o conteúdo pode ser recuperável no disco.
- **Sem assinatura de código.** O `.exe` do PyInstaller pode gerar falso positivo; prefira `install.ps1`/`horash.bat`.
- **Sem atualização automática do app.** Rodar o instalador de novo baixa o `main`; não há canal stable/beta separado.

### Lacunas técnicas conhecidas

- **Fallback `yara-python` não é detectado pelo scanner.** Se nenhum binário oficial do YARA baixar, o instalador grava `yara64.bat`, mas `find_yara()` procura `yara64.exe`, `yara.exe` ou `yara`; o engine pode aparecer indisponível.
- **Parsing do scrape não tem teste dedicado.** A suíte cobre validação de hash e o endpoint, mas não o parser do DOM/JSON do VT.
- **Sem testes automatizados de UI/navegador.**
- **Sem lint configurado.** O CI roda `compileall` + `unittest`; veja [desenvolvimento](development.md#lint).

## O que o horash não faz

- Não envia o arquivo para o VirusTotal.
- Não instala driver, serviço ou proteção em tempo real.
- Não bloqueia execução nem quarentena arquivos.
- Não limpa o arquivo original; o scan é somente leitura.
- Não funciona em Linux/macOS.
- Não tem telemetria.

## Roadmap e pendências

Não há roadmap público versionado. As pendências técnicas registradas são:

- criar a tag/release `v0.4.0-beta` (o código já está em `0.4.0-beta`);
- corrigir a detecção do fallback `yara-python` no `find_yara()`;
- adicionar testes do parser do `vt_scrape` e da UI;
- decidir sobre assinatura de código dos binários locais.

Essas pendências não são compromisso de prazo. Limitações de operação e escopo estão acima; comportamento atual está em [uso](usage.md).
