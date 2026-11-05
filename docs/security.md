# Segurança e privacidade

[← Funcionalidades](features.md) · [README](../README.md) · [Arquitetura →](architecture.md)

## Modelo de ameaça

O horash é um app local de usuário único. O servidor HTTP não tem autenticação e roda em `127.0.0.1:8765`; qualquer processo ou usuário local consegue chamá-lo. As defesas de `Host`/`Origin`/`Sec-Fetch-Site` existem para impedir que uma página web aberta no navegador faça requests cross-site para o servidor local (CSRF/DNS rebinding), não para conter malware local.

O app não é um sandbox: ClamAV e YARA recebem o arquivo temporário e o processo do app tem acesso ao disco do usuário.

## Fluxo de dados

| Dado | Para onde vai |
|---|---|
| Bytes do arquivo | Ficam na máquina. Vão para o servidor local (`127.0.0.1`) e para `clamscan`/`yara`. |
| SHA-256 | Vai ao VirusTotal na consulta por hash (API ou site via Playwright). |
| API key do VT | Vai direto do navegador para `virustotal.com`; o servidor local não a recebe. |
| Stats do VT | Voltam para a UI; não são persistidos. |
| Telemetria | Nenhuma. |

O horash **não** faz upload do arquivo ao VirusTotal. A consulta é sempre por hash. Se o hash não existe no VT, não há resultado.

## Servidor local

- Escuta somente `127.0.0.1:8765` (`HOST = "127.0.0.1"`).
- Rejeita `Host` que não seja `localhost`, `127.0.0.1` ou `::1`.
- Rejeita `Origin` que não seja local (inclui `null`).
- Rejeita `Sec-Fetch-Site: cross-site` e `same-site`.
- CORS só ecoa origem local permitida.
- `Cache-Control: no-store` em todas as respostas.
- `/open` e `/vt-scrape` validam hash SHA-256 (64 hex) antes de qualquer ação.
- `/scan` sanitiza `X-Filename` com `unquote` + `basename` + limite de 255 caracteres; o nome é só metadado e nunca vira caminho.
- `/scan` limita o corpo a 10 GiB e detecta upload truncado.
- A UI e os arquivos estáticos são servidos de `web/`; não há endpoint para ler arquivos arbitrários do disco.

Isso não impede um processo local de chamar a API, ler a resposta ou rodar um scan. Para uso em máquina compartilhada, trate o app como ferramenta de confiança local.

## Arquivo temporário

O `/scan` grava o corpo em um `NamedTemporaryFile(delete=False, suffix=".bin")` em `%TEMP%`, roda os engines e remove o arquivo no `finally`.

- O nome é aleatório; o nome original não é usado no disco.
- Se o processo for morto (Task Manager, queda de energia), o `finally` pode não rodar e o `.bin` pode ficar em `%TEMP%`.
- A remoção é lógica, não segura: não há sobrescrita. O conteúdo pode ser recuperável no disco.
- O scan é somente leitura; o arquivo original não é alterado.

## API key

- Fica no valor do campo `#apiKey` (input `type=password`), apenas em memória.
- É enviada pelo navegador/WebView direto para `https://www.virustotal.com/api/v3/files/{hash}` no header `x-apikey`.
- O servidor local não vê a key e ela não é gravada em disco, log ou `localStorage`.
- É limpa em `beforeunload` (fechar/recarregar).
- Ferramentas de desenvolvedor do WebView/navegador podem inspecionar a memória enquanto a página está aberta.

## Modo anônimo do VT

`/open` tenta, nesta ordem:

1. Chrome `--incognito`;
2. Edge `--inprivate`;
3. Firefox `--private-window`;
4. navegador padrão, sem flags de anonimato.

O modo privado evita histórico/cookies locais, mas não esconde a consulta do VirusTotal, do provedor ou da rede. O botão só abre o relatório; não faz upload.

## Scrape sem API key

Sem key, o servidor usa Playwright com Chromium headless para abrir o site do VT:

- flags `--no-sandbox`, `--disable-blink-features=AutomationControlled`, `--disable-dev-shm-usage`;
- user-agent de Chrome, viewport e locale fixos;
- interceptação das respostas de API do próprio site.

A consulta sai da sua máquina para o VT normalmente. Cloudflare pode bloquear; o modo não é garantido.

## Downloads e checksums

O `install.ps1` e o `bootstrap.ps1` baixam de:

- `github.com/seiti-kg/horash` (código e scripts);
- `github.com/Cisco-Talos/clamav` / `clamav.net` (ClamAV 1.5.4, SHA-256 conferido);
- `github.com/YARAHQ/yara-forge` (regras; SHA-256 quando o GitHub informa o digest);
- `python.org` ou `winget` (Python, se necessário);
- PyPI (`requirements.txt`);
- CDN do Playwright (Chromium).

O código é baixado do branch `main`, não de uma tag assinada. Para ambientes sensíveis, audite o commit e faça um checkout fixo em vez de usar `irm | iex`.

Não há assinatura de código. O `horash.bat` existe para contornar o Smart App Control chamando um `python.exe` assinado; isso não torna o código do app assinado.

## Boas práticas

- Use API key do VT em vez de scrape quando precisar de resultado confiável.
- Rode `freshclam` periodicamente.
- Não trate “Limpo” como garantia: cobertura parcial é explícita, mas dois engines não cobrem tudo.
- Se o arquivo for sensível, lembre que o hash é enviado ao VT e que o temporário pode ficar em `%TEMP%` após uma queda.
- Feche a bandeja ao terminar; não há persistência intencional.
