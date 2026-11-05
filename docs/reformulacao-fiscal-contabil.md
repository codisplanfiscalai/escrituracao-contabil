# Reformulação do domínio fiscal e contábil

Diretriz explícita do usuário em 05/11/2026: substituir os processos fiscais/contábeis anteriores; conservar tecnologias, guias e recursos gerais úteis e preservar os dados. Esta diretriz supera as decisões anteriores que exigiam preservar o fluxo de domínio. Branch local parte de develop e85c425. Não há autorização de publicação.

## Problema e novo percurso

O produto anterior exigia revisão documental, ficha fiscal, lote contábil e título avulso como atividades separadas. O operador precisava repetir contexto e dados; as cobranças recebidas não conduziam ao financeiro e o histórico técnico dominava a operação.

A unidade operacional passa a ser a **competência de trabalho** de uma empresa, com competência de parâmetros independente, plano e políticas contábeis explícitas. Dentro dela, uma **operação** reúne documento canônico/fontes, ficha fiscal, partidas e cobrança; cada componente mantém sua identidade e proveniência. Receber XML e SPED não efetiva lançamentos. Conferir e escriturar a operação efetiva, em uma transação, os movimentos e os títulos escolhidos; baixar um título não cria outra compra ou venda.

Percurso: selecionar empresa → receber e identificar fontes sem exigir competência/plano → configurar competência e organizar fontes → abrir operações pendentes → completar/classificar com política contábil aprovada → conferir fiscal/contábil/financeiro em conjunto → escriturar → consultar livros e liquidar títulos → conferir a competência e exportar o pacote de trabalho. Toda pendência indica campo, causa e ação seguinte. Não há exportação oficial habilitada sem perfil demonstrável.

| Estado da operação | Significado | Próxima ação |
| --- | --- | --- |
| Sem ficha | Documento recebido e organizado, sem decisão operacional | Abrir ficha da operação |
| Rascunho | Conteúdo durável, inclusive incompleto, sem efeito nos livros | Completar campos apontados |
| Revisado | Versão completa conferida, com hashes de fonte e parâmetros | Escriturar a versão conferida |
| Escriturado | Snapshot imutável, movimentos e títulos vinculados materializados | Livros, financeiro ou ajuste vinculado |
| Dispensado | Decisão explícita e motivada de não escriturar | Histórico da decisão |
| Legado | Registro anterior preservado, sem reexecutar efeitos | Consultar ou retomar rascunho no novo modelo |

## Modelo e regras

- Empresas, arquivos originais, documentos/fontes canônicos, contas e identidade permanecem como infraestrutura de dados. O novo processo não depende de revisões/lotes antigos para funcionar.
- Competência operacional única por empresa/mês; referência de parâmetros separada. Períodos anteriores equivalentes são vinculados à mesma competência, impedindo duplicação por troca de mês-base.
- Políticas por empresa/plano/operação/referência, com versões e aprovação. Contas analíticas explícitas; nenhum enquadramento fiscal ou conta é inferido pelo nome. Propostas reutilizam políticas aprovadas e valores de fonte, sempre sujeitas à conferência.
- Revisões de operação preservam fonte escolhida, divergências reconhecidas, ficha fiscal, partidas, cobrança, política, plano e competências. Alteração de fonte/plano/política torna a revisão pendente; efetivação verifica novamente o estado.
- Cada evento/data/grupo equilibra débitos e créditos usando Decimal. O valor documental da operação e os títulos informados são confrontados com a fonte; dados ausentes não são fabricados.
- Fatura, parcela e título financeiro não são documentos fiscais. Parcelas com identificação confiável podem ser propostas da fonte; só passam ao financeiro ao escriturar ou vincular título existente expressamente. Idempotência protege todas as materializações.
- Livros combinam movimentos anteriores fechados e novos sem reprocessar os anteriores. Exportações preservam bytes, fontes e hashes. Financeiro preserva baixas, estornos e cancelamentos; decisões são auditadas.
- Ajustes de lançamentos escriturados são novas operações vinculadas. Não alteram snapshots fechados ou significam retificação fiscal/transmissão automática.
- Guias da operação e rascunhos são duráveis por usuário/empresa/competência. Autorização é validada na API; menu não substitui permissão.

## Migração e retirada do fluxo anterior

Migração aditiva, transacional: cria o novo modelo e referências de legado, sem reescrever originais, partidas fechadas, livros exportados ou baixas. Rascunhos anteriores de lançamentos e de guias fiscais pertencentes ao operador podem ser retomados de forma explícita; registros fechados são somente consultados e entram nos livros históricos. O frontend operacional anterior é substituído. Endpoints antigos de escrituração deixam de aceitar novas gravações, mantendo consultas históricas necessárias. Testes de comportamento antigo não constituem requisito para manter o processo rejeitado.

## Material e dependências

O documento de requisitos da Library foi lido integralmente. O ZIP geradorsped-main.zip foi localizado na pasta Contabil; o helper autorizado de materialização falhou com `hosted apps tools/list request failed: network`. Não houve leitura de bytes nem contorno de acesso. O estudo do código do gerador e a decisão de reaproveitamento verificável permanecem bloqueados até recuperar esse acesso. O inventário anterior serve apenas como pista de requisitos: parser/serializer, estrutura de registros, fechamento de blocos, editor e cobrança; não comprova portabilidade nem homologação.

Os leiautes reais Prosoft e exemplos não são presumidos. Nenhuma saída própria JSON/CSV será rotulada como SPED/PVA ou importação Prosoft homologada. CBS/IBS continuam fora do cálculo. Formatos e perfis não demonstrados ficam indisponíveis com motivo explícito.

## Aceite executável

Verificar com fontes sintéticas: competência-base distinta; XML/SPED do mesmo documento sem dupla operação; conflitos e fontes modificadas; ficha única fiscal/contábil/cobrança; política explícita e conta analítica; conferência e efetivação atômicas; tentativa repetida/concorrente; títulos vinculados e baixa parcial; livros/exportações estáveis; guias recuperadas após reload/login; isolamento e permissões; migração preservando bytes/hashes/baixas; impossibilidade de operar pelo processo retirado. Registrar diferenças de tela e testes reais, sem homologação presumida.


## Comportamento implementado

- `source_evidence.py`: caixa de entrada e revisões imutáveis `source-evidence/2`, decisão de competência separada, originais e análise técnica reaproveitados, retirada lógica com prévia e proteção de efeitos fechados.
- `work_domain.py` / `work_store.py`: competência, políticas, ficha única, versões, conferência, efetivação atômica, parcelas/títulos, liquidação e estorno no mesmo livro, abertura e encerramento.
- `work_books.py`: snapshots, saldos, continuidade, fiscal e financeiro por competência, pacote operacional preservado e verificável. Estados financeiros antigos sem competência econômica são sinalizados.
- `frontend/templates/workbench.html` / `src/web/workbench.js`: nova interface operacional; substitui o frontend anterior. Recursos do portal abrem em guias, iframe mantém a instância, contexto de cliente é independente e rascunhos contábeis ficam no banco com controle de versão. Guias encerradas podem ser reabertas pelo Histórico.
- `work_api.py`: APIs novas, permissões de escrita/conferência e HTTP 410 nos escritores antigos. Os métodos antigos permanecem internos para leitura/migração e seus testes históricos.

O fechamento é mensal e local. Não representa apuração, encerramento anual das contas de resultado, retificação de obrigação transmitida ou homologação de leiaute. Plano completo em PDF continua dependente de perfil de extração comprovado; a importação implementada usa CSV explícito. Mudança de plano conserva contas e saldos por versão, sem converter contas automaticamente.
