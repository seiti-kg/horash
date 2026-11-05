# 0002 — Cobertura parcial explícita no veredito

- **Status:** Aceita
- **Data:** 2026-11-05

## Contexto

O scan local depende de dois engines independentes, ClamAV e YARA. Cada um pode estar ausente, falhar, estourar timeout ou ser ignorado por limite de tamanho. Um resultado “Limpo” quando apenas um engine rodou — ou quando nenhum rodou — daria uma falsa sensação de segurança.

## Decisão

- `complete` só é `true` quando ClamAV **e** YARA terminam em `clean` ou `infected`.
- Qualquer engine `skipped`, `unavailable` ou `error` torna o resultado **Parcial** e gera um item em `warnings`.
- Uma detecção (`infected`) sempre vence e é exibida mesmo se o outro engine falhou; nesse caso o resumo recebe `(parcial)`.
- Se nenhum engine concluir, a resposta inclui `error: "Nenhum engine concluiu o scan"`.
- Os testes de `tests/test_scanner.py` fixam esse contrato com engines mockados.

## Consequências

- O usuário vê cobertura incompleta em vez de um “Limpo” silencioso.
- Mais resultados aparecem como **Parcial**, especialmente sem ClamAV/YARA instalados ou com arquivos acima de 2000 MiB.
- A UI precisa mostrar avisos por engine; o rodapé/config expõe a saúde dos engines.
- Um novo engine só entra no `scan_file` se respeitar o mesmo contrato de status e warnings.
