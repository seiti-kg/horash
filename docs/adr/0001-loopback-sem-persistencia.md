# 0001 — Servidor loopback-only e estado efêmero

- **Status:** Aceita
- **Data:** 2026-11-05

## Contexto

O horash processa arquivos que podem ser sensíveis e precisa de um processo local para rodar ClamAV/YARA, receber uploads do navegador e abrir o VirusTotal em modo anônimo. Não há backend remoto nem banco de dados. A UI roda em WebView/navegador e o servidor é um processo Python separado.

Um servidor HTTP local aberto em todas as interfaces permitiria acesso de outros dispositivos da rede. Persistir bandeja, hashes ou API key criaria histórico de arquivos sensíveis e ampliaria a superfície de vazamento.

## Decisão

- O servidor escuta apenas `127.0.0.1:8765`.
- Não há autenticação; a proteção é de origem (`Host`, `Origin`, `Sec-Fetch-Site`) para bloquear requests de páginas web.
- O estado da UI (bandeja e API key) vive apenas na memória e é limpo em `beforeunload`.
- O arquivo enviado ao `/scan` é gravado em `%TEMP%` e removido no `finally`; não há persistência intencional.
- Não há `localStorage`, cookies, banco ou arquivo de configuração.

## Consequências

- O app é de usuário único e não funciona como serviço remoto/multiusuário.
- Qualquer processo local consegue chamar a API local; o limite de origem não protege contra malware já em execução na máquina.
- Não há histórico entre sessões; recarregar/fechar exige reselecionar arquivos.
- A remoção do temporário é lógica, não segura; uma queda pode deixar o `.bin` em `%TEMP%`.
- O servidor não pode ser exposto na rede sem uma decisão explícita que substitua esta ADR (autenticação, TLS e autorização passariam a ser necessários).
