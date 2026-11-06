# Integração contábil com eventos NF-e e esquema 18

## Base e composição

Base fiscal: [PR #20](https://github.com/codisplanfiscalai/escrituracao-contabil/pull/20), branch `feat/eventos-nfe-conferencia`, HEAD **`dcdc7c8850623469e2a09f516b7b6434b8acb3ce`**. O incremento contábil do [PR #19](https://github.com/codisplanfiscalai/escrituracao-contabil/pull/19), `875e87de207f18322bb3dc1134ae9f748ac3d8d1`, foi reaplicado na árvore isolada `/workspace/escrituracao-contabil-compat18`, branch `feat/contabil-compat-esquema18`.

Os sete commits anteriores foram reaplicados como `88c14c2`, `81e4933`, `77d4ac5`, `fcae94f`, `5e010e4`, `cad3091` e `94a223a`. O complemento desta etapa acrescenta os contratos de eventos, o cenário de navegador conjunto e a reconciliação das fixtures de esquema. Não aplicar também os commits originais ou composições anteriores sobre esta árvore. Os PRs e branches anteriores permanecem preservados.

Os arquivos temporários de composição citados no PR fiscal não estavam disponíveis neste executor. A integração foi refeita diretamente a partir do código e validada nesta árvore, sem atribuir a ela os testes ou builds da composição temporária fiscal.

## Frontend compartilhado

Houve um conflito em `src/web/workbench.js`, na fronteira entre o novo mixin de eventos e o painel contábil. A resolução conserva integralmente `NFeEventUI`, `TaxUI.mixins=[NFeEventUI]` e `mixins:[TaxUI]` na aplicação. Acrescenta `AccountingReportPanel` e o render composto com o render fiscal existente, sem substituir templates ou renders fiscais.

Foi comparado byte a byte o código de `NFeEventUI`/ligação a `TaxUI`, o controlador fiscal anterior ao bloco e as opções/ações principais posteriores ao render. Permanecem idênticos à base. A sintaxe e o comportamento são verificados separadamente; comparação textual não substitui teste de interface.

`qa/accounting_events.py` exercita eventos e relatórios na mesma instância Vue, nos modos local/portal: consulta sem movimentos, decisão explícita do evento pela interface, consulta ainda sem movimentos, escrituração explícita, relatório atualizado e prova histórica. Navegação entre os dois painéis, tela estreita e troca de empresa conferem a preservação dos componentes e a limpeza de contexto. Os cenários fiscais originais são preservados.

## Esquema e contratos de dados

Sete expectativas em seis arquivos contábeis históricos foram reconciliadas de 17 para 18. As fixtures que representam versões anteriores retiram as três tabelas exclusivas de eventos antes da migração, além das estruturas de versões posteriores já retiradas. As verificações continuam comparando dados, hashes, movimentos, memórias e bloqueios, não apenas o número do esquema.

Não há migração contábil concorrente 18/19. Persistência, fechamento por módulo, leitor/serviço de eventos, recepção, guardas de escrituração, preparação XML, tributação/lotes, ajustes/saldos e templates/renders permanecem idênticos à base fiscal.

Eventos e decisões operacionais não alteram automaticamente campos da nota, partidas, títulos ou valores tributários. Um evento pendente bloqueia nova escrituração; uma decisão de manter fluxo não é autorização SEFAZ nem substitui a conferência/escrituração explícita. Esta grava a prova separada na mesma transação dos movimentos.

Históricos escriturados e relatórios permanecem consultáveis após eventos ou decisões posteriores, inclusive suspensão depois do fechamento. A prova preserva o contexto considerado na escrituração. Fechamento contábil permanece independente do fiscal; recepção/anotação não reabrem nem regravam livros. Provas, originais, memórias e relatórios mantêm escopo por empresa.

## Testes acrescentados

`tests/test_accounting_events_schema18.py` acrescenta quatro cenários conjuntos:

1. Evento pendente impede escrituração; revisão mantém relatórios sem movimentos; escrituração explícita cria duas partidas de 100,30 e a prova da decisão; suspensão posterior com ambos os módulos fechados conserva livros/hashes, prova e títulos. Outra empresa não acessa a prova.
2. CC-e posterior não modifica campos ou livros escriturados. Evento bloqueia encerramento fiscal e permite encerramento contábil independente. Revisão não inventa prova retroativa.
3. Falha após registrar a prova desfaz prova e movimentos na mesma transação e mantém relatório/títulos; nova tentativa explícita cria somente uma prova e duas partidas.
4. Migração sintética 17→18 conserva preparação XML, memória tributária v4, originais/revisões, movimentos, apuração, livros/hashes e ambos os bloqueios. O índice de eventos inicia vazio, sem reinterpretar os originais antigos, e as chaves estrangeiras permanecem íntegras.

Execução direcionada `test_accounting*.py`: **56 testes aprovados**. A suíte completa da composição passou com **447 testes da aplicação**, 18 de distribuição (17 aprovados e DPAPI omitido no Linux) e 30 de ferramentas; templates, compilação/sintaxe, matemática monetária, ícones e smoke autenticado aprovados. O navegador conjunto passou nos modos local e portal. As capturas sintéticas de relatórios desktop e eventos mobile foram inspecionadas.

Durante a elaboração do novo cenário de navegador, foram corrigidas duas suposições do teste: o painel de eventos já aberto não deve ser fechado ao retornar à Recepção, e a navegação do portal em tela estreita exige abrir o menu móvel. As correções usam os controles existentes e não alteram a aplicação. Regressões, Docker e CI são registrados pelo HEAD final efetivamente executado na descrição do PR, na conversa e no artefato local ignorado `artifacts/validacao-esquema18.md`. Não atribuir à composição os resultados/builds do PR fiscal.

## Publicação e limites

A revisão autorizada é em rascunho contra a branch do PR #20, contendo somente o incremento contábil. Sem merge, release, implantação ou alteração das branches anteriores. A arquitetura continua integrada, Windows gráfico/tray e servidor Docker; não há EXE por relatório.

Windows x86/x64 requer build nativo deste HEAD. Os workflows por PR filtram main/develop e não esta base empilhada. O dispatch pelo CLI foi anteriormente bloqueado com Forbidden em api.github.com antes do envio, e o conector não oferece a ação. Não repetir sem alteração de disponibilidade nem contornar o bloqueio. Os builds fiscais anteriores e CI Linux não comprovam Windows desta composição. Docker local comprova somente a imagem testada, sem publicação em registro.

Somente dados sintéticos, sem homologação fiscal/Prosoft/PVA. Cobertura de eventos e XML limitada ao perfil descrito na documentação fiscal da base; sem validação presumida de autorização, cancelamento ou texto de CC-e, sem estorno automático ou regras/alíquotas legais inventadas. CBS/IBS continuam excluídos. Centros de custo, conciliação e demais requisitos ainda abertos permanecem pendentes.

Anexos legados continuam sem bytes/pixels acessíveis por falha anterior de transferência. Não houve nova tentativa sem mudança de disponibilidade, execução de EXE desconhecido ou recuperação de código-fonte alegada. O levantamento permanece aberto.
