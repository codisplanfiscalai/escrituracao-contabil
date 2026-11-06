# PR preparado localmente — não publicado

Estado atual: composição com eventos do PR fiscal #20, base `dcdc7c8850623469e2a09f516b7b6434b8acb3ce`, esquema 18, em `frente-contabil-integracao-esquema18.md`. O PR contábil #19 e as etapas abaixo são históricos e permanecem preservados.

Estado atual: integração com o PR fiscal #18, base `2a68f7452e739438cc2922dc2a3b5702a96291ea`, esquema 17, em `frente-contabil-integracao-esquema17.md`. O PR contábil #17 do esquema 16 e os demais registros abaixo são históricos e permanecem preservados.

Estado posterior: o incremento contábil do esquema 15 foi publicado no PR #15, e a etapa atual prepara revisão empilhada contra o PR #16, `feat/tributacao-lote-conferida`, se a combinação for aprovada. Consulte `frente-contabil-integracao-esquema16.md`. Os PRs anteriores devem permanecer preservados.

Publicações históricas: PRs contábeis #9 e #12 em rascunho. A etapa posterior usa a branch isolada `feat/contabil-compat-esquema15`, base `3673c5a1212c29aff0c600e11bfd329f5d96022a` do PR #14, com autorização para publicar revisão empilhada em rascunho se validada. Consulte `frente-contabil-integracao-esquema15.md`. Os PRs anteriores não devem ser reescritos ou mesclados por essa etapa.

O título acima é histórico. O incremento foi publicado no PR #9 em rascunho, com HEAD `c4a7a31404f49ba53a01db64192be10e00804a1a`. Os PRs foram preservados. A combinação posterior com o PR #11 foi preparada separadamente, sem atualizar o PR #9; consulte `frente-contabil-integracao-esquema14.md` antes de publicar ou retargetar qualquer revisão.

Atualização: a combinação foi preparada em `feat/contabil-compat-esquema13`, baseada no HEAD fiscal `64378f695919c3816840b9eb29c669c762fc6ca1` do PR #8. A branch fiscal não foi modificada. O incremento contábil pode ser revisto como diferença contra esse HEAD; uma eventual revisão empilhada teria a branch fiscal como base, evitando duplicar seus arquivos em outro PR para `develop`. Este documento não publica PR nem autoriza merge ou release.

Título proposto:

`feat(contabil): adiciona consultas configuráveis de Diário, Razão e Balancete`

Descrição proposta:

O painel de livros passa a permitir consultas de Diário, Razão e Balancete por empresa, competência, versão do plano, datas e conta/grupo, com balancete analítico ou sintético. O serviço reutiliza o livro integrado existente, conserva abertura e continuidade dos saldos, calcula os totais pelas contas analíticas e expõe os hashes do livro e do recorte. A rota GET é compartilhada pelo aplicativo local e pelo portal autenticado; a consulta não grava movimentos ou altera regras fiscais.

O componente de filtros fica em `workbench.js`, com o mixin tributário e todos os dados/ações fiscais preservados. Houve um conflito textual na criação da aplicação Vue, resolvido na árvore de integração. Não há nova migração, alteração de templates/renders ou empacotamento.

Validação conjunta local: `python3 scripts/build.py check` aprovado — 294 testes da aplicação, 18 de distribuição com um DPAPI omitido no Linux e 30 de ferramentas. Os seis novos testes conjuntos cobrem migração 10→13 preservando originais/movimentos/hashes, leituras após fechamento, bloqueio de escritas mistas, `tax_calculation`, `tax_adjustment_of` e regras futuras sem recálculo histórico. QA Chromium de relatórios, tributação/apuração, fechamento independente, navegação e fluxo integrado aprovados; relatórios desktop/móvel inspecionados e `git diff --check` aprovado.

Limites: os 13 executáveis e 13 prints de referência estão inventariados, mas nenhum byte ficou disponível no executor devido à transferência recusada com 403. Nenhum binário foi executado ou analisado, e nenhum print de referência foi inspecionado por pixels. Modelos específicos, centros de custo, conciliação bancária e critérios de associação seguem abertos. O fechamento por módulo e os campos tributários do esquema 13 vêm da base fiscal e não foram reimplementados. Não foram executados CI remota, builds Windows ou smoke de imagem Docker publicada para a combinação. A CI aprovada do PR #8 comprova somente seu HEAD fiscal. Não há validação Prosoft/PVA.

Documentação completa: `docs/frente-contabil-integracao-esquema13.md`, `docs/frente-contabil-levantamento-aberto.md` e `docs/frente-contabil-validacao.md`.
