# PR preparado localmente — não publicado

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
