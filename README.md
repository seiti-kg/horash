<p align="center">
  <img src="assets/logo.png" alt="horash" width="360">
</p>

<p align="center">
  <em>Triagem local de arquivos em lote: SHA-256, consulta ao VirusTotal por hash e scan ClamAV + YARA no Windows.</em>
</p>

---

## Quick start

Windows 10/11 x64 · Python 3.11+ (o instalador baixa se faltar) · internet na primeira execução.

```ps1
irm https://raw.githubusercontent.com/seiti-kg/horash/main/tools/install.ps1 | iex
```

Em um terminal **novo**:

```ps1
horash
```

Requisitos, atualização, desinstalação e solução de problemas: [docs/usage.md](docs/usage.md).

## Documentação

### Começando
- [Uso](docs/usage.md) — instalação, execução, CLI e automação.

### Referência
- [Funcionalidades](docs/features.md) — escopo atual, status e limitações.
- [Endpoints HTTP](docs/reference/endpoints.md) — API local e schemas de resposta.
- [ClamAV + YARA](docs/reference/engines.md) — engines, regras e contrato de veredito.
- [Segurança e privacidade](docs/security.md) — modelo de ameaça e fluxo de dados.

### Projeto
- [Arquitetura](docs/architecture.md) — componentes e fluxos.
- [Desenvolvimento](docs/development.md) — build, testes, lint e CI.
- [ADRs](docs/adr/README.md) — decisões arquiteturais.

## Licença

MIT — veja [LICENSE](LICENSE).
