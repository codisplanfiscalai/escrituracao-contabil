# Conciliação documental e cobrança — plano do incremento

Fluxo definido antes da implementação: selecionar empresa/período → receber original → escolher perfil → extrair observações localizadas → vincular documento canônico por chave confiável → comparar campos comuns → exibir coincidências/divergências e cobrança → manter revisão pendente. Não gerar lançamentos ou saída Prosoft.

## Formatos e limites explícitos

- XML: NF-e 4.00 modelo 55, recorte já implementado. Fatura identificada por documento + nFat; parcela por fatura + nDup. Ausência ou repetição de identificador produz observação pendente, sem fabricar identidade. Todas as ocorrências preservam arquivo e localização. Valores conflitantes não sobrescrevem a primeira representação canônica.
- SPED: recepção simples continua disponível e é o padrão. Perfil opcional `efd-icms-ipi-020-c100-v1`: leitura parcial de 0000 e C100 regular (COD_SIT 00), modelo 55, para 2026. Somente CNPJ e período de cabeçalho coerentes com o contexto permitem vinculação. Chave ausente/inconsistente, data divergente, versão desconhecida ou outro modelo/situação geram pendência por linha/campo. Não inventar chave alternativa.
- C140/C141 são preservados como observações de registro. Nenhuma fatura/parcela é inferida para modelo 55 a partir deles: falta o contrato específico Prosoft. O perfil de leitura não é um perfil de saída Prosoft.
- O comparador verifica apenas campos disponíveis em ambas as fontes. Divergência de valores é mostrada, sem ajuste tributário, prioridade automática ou descarte de fonte. Coincidência no recorte não é validação fiscal, liberação contábil ou equivalência integral XML/SPED.

## Modelo e persistência

Documento fiscal continua na tabela canônica existente. Novas tabelas de faturas e parcelas referenciam esse documento; observações preservam perfil/versão, arquivo, linha/caminho, conteúdo bruto, campos normalizados, vínculo e pendências. A chave documental usa empresa + chave NF-e no recorte modelo 55. Não há novo documento para cada fonte ou título. Importação e análise repetidas registram tentativa, sem replicar entidades.

Esquema 2 é uma migração aditiva e transacional a partir do esquema 1: cria somente tabelas novas e atualiza a versão técnica. Não altera payloads, bytes, estados ou auditoria preexistentes. Versão desconhecida é recusada. Não há indexação retroativa silenciosa; ação explícita analisa originais já armazenados e mantém os resultados anteriores. Nenhuma entidade canônica recebe atualização silenciosa de valor por conflito.

Remoção lógica inclui faturas/parcelas no escopo apresentado e deixa a cadeia dependente pendente, preservando observações e originais. Conciliação ignora fontes excluídas na comparação ativa, mas continua exibindo seu histórico.

## Tela e aceite

Documentos oferece perfil de importação e análise de arquivo já recebido; Conciliação mostra documento, fontes e localizações, diferenças de campo, faturas e parcelas com suas origens. Erros sem identidade ficam na lista de observações pendentes, sem desaparecer da consulta.

Testes fictícios: XML antes/depois do SPED; repetição de arquivo e registro; chave ausente ou inválida; cabeçalho/período incompatível; conflitos de valor/data; versão desconhecida; XML com fatura/parcelas incompletas ou repetidas; isolamento; preservação entre sessões; migração sem mudança de originais; atomicidade; fontes excluídas; HTTP e fluxo visual. Sem teste Prosoft/PVA ou dados reais.

## Fontes consultadas em 2026-11-04

[Guia Prático EFD-ICMS/IPI 3.2.4](https://www.gov.br/sped/pt-br/assuntos/escrituracoes-digitais/efd-icms-ipi/manuais-e-documentos-tecnicos/guia-pratico-efd-versao-3-2-4.pdf), tabelas de 0000 e C100 e seção C140/C141. [Portal oficial — Manuais e Guias](https://sped.rfb.gov.br/pasta/show/1573) identifica a versão 020 para 2026. Esses documentos fundamentam o recorte de leitura; não comprovam compatibilidade do importador Prosoft nem validação de arquivo integral. Exemplos reais do cliente e especificação Prosoft continuam ausentes.
