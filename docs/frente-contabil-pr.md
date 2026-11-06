# PR preparado localmente — não publicado

Destino: `develop`. Origem: `feat/modulo-contabil-integrado`. Conferir novamente o estado remoto e os arquivos da frente fiscal antes de publicar ou reunir branches. A publicação exige autorização específica, ainda não recebida nesta tarefa.

Título proposto:

`feat(contabil): adiciona consultas configuráveis de Diário, Razão e Balancete`

Descrição proposta:

O painel de livros passa a permitir consultas de Diário, Razão e Balancete por empresa, competência, versão do plano, datas e conta/grupo, com balancete analítico ou sintético. O serviço reutiliza o livro integrado existente, conserva abertura e continuidade dos saldos, calcula os totais pelas contas analíticas e expõe os hashes do livro e do recorte. A rota GET é compartilhada pelo aplicativo local e pelo portal autenticado; a consulta não grava movimentos ou altera regras fiscais.

O componente de filtros fica em `workbench.js`, sem modificar templates/renders, roteadores ou persistência em trabalho pela frente fiscal. Não há migração de banco ou alteração de empacotamento.

Validação local: `python3 scripts/build.py check` aprovado — 257 testes da aplicação, 18 de empacotamento com um DPAPI omitido no Linux e 27 de entrega. QA Chromium do relatório e fluxo integrado aprovados no modo local e portal; inspeção visual desktop/móvel e `git diff --check` aprovados.

Limites: os 13 executáveis e 13 prints de referência estão inventariados, mas nenhum byte ficou disponível no executor devido à transferência recusada com 403. Nenhum binário foi executado ou analisado, e nenhum print de referência foi inspecionado por pixels. Modelos específicos, centros de custo, conciliação bancária e critérios de associação seguem abertos. O novo bloqueio independente por módulo está documentado para implementação coordenada após a migração fiscal 11; não é entregue por este PR. Não foram executados CI remota, builds Windows ou smoke de imagem Docker publicada. Não há validação Prosoft/PVA.

Documentação completa: `docs/frente-contabil-levantamento-aberto.md` e `docs/frente-contabil-validacao.md`.
