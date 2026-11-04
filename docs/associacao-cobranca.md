# Associação explícita de cobrança — contrato antes do código

Fluxo: conferir observações de cobrança e fatura/parcelas canônicas → selecionar arquivo XML, fatura existente e correspondências de parcelas → gerar prévia validada → conferir origem, valores, vencimentos e destinos → confirmar com motivo e fingerprint → registrar nova decisão → revisar novamente o documento antes de preparar partidas.

## Recorte permitido

Uma decisão associa todo o conjunto de cobrança de um arquivo XML a uma fatura já existente do mesmo documento, empresa e contexto de período. Deve existir exatamente uma observação de fatura com nFat presente e parcelas com nDup presentes e únicos. Todas as parcelas da fatura canônica devem ser cobertas uma única vez, e toda parcela da fonte deve ter um destino. Nenhuma fatura, parcela, valor, vencimento ou identidade é criada. Observações que já têm vínculo canônico não podem ser remapeadas para outro título/parcela.

Valores da fatura (original, desconto e líquido) e de cada parcela devem coincidir exatamente com o alvo. Datas de vencimento também devem coincidir; somente nFat/nDup podem ser diferentes. Fatura/parcelas canônicas precisam de evidência XML ativa no mesmo contexto, com valores correspondentes e sem alertas não resolvíveis. Somatórios e aritmética da fatura/fonte/alvo são conferidos com Decimal. Campos ausentes, identificadores repetidos, duplicidades internas, valores ou datas divergentes e demais alertas continuam bloqueados. Sem correspondência completa um a um, a operação falha inteira. Não há sugestão automática de associação nem criação de parcelas.

Somente três alertas específicos de identidade podem ser cobertos por uma decisão aplicável: nFat divergente, nDup divergente e parcela sem título inequívoco quando o título e os IDs foram agora demonstrados. A validação completa impede usar esse último alerta para resolver ausência de ID ou duplicidade interna. Alertas aritméticos e de valor não são suprimidos por associação. Originais, issues, IDs normalizados e estados canônicos continuam intactos.

## Versionamento e validade

Cada confirmação cria uma nova versão por documento/arquivo, com ator local, motivo e snapshot da proposta, fontes e alvos. A decisão guarda fingerprint de todas as fontes do documento e dos alvos. Nova fonte, exclusão lógica ou mudança dos alvos torna a decisão caduca; exige nova prévia e confirmação. Decisão nova para outro arquivo não invalida uma associação anterior cujo conjunto bruto de fontes permanece igual, mas altera o snapshot documental e exige nova revisão.

A prévia incorpora a proposta exata, as fontes, os alvos e as versões atuais de decisões do documento. Confirmação exige `confirmed=true`, motivo e fingerprint correspondente. Duas confirmações concorrentes da mesma prévia não podem criar versões duplicadas: a segunda encontra prévia desatualizada. Mutação e auditoria são atômicas.

Snapshots documentais passam a conter as decisões de cobrança existentes e sua aplicabilidade. Sem decisões, a estrutura anterior é preservada para não caducar revisões por simples migração. Criar ou substituir associação altera o fingerprint documental; revisões/prévias já preparadas exigem nova versão. Fechados e evidências exportadas nunca são reescritos. Uma associação posterior ao fechamento descreve a conferência atual e não altera o histórico. Não há estorno, pagamento, recebimento, exportador Prosoft ou inferência fiscal neste incremento.

## Contratos para o integrador

- `preview_billing_association(company_id, document_id, period_id, file_id, invoice_id, installment_links)`: valida e devolve a proposta enriquecida, fontes/alvos e `expected_fingerprint`. `installment_links` é uma lista de `{observation_id, installment_id}`, cobrindo todas as parcelas da fonte e do alvo. A observação de fatura é identificada pelo arquivo/documento, sem escolha arbitrária entre múltiplas faturas.
- `save_billing_association(company_id, document_id, period_id, file_id, invoice_id, installment_links, expected_fingerprint, reason, confirmed=False)`: refaz a prévia dentro de transação e grava nova versão somente quando todos os dados coincidem. Retorna a decisão com `current`, `valid` e `blockers`.
- `list_billing_associations(company_id, document_id=None)`: histórico isolado por empresa, com snapshot, versão, ator/motivo e validade atual.

Rotas propostas: POST `billing-association-preview`; GET/POST `billing-associations`. A API e a interface são responsabilidade do integrador.

Conciliação mantém `sources[].issues` e os IDs originais, acrescentando `billing_resolution` somente quando há decisão aplicável, com `association_id`, `version`, `invoice_id`, `installment_id` e `resolved_issues`. Questões agregadas mantêm `messages` originais e expõem `resolved_messages` separadamente. A lista `billing_associations` mostra histórico/validade. Diferenças de identificadores e fontes continuam consultáveis; a decisão explicita a relação sem apagá-las. `ready_for_export` continua false.

## Migração e aceite

Migração aditiva 1/2/3/4→5 com tabela própria de decisões; sem alterações de bytes, payloads, IDs ou snapshots anteriores. Testes fictícios: associação nFat/nDup, atomicidade e concorrência, escopo/empresa/período, origem excluída, ausência/duplicidade de ID, valores/datas/aritmética divergentes, cobertura completa 1:1, fingerprint desatualizado, nova versão, preservação das issues, caducidade de revisão/prévia, histórico fechado/exportado e migração com rollback. Todos os testes e campos livres usam dados fictícios.

## Resultado do incremento

Implementado em `src/billing_association.py`, com integração aos snapshots do motor e à consulta de conciliação. A anotação de resolução só aparece na conciliação; a consulta direta de observações permanece crua. As fontes associadas aparecem também na fatura/parcela de destino com anotação explícita, preservando IDs originais nulos e diferenças nFat/nDup. O estado geral pode continuar divergente mesmo depois de resolver a identidade: diferença de conteúdo não é apagada e a disponibilidade contábil depende de nova revisão documental.

Verificação local em 2026-11-04: 17 testes novos de associação e 142 testes totais aprovados; `compileall` e `git diff --check` aprovados. Cobertos também empate de valor/vencimento com confirmação da correspondência exata, proibição de remapear vínculo nativo existente, reabertura de snapshot associado e igualdade byte a byte da evidência exportada. API, interface e validação Chromium pertencem à integração posterior; não são alegadas como resultado destes testes.

Limites: apenas associação completa de uma fatura XML a uma fatura canônica existente; sem criação, agrupamento/desmembramento de títulos, vínculo parcial, alteração monetária ou revogação independente de associação. Corrigir uma associação usa nova versão explícita; não há aplicação retroativa em fechado. A política prévia de revisão de divergências documentais permanece separada: esta decisão só resolve os alertas de identidade listados, nunca substitui a revisão contábil nem resolve valores divergentes por associação.
