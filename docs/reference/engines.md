# ClamAV + YARA

[← Endpoints](endpoints.md) · [README](../../README.md) · [Segurança →](../security.md)

O scan local combina dois engines independentes. O veredito só é **Limpo** quando os dois concluem sem detecção; qualquer falha vira **Parcial**.

## ClamAV

- Versão fixada: **1.5.4**.
- Download: release oficial `Cisco-Talos/clamav` (fallback `clamav.net`).
- SHA-256 fixado no instalador: `0d9e0228b2674137ea1a2853566c98a0278ad52ab2582c3d6dbd75373848c395`.
- O checksum é validado antes de tocar na instalação existente.
- Destino: `%LOCALAPPDATA%\horash\clamav` (ou `clamav/` no checkout de dev).
- Banco: `clamav/db` (`main.cvd`/`daily.cvd`).

O `clamscan` roda com:

- `--no-summary --stdout`;
- `--database <clamav/db>` quando o banco é encontrado;
- `--max-filesize=2000M` e `--max-scansize=2000M`;
- timeout de 600 s.

Arquivos acima de **2000 MiB** são marcados como `skipped` sem chamar o subprocesso. Isso evita o comportamento do `--max-filesize`, que retornaria “OK” e esconderia a cobertura parcial.

Atualizar assinaturas:

```ps1
& "$env:LOCALAPPDATA\horash\clamav\freshclam.exe" --datadir="$env:LOCALAPPDATA\horash\clamav\db"
```

O app **não** agenda `freshclam`; o banco só é atualizado quando você roda o comando ou o bootstrap.

## YARA

- Binário oficial do VirusTotal (tenta 4.5.x). Se nenhum mirror funcionar, o instalador tenta `yara-python` via pip, mas o scanner procura `yara64.exe`, `yara.exe` ou `yara`; nesse cenário o engine pode aparecer indisponível.
- Destino: `%LOCALAPPDATA%\horash\yara` (ou `yara/` no checkout).
- Regras: [YARA Forge](https://github.com/YARAHQ/yara-forge), release `latest`.
- Pacotes: `core`, `extended`, `full` (`full` é o padrão).
- O instalador tenta a API do GitHub para obter o asset e o digest SHA-256. Se a API falhar, usa `releases/latest/download` **sem checksum**.
- As regras são compiladas com `yarac64.exe` para `<pacote>.yarc`; o scanner usa o `.yarc` quando ele é mais novo que o `.yar`.

Arquivos:

```
yara/
├── yara64.exe          # não versionado
├── rules/
│   ├── full.yar        # não versionado
│   └── full.yarc       # não versionado
└── fallback.yar        # versionado, 11 regras de emergência
```

Ordem de resolução em `find_yara_rules()`:

1. `yara/rules/full.yar`
2. `yara/rules/extended.yar`
3. `yara/rules/core.yar`
4. `yara/rules.yar`
5. `yara/fallback.yar`
6. `rules/index.yar`
7. primeiro `.yar` encontrado recursivamente em `yara/`

Trocar o pacote:

```ps1
powershell -ExecutionPolicy Bypass -File tools/install_yara.ps1 -Package core
# core | extended | full
```

O `core` é menor e tem menos falso positivo; o `full` cobre mais famílias. As regras instaladas são ignoradas pelo Git.

Se o download falhar, `tools/fix_yara.py` grava o fallback curado em `yara/fallback.yar` e `yara/rules/curated.yar`. O fallback versionado tem **11 regras**.

## Contrato do veredito

`scan_file()` agrega os dois engines:

| Situação | `complete` | `summary` |
|---|---|---|
| ClamAV e YARA `clean` | `true` | `Limpo` |
| Qualquer engine `infected` | `true` se ambos concluíram; `false` se o outro falhou | assinatura; `(parcial)` se incompleto |
| Um engine `skipped`/`unavailable`/`error` | `false` | `Parcial` + avisos |
| Nenhum engine concluiu | `false` | `Parcial...` e `error: "Nenhum engine concluiu o scan"` |

Status possíveis por engine: `clean`, `infected`, `skipped`, `unavailable`, `error`.

- `infected` vence: uma detecção nunca é escondida por falha do outro engine.
- `warnings` lista o motivo de cada engine que não concluiu.
- O YARA roda mesmo quando o ClamAV é ignorado por tamanho.

## Verificar a instalação

Com o app aberto:

```ps1
curl.exe http://127.0.0.1:8765/health/scan
```

No checkout:

```ps1
python src/scanner.py
python src/scanner.py caminho\do\arquivo.bin
```

O primeiro comando imprime os caminhos encontrados; o segundo roda ClamAV + YARA e imprime o JSON agregado.

## Limitações

- Assinaturas YARA são estáticas: não desempacotam, não emulam e não executam o arquivo.
- O pacote `full` aumenta a cobertura e também o risco de falso positivo. Trate um match YARA como **suspeita**, não como veredito de antivírus.
- O banco do ClamAV pode estar desatualizado; atualize com `freshclam`.
- Os testes usam mocks e não exigem ClamAV/YARA instalados; eles cobrem o contrato de cobertura parcial, seleção de regras e limites.

Veja [limitações conhecidas](../features.md#limitações-conhecidas).
