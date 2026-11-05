# Desenvolvimento

[← Arquitetura](architecture.md) · [README](../README.md) · [Uso →](usage.md)

## Rodar do código

```ps1
git clone https://github.com/seiti-kg/horash.git
cd horash
python -m pip install -r requirements.txt

# baixa ClamAV + YARA full (primeira vez: ~10+ min).
# sem isso, o YARA usa só o fallback de 11 regras e o ClamAV pode aparecer indisponível.
powershell -ExecutionPolicy Bypass -File tools/bootstrap.ps1

# necessário apenas para o scrape do VT sem API key:
python -m playwright install chromium

python src/main.py                 # app com janela pywebview
# ou:
python src/server.py               # só o servidor; abra http://localhost:8765
# ou, no Explorer:
horash.bat
```

O `horash.bat` usa o diretório do próprio arquivo (não o cwd) e ignora o alias da Microsoft Store.

## Estrutura do código

- `src/`: app Python (servidor, scanner, scrapers, entrypoint).
- `web/`: UI estática (HTML/CSS/JS, sem build de frontend).
- `tests/`: testes `unittest` com engines mockados.
- `tools/`: instaladores PowerShell, bootstrap e scripts Inno Setup.
- `scripts/`: automação de build local.
- `docs/`: esta documentação.
- `yara/fallback.yar`: 11 regras versionadas; `yara/rules/` e `clamav/` são gerados e ignorados.

Árvore completa e responsabilidades por módulo: [arquitetura](architecture.md#estrutura-do-repositório).

## Testes

```ps1
python -m unittest discover -s tests -v
```

A suíte usa apenas a stdlib (`unittest`). Não exige ClamAV/YARA instalados: os engines são mockados. Cobre:

- contrato de veredito (`tests/test_scanner.py`): limpo, infectado, parcial, engine indisponível, nenhum engine;
- seleção de regras: full vs fallback, `.yarc` mais novo vs fonte;
- limites: arquivo grande pulado sem subprocesso, binário ausente, regras ausentes;
- servidor (`tests/test_server.py`): ping, index, Host/Origin/Sec-Fetch-Site, `/scan`, upload vazio/truncado, `/open` e `/vt-scrape` com hash inválido;
- normalização do `vt_incognito.py`.

Rode também `python -m compileall -q src tests` antes de enviar.

## Lint

Não há lint, formatter ou type checker configurado no repositório. O CI valida a sintaxe com `compileall` e roda a suíte; não há etapa separada de lint. Se `ruff`/`flake8` for adicionado, configure a etapa no CI e documente o comando aqui antes de torná-lo obrigatório.

## CI

`.github/workflows/ci.yml` roda em `windows-latest` a cada push/PR:

1. checkout;
2. Python 3.11;
3. `python -m compileall -q src tests`;
4. `python -m unittest discover -s tests -v`.

## Build

### Executável leve

```ps1
python -m PyInstaller horash.spec --noconfirm --clean
# dist/horash.exe (~12 MB)
```

O spec embute `web/` e `src/`, mas não embute ClamAV/YARA. Nesse modo o app usa os engines instalados ao lado do exe ou baixados pelo `bootstrap.ps1`.

### Executável offline

```ps1
$env:HORASH_OFFLINE = "1"
python -m PyInstaller horash.spec --noconfirm --clean
```

Com `HORASH_OFFLINE=1`, o spec inclui `clamav/` e `yara/` no bundle (é preciso ter rodado o bootstrap antes).

### Instaladores Inno Setup

Requer Inno Setup 6:

```ps1
iscc tools\horash_setup.iss
iscc tools\horash_setup_offline.iss
```

- `horash_setup.exe` (~12 MB): baixa os engines sob demanda.
- `horash_setup_offline.exe` (~400 MB): inclui ClamAV/YARA.

Os scripts `scripts\build.bat` e `scripts\build_setup.bat` automatizam a sequência.

Os `.exe`/setups são artefatos **locais**; as releases publicam apenas os scripts `.ps1` (veja abaixo).

## Release

`.github/workflows/release.yml` dispara em tags `v*` (e `workflow_dispatch`):

1. roda `compileall` e a suíte de testes;
2. publica no GitHub Release:
   - `tools/install.ps1`
   - `tools/uninstall.ps1`
   - `tools/bootstrap.ps1`
3. gera release notes automaticamente;
4. marca como prerelease quando a tag contém `-beta`.

Fluxo:

```ps1
git tag v0.4.0-beta
git push origin v0.4.0-beta
```

Não há upload de binários. Quem instala usa `install.ps1`, que baixa o código de `main`.

## Versionamento

Mantenha em sincronia:

- `src/version.py` (`__version__`) — usado por `/ping` e `server_version`;
- `tools/horash_setup.iss` e `tools/horash_setup_offline.iss` (`MyAppVersion`) — exibidos pelo Inno Setup;
- `docs/features.md` (status atual) — versão, última tag e estado de release.

Atualize os três ao taguear uma release.

Para ver o estado atual do checkout:

```ps1
git describe --tags --always
$tag = git describe --tags --abbrev=0
git log --oneline "$tag..HEAD"
```

## Convenções

- Python 3.11+; servidor e testes usam apenas stdlib.
- Windows é a plataforma-alvo; use caminhos e APIs compatíveis.
- Não introduza persistência (banco, `localStorage`, cookies) sem decisão explícita.
- Não adicione dependência externa na UI; nada de CDN/fontes remotas.
- O servidor continua loopback-only.
- Falha de engine deve continuar resultando em **Parcial**, nunca “Limpo”.
- O arquivo temporário do `/scan` deve continuar sendo removido no `finally`.
- O VT continua recebendo apenas o hash; não implemente upload de arquivo.

## Documentação

- `README.md` é a landing page: descrição, quick start e índice.
- `docs/usage.md`: instalação, execução, CLI e solução de problemas.
- `docs/features.md`: escopo, status, limitações e pendências.
- `docs/architecture.md`: componentes, fluxos e decisões.
- `docs/security.md`: modelo de ameaça, privacidade e fluxo de dados.
- `docs/reference/endpoints.md` e `docs/reference/engines.md`: catálogos de API e engines.
- `docs/adr/`: decisões arquiteturais no formato Status/Contexto/Decisão/Consequências.

Regras:

- Um arquivo por assunto; nomes em kebab-case.
- Links relativos entre docs; o README aponta para a fonte única.
- Atualize a documentação no mesmo PR que altera comportamento.
- **Documentação gerada:** não há arquivos gerados por build/script hoje; todos são mantidos manualmente. Se um arquivo passar a ser gerado, escreva no topo “Gerado por `<comando>`; não edite manualmente” e documente o comando neste arquivo.
- Os instaladores Inno copiam `docs/` para `{app}\docs`; mantenha os caminhos relativos válidos.
