# Revisão documental e motor local — plano antes do código

Fluxo: empresa/período → conciliação e fontes → decisão explícita com motivo e observação escolhida → partidas informadas pelo operador → prévia imutável → revisão explícita → fechamento local. Fechamento local não representa importação, exportação ou homologação Prosoft.

## Contrato e limites

Decisões são novas versões por documento/contexto, registradas com ator local, motivo, observação documental escolhida e snapshot/fingerprint das fontes e observações. Novas fontes, análise posterior ou remoção lógica invalidam a decisão. As diferenças continuam visíveis e os originais não mudam. A seleção representa a fonte documental e suas observações de cobrança; não associa títulos desconhecidos. Cobrança sem identidade inequívoca e demais problemas de origem continuam bloqueados; sua resolução estruturada fica pendente. Alertas de aritmética, identidade e registros fora do recorte em qualquer fonte ativa mantêm o bloqueio, mesmo se outra fonte for escolhida. Contextos diferentes também bloqueiam a contabilização.

O motor recebe somente partidas explícitas: documento, observação escolhida, grupo, data, débito/crédito, valor decimal textual, ID exato de mapeamento e histórico. Não há classificação automática por CFOP/CST, conta, destino ou tributo. Cada mapeamento deve pertencer ao plano da empresa, ter destino analítico, estar aprovado e ser a última versão aplicável à competência de movimentos. Mapeamentos ambíguos não são escolhidos automaticamente. Os valores, contas, mapeamentos, fontes e decisões ficam no snapshot, com hash e versões. A referência de parâmetros não desloca movimentos.

Valores positivos com até duas casas decimais; floats são recusados. Datas devem pertencer ao mês processado. Débitos e créditos devem equilibrar cada grupo/documento e o lote. O total de débitos (e créditos) de cada documento deve corresponder exatamente ao total da observação documental escolhida, inclusive quando dividido em grupos. O recorte reserva um único evento contábil por documento/empresa, independente de conta, versão, grupo e competência: grupos e rateios pertencem ao mesmo evento. Eventos adicionais (pagamentos, recebimentos, estornos, ajustes e movimentos por título) precisam de contrato próprio futuro e não podem usar outro rótulo para repetir o documento.

A reserva é feita em transação desde a prévia para impedir lotes concorrentes. Repetir request_key com o mesmo conteúdo devolve o lote e audita a tentativa; conteúdo diferente é recusado. Correção cria nova versão ligada: prévia/revisado anteriores tornam-se substituídos e transferem a reserva atomicamente. O conjunto de documentos deve permanecer igual nessa correção. Um fechado nunca é sobrescrito: sua correção pode ser preparada e revisada, mas permanece impedida de fechar enquanto estorno/ajuste não estiver implementado. Snapshots não mudam; apenas estado e metadados de revisão/fechamento evoluem com auditoria. Revisar e fechar conferem novamente fontes, decisão vigente e mapeamentos. Fechado conserva a evidência histórica mesmo quando novas fontes aparecem.

Remoção lógica de fonte ligada a lote fechado é bloqueada e sua prévia lista os lotes afetados. Outras remoções invalidam decisões/prévias. Não há cancelamento de reservas ou purga neste incremento; corrigir uma prévia usa a versão vinculada.

## APIs e interface

GET/POST `document-reviews`: consultar histórico/registrar decisão (`document_id`, `period_id`, `chosen_observation_id`, `expected_fingerprint`, `reason`). A conciliação acrescenta `source_fingerprint`, `review`, `readiness_for_accounting` e bloqueios, mantendo `ready_for_export=false`.

GET/POST `accounting-batches`: histórico/criar prévia (`period_id`, `plan_id`, `request_key`, `entries`, `reason`, `previous_batch_id` opcional). POST `accounting-review` e `accounting-close` usam `batch_id`, `snapshot_hash`, `reason`. Cada partida usa `document_id`, `observation_id`, `group`, `date`, `side` (`D`/`C`), `amount` (texto), `mapping_id`, `memo`. A interface mínima permite revisar fontes, informar partidas JSON, examinar snapshots e executar transições explícitas.

## Migração e verificação

Migração aditiva transacional 1/2→3; preservar bytes, documentos, observações e histórico. Testes sintéticos abrangem caducidade, isolamento, origens ausentes/ambíguas, conta/plano/vigência, valores Decimal, equilíbrio, reserva entre lotes e conexões, snapshots históricos, remoção bloqueada e rollback. Sem dados reais, acesso Prosoft, apuração CBS/IBS, exportador, estorno, segregação de funções ou homologação. Ator identifica a sessão local; não prova identidade autenticada de revisor.

## Resultado deste incremento

Implementados o mixin `src/accounting_store.py`, a migração 3, as rotas descritas e os formulários locais. `source_fingerprint` cobre também fontes excluídas e metadados de origem, para tornar mudanças de estado detectáveis. O conjunto de observações e originais continua consultável; revisão válida não remove diferenças da conciliação. Cada linha no snapshot guarda observação, decisão, conta e mapeamento completos; os totais e grupos usam Decimal com precisão suficiente para o limite aceito.

Verificação local em 2026-11-04: 108 testes sintéticos aprovados (89 regressões existentes, 17 de revisão/motor e 2 HTTP); `compileall`, `node --check` e `git diff --check` aprovados. A regressão de migração 1 mantém a preservação de bytes/payloads e passa a esperar esquema 3. Migração 2 e falha transacional de migração também verificadas. Inspeção Chromium e publicação são etapas da revisão do integrador, não resultados atribuídos a estes testes.

O recorte não resolve associação de cobrança de identidade ambígua, não cancela reservas, não importa movimentos reais e não gera arquivo fiscal/contábil. Correções de lotes fechados só podem ser preparadas/revisadas para inspeção; não podem fechar. Fontes novas de documento já fechado também tornam a conferência atual pendente e não reescrevem o snapshot histórico. Remoção de qualquer fonte vinculada a esse documento fica bloqueada por seus lotes fechados, mesmo se a fonte tiver chegado depois do fechamento. Reprocessamento de uma prévia mantém o mesmo conjunto de documentos; dividir, expandir ou cancelar esse conjunto exige fluxo futuro explícito.
