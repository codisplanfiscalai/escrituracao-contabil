# Fluxo operacional proposto

## Parâmetros do cenário

| Campo | Valor inicial | Uso |
|---|---|---|
| Competência de referência | 2026-08 | Identifica a versão/recorte de parâmetros acordada para este cenário. |
| Competência processada | 2026-09 | Seleciona documentos e período dos arquivos e lançamentos de saída. |
| UF | SP | Escopo inicial informado; tabelas/particularidades ainda dependem de confirmação. |
| Destino fiscal | Importador Prosoft | Preparação para importação interna, sem transmissão ao Fisco e sem execução do PVA. |

## Etapas e estados

1. **Preparar execução:** carregar configuração versionada; conferir competência de referência e competência processada. Cada execução recebe um run_id e um hash do manifesto. Não copiar a configuração de referência para o campo de período processado.
2. **Receber entradas fora do Git:** ler somente a pasta controlada definida pela empresa. Calcular hash dos arquivos, registrar contagem e classificar duplicatas técnicas. Não registrar nomes, CNPJ, chaves NF-e ou valores em logs versionados.
3. **Normalizar:** converter campos para um contrato interno comum, preservar documento e origem, e separar documentos cancelados/inválidos para revisão. A chave NF-e é preferida quando existir; sem ela, usar a combinação empresarial confirmada de modelo, série, número, emitente/destinatário e datas. Colisão ou chave insuficiente vai para revisão, nunca para deduplicação silenciosa.
4. **Aplicar parâmetros:** usar regras etiquetadas com 2026-08, mas aceitar somente documentos da competência 2026-09. Registrar a versão/hash dos parâmetros efetivamente usados.
5. **Preparar fiscal:** gerar arquivo SPED de trabalho para o importador Prosoft confirmado. Gerar C100 para os documentos elegíveis. C140/C141 ficam condicionados ao tipo de documento, existência de fatura/parcelas e contrato do importador. Não presumir que sejam exigidos para toda NF-e.
6. **Pré-checagem interna:** conferir codificação, delimitadores, registros permitidos, hierarquia, cardinalidade declarada pelo contrato, documentos duplicados e totais de controle. Essa checagem é do projeto; não substitui PVA nem validação oficial e não libera transmissão.
7. **Revisão antes da importação:** apresentar manifesto, contagens, resumo de totais e exceções. O operador confere no Prosoft e importa manualmente. Registrar versão do módulo/importador e identificador do relatório/comprovante, sem anexar dados reais ao Git.
8. **Preparar contábil:** derivar lançamentos do mesmo conjunto normalizado de documentos e do mapa de contas aprovado. Não criar uma segunda ingestão paralela do mesmo lote. Gerar chave idempotente estável por documento, competência, versão de regra, agrupamento e linha contábil.
9. **Importar e reconciliar contábil:** bloquear lote já concluído; verificar se movimentos equivalentes já existem; importar uma única vez; comparar resultado com o manifesto. Um timeout ou resultado ambíguo muda o estado para RECONCILIACAO_PENDENTE e bloqueia novo envio.
10. **Fechar execução:** só marcar CONCLUIDO após conciliação de contagens/totais e confirmação no Prosoft. Manter evidências minimizadas, hash e logs redigidos fora do repositório.

## Estados permitidos do lote

PREPARADO → REVISADO → IMPORTACAO_INICIADA → CONFIRMADO → CONCILIADO.

- Rejeição comprovada: encerrar a tentativa como REJEITADO; correção gera novo manifesto/lote, preservando a tentativa anterior.
- Resultado desconhecido, interrupção ou timeout: RECONCILIACAO_PENDENTE; consultar o Prosoft e registrar decisão antes de novo lote.
- Estados CONFIRMADO, CONCILIADO e RECONCILIACAO_PENDENTE nunca podem ser reenviados automaticamente.

