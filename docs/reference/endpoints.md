# Endpoints HTTP

[← Uso](../usage.md) · [README](../../README.md) · [Arquitetura →](../architecture.md)

O servidor local escuta **somente em `127.0.0.1:8765`** e serve a UI em `web/`. Não há autenticação: qualquer processo local consegue chamar a API. A proteção existente é contra requests vindos de páginas web (CSRF/DNS rebinding), não contra malware local.

## Rotas

| Método | Rota | Função |
|---|---|---|
| GET | `/ping` | Health check do servidor. |
| GET | `/health/scan` | Presença e caminhos de ClamAV, YARA, regras e banco. |
| GET | `/open?hash=<sha256>` | Abre `virustotal.com/gui/file/{hash}` em aba anônima. |
| GET | `/vt-scrape?hash=<sha256>` | Consulta o VT via Playwright e devolve stats. |
| POST | `/scan` | Recebe bytes, roda ClamAV + YARA e apaga o temporário. |
| GET | `/` ou `/index.html` | UI. |
| GET | `/<arquivo>` | Arquivos estáticos de `web/`. |
| OPTIONS | qualquer rota | Preflight CORS. |

## Segurança de origem

`_request_allowed` rejeita com `403`:

- `Host` presente cujo hostname não seja `localhost`, `127.0.0.1` ou `::1`;
- `Origin` presente que não seja `http(s)://localhost`, `http(s)://127.0.0.1` ou `http(s)://[::1]` (inclui `Origin: null`);
- `Sec-Fetch-Site: cross-site` ou `Sec-Fetch-Site: same-site`.

Headers ausentes (por exemplo, `curl.exe`) são aceitos. Requisições locais same-origin também.

CORS:

- `Access-Control-Allow-Origin` só é ecoado para origem local permitida.
- Métodos: `GET, POST, OPTIONS`.
- Headers: `Content-Type, X-Filename`.
- Todas as respostas levam `Cache-Control: no-store`.

## GET /ping

```json
{"status":"ok","server":"horash","version":"0.4.0-beta"}
```

```ps1
curl.exe http://127.0.0.1:8765/ping
```

## GET /health/scan

Retorna o resultado de `scanner.check_scanners()`:

```json
{
  "clamav_path": "C:\\Users\\...\\horash\\clamav\\clamscan.exe",
  "clamav_available": true,
  "clamav_db": "C:\\Users\\...\\horash\\clamav\\db",
  "yara_path": "C:\\Users\\...\\horash\\yara\\yara64.exe",
  "yara_available": true,
  "yara_rules": "C:\\Users\\...\\horash\\yara\\rules\\full.yar",
  "yara_rules_available": true,
  "yara_compiled": "C:\\Users\\...\\horash\\yara\\rules\\full.yarc"
}
```

Caminhos ausentes voltam como `null`; os booleanos indicam disponibilidade.

```ps1
curl.exe http://127.0.0.1:8765/health/scan
```

## GET /open?hash=<sha256>

Valida o hash (64 hex), abre o relatório no navegador com modo anônimo quando possível e responde:

```json
{"status":"ok incognito","hash":"<sha256>"}
```

- `status` pode ser `ok incognito` ou `fallback normal`.
- `400` se o hash não for SHA-256 válido.
- `500` se o helper falhar.

Não é um redirect HTTP: o navegador é aberto pelo processo Python.

```ps1
curl.exe "http://127.0.0.1:8765/open?hash=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
```

## GET /vt-scrape?hash=<sha256>

Usa Playwright/Chromium headless para abrir o site do VT e interceptar os stats. Pode levar ~25 s.

Sucesso (`200`):

```json
{
  "available": true,
  "stats": {
    "malicious": 0,
    "suspicious": 0,
    "undetected": 60,
    "harmless": 0,
    "timeout": 0,
    "failure": 0,
    "confirmed-timeout": 0,
    "type-unsupported": 12
  },
  "results": {},
  "url": "https://www.virustotal.com/gui/file/<sha256>",
  "time_ms": 12000,
  "method": "playwright"
}
```

- `400`: hash inválido.
- `502`: não conseguiu extrair stats (Cloudflare, timeout, DOM mudou, arquivo não encontrado).
- `500`: exceção inesperada.

Em falha, o corpo pode vir com `available: false`, `error` e, no caso de bloqueio do site, `cloudflare: true`.

## POST /scan

Headers:

- `X-Filename`: nome do arquivo, URL-encoded. O servidor faz `unquote`, extrai o basename e limita a 255 caracteres; o valor é só metadado.
- `Content-Length`: obrigatório e maior que zero.

Limites:

- Corpo máximo: **10 GiB** (`413` acima disso).
- Corpo vazio: `400`.
- Upload truncado (menos bytes que o `Content-Length`): `400` com `missing_bytes`.
- O temporário é criado em `%TEMP%` como `*.bin` e apagado no `finally`.

Resposta `200`:

```json
{
  "filename": "sample.bin",
  "size": 12345,
  "infected": false,
  "signatures": [],
  "clamav": {
    "available": true,
    "status": "clean",
    "infected": false,
    "signature": null,
    "output": "OK",
    "time_ms": 812
  },
  "yara": {
    "available": true,
    "status": "clean",
    "infected": false,
    "output": "OK",
    "time_ms": 45
  },
  "complete": true,
  "warnings": [],
  "summary": "Limpo",
  "upload_time_ms": 90,
  "scan_time_ms": 857,
  "total_time_ms": 947
}
```

Status de engine: `clean`, `infected`, `skipped`, `unavailable`, `error`.

- `complete` só é `true` quando ClamAV **e** YARA concluíram (`clean`/`infected`).
- Se um engine foi `skipped`/`unavailable`/`error`, `complete` é `false`, `warnings` explica e `summary` fica “Parcial”.
- Se houve detecção com cobertura incompleta, `summary` termina em `(parcial)`.
- Se nenhum engine concluiu, a resposta inclui `error: "Nenhum engine concluiu o scan"`.

Exemplo:

```ps1
curl.exe -X POST `
  -H "X-Filename: sample.bin" `
  --data-binary "@sample.bin" `
  http://127.0.0.1:8765/scan
```

## Códigos de erro

| Código | Quando |
|---|---|
| `400` | hash inválido, corpo vazio, `Content-Length` inválido ou upload truncado. |
| `403` | `Host`/`Origin` não local ou `Sec-Fetch-Site` cross-site/same-site. |
| `404` | `POST` em rota desconhecida. |
| `413` | corpo acima de 10 GiB. |
| `500` | exceção no servidor. |
| `502` | scrape do VT sem stats. |

## Implementação

- `src/server.py`: handlers HTTP, validação de origem, upload e resposta.
- `src/scanner.py`: engines, seleção de regras e veredito agregado.
- `src/vt_scrape.py`: Playwright e parsing dos stats.
- `src/vt_incognito.py`: abertura do navegador em modo privado.

Testes de contrato e de segurança ficam em `tests/test_server.py`, `tests/test_scanner.py` e `tests/test_vt_incognito.py`.
