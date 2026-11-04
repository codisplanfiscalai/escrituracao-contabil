# Plano de testes

Todos os casos desta fase são sintéticos. Não usar arquivo real da empresa, identificador fiscal real, chave NF-e real, conta bancária ou credencial.

| ID | Caso | Resultado esperado |
|---|---|---|
| T01 | Parâmetros 2026-08 e 2026-09 distintos | Preservar referência agosto; aceitar somente competência processada setembro. |
| T02 | Documento com competência agosto ou outubro | Rejeitar da execução de setembro e listar exceção sem dados sensíveis. |
| T03 | C100 sintético com identidade única | Aceitar um documento no manifesto fiscal. |
| T04 | Mesmo documento sintético repetido duas vezes | Marcar colisão/duplicata; não dobrar documento ou lançamento. |
| T05 | C140 aplicável e único em nota do modelo aceito | Aceitar conforme o contrato do importador. |
| T06 | C141 sem C140 ou parcela repetida | Rejeitar a estrutura contratual. |
| T07 | Mesmo identificador de linha contábil reprocessado | Derivar a mesma chave e bloquear repetição. |
| T08 | Mesmo documento com linhas contábeis distintas e identificadores determinísticos distintos | Aceitar as linhas diferentes, sem confundi-las com duplicata. |
| T09 | Arquivo de lote conhecido com hash idêntico e status confirmado | Bloquear reimportação. |
| T10 | Mesmo run_id ou hash apresentado com conteúdo diferente | Bloquear e exigir novo lote/manifesto. |
| T11 | Resultado de importação desconhecido | Marcar reconciliação pendente; não liberar retry. |
| T12 | Rejeição comprovada seguida de arquivo corrigido | Registrar nova tentativa e manter vínculo com a rejeitada. |
| T13 | Débitos diferentes dos créditos ou total divergente | Falhar conciliação; não permitir estado concluído. |
| T14 | Arquivo de teste com campos fictícios | Não expor informação real em logs; manter processamento local. |

## Bloqueios para homologação

- Obter manual/contrato da versão real do importador Prosoft Fiscal e Contábil.
- Confirmar tipos de documentos abrangidos e regra de C140/C141 no importador.
- Confirmar mapa contábil, plano de contas, histórico, centros de custo e comportamento de reimportação.
- Fazer teste controlado em ambiente autorizado do Prosoft com dados exclusivamente sintéticos.
- Atualizar a referência do Guia Prático aplicável ao período antes da implementação fiscal de produção.

