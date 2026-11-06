# Validação do incremento contábil — 06/11/2026

Validação posterior de esquema 16: consulte `frente-contabil-integracao-esquema16.md` e o relatório final por SHA. Os resultados abaixo são históricos.

Estado posterior do esquema 15: consulte `frente-contabil-integracao-esquema15.md` e o relatório final da execução, preservando os resultados abaixo como históricos.

Validação posterior do esquema 14: consulte `frente-contabil-integracao-esquema14.md`; este arquivo preserva o registro inicial, não o resultado da combinação com o PR #11.

Registro histórico da validação inicial. A validação conjunta posterior usa a base fiscal `64378f6`, esquema 13, e está em `frente-contabil-integracao-esquema13.md`: 294 testes da aplicação, 18 de distribuição (um omitido) e 30 de ferramentas. O fechamento por módulo e a tributação parametrizada daquela base foram preservados. As referências abaixo à ausência de integração fiscal descrevem somente a etapa inicial.

Base: `develop` em `22ebdb14d812980dac532cd7c0403c2f811f559e`. Branch local: `feat/modulo-contabil-integrado`. Árvore isolada: `/workspace/escrituracao-contabil-contabil`. Não foi incorporado o commit local da frente fiscal; reunir as alterações e testar novamente a combinação é etapa posterior.

## Resultado local executado

| Verificação | Resultado real |
|---|---|
| `python3 scripts/build.py check` após a última alteração de código | Aprovado, exit 0 |
| Suíte da aplicação | 257 testes aprovados, incluindo 12 novos testes contábeis |
| Empacotamento | 18 testes, aprovados; DPAPI omitido por exigir Windows |
| Ferramentas de entrega/CI | 27 testes aprovados |
| Templates pré-compilados | Conferência aprovada, sem mudanças de templates/renders |
| Python e JavaScript | `compileall`, sintaxe Node e matemática monetária JS aprovados |
| Ativos e smoke | Ícones e smoke de portal/login/CSRF/persistência aprovados |
| `python3 qa/accounting_reports.py` | Chromium local e portal aprovados |
| `python3 qa/integrated_flow.py` | Fluxo integrado local e portal aprovados |
| `git diff --check` | Aprovado |

Os 10 testes unitários novos cobrem recorte por data e conta, continuidade de abertura, natureza/sinal D/C, hierarquia explícita inclusive códigos sem prefixo e grupos vazios, totais sem dupla contagem, planos separados, rejeição de filtros desconhecidos, rascunhos fora do livro, integridade de movimentos, preservação da transação do chamador, reinício determinístico e ausência de migração. Os dois testes HTTP novos cobrem as fronteiras reais local/token e portal/autenticação/escopo de empresa, rejeição de POST e de filtros sem suporte.

O QA Chromium preenche o relatório pela interface e confere saldo inicial de 0,10, movimento de 0,20 e saldo final de 0,30. Confere também o balancete sintético, a invalidação da consulta ao alterar filtros, a limpeza ao trocar empresa e ausência de erros JavaScript. Foram verificados os modos desktop de 1440 px e móvel de 390 px, sem transbordamento horizontal da página ou do iframe. Tabelas largas mantêm rolagem interna.

As quatro imagens produzidas com dados sintéticos foram inspecionadas por pixels em `/tmp/accounting-reports-qa/`: `local-desktop.png`, `local-mobile.png`, `portal-desktop.png`, `portal-mobile.png`. São evidências do projeto próprio, não os prints de referência. Não foram incorporadas ao Git ou publicadas.

O fluxo integrado anterior continua aprovado: recepção → organização → operação → conferência → escrituração → abertura → preservação de rascunhos/reload → liquidação → livros/download → encerramento. Não foram reativados gravadores legados.

## Limites desta validação

- Ambiente Linux com Python 3.12. Não foram executados CI remota, builds nativos Windows x86/x64, DPAPI, binários Windows distribuídos ou imagem Docker publicada. O incremento não altera empacotamento, workflows ou Dockerfile.
- `actionlint` não estava disponível e não foi executado; nenhum workflow foi alterado. Os testes locais de ferramentas de entrega não substituem esse validador ou a CI do SHA que futuramente for publicado.
- O ambiente emitiu aviso de depreciação do adaptador Starlette/httpx; os testes passaram. As dependências do projeto não foram alteradas nesta tarefa.
- Não houve validação com Prosoft, PVA, fontes reais, assinatura de livro, leiautes bancários ou regras de conciliação. Os 26 anexos continuam sem bytes acessíveis; seu inventário e bloqueio estão em `frente-contabil-levantamento-aberto.md`.
- Bloqueio independente por módulo/empresa/período foi contratado e documentado, mas ainda não implementado. O encerramento geral existente não comprova esse requisito.
- Não houve push, PR publicado, merge, release, upload de dados ou implantação.

## Arquivos para integração

Preexistentes alterados:

- `src/accounting_api.py`: registra a rota GET `accounting-report`; nenhum roteador fiscal foi editado.
- `src/web/workbench.js`: adiciona o componente independente de filtros no painel de livros, via Vue Teleport; templates e renders compartilhados ficam intactos.

Novos:

- `src/work_reports.py`.
- `tests/test_work_reports.py`.
- `tests/test_work_reports_http.py`.
- `tests/server/test_work_reports_http.py`.
- `qa/accounting_reports.py`.
- `docs/frente-contabil-levantamento-aberto.md`.
- `docs/frente-contabil-validacao.md`.
- `docs/frente-contabil-pr.md`.

A migração contábil não foi incrementada. O esquema-base permanece 10; a frente fiscal prepara 11. A futura migração para bloqueios por módulo deve ser alocada depois de reunir as branches. Não aplicar duas migrações diferentes com a mesma versão.
