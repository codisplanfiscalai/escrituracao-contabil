# Preparação de documentos e valores por item — 06/11/2026

## Entrega e dependências

Este incremento parte do PR #16 (`9b0a4fb97dd916de854b28515ca99ddb89cb0a00`) e continua a cadeia fiscal #16 → #14 → #13 → #11 → #10 → #8, destinada à develop. Acrescenta preparação conferida de rascunhos a partir de documentos organizados e observação rastreável de valores por item de NF-e/NFC-e. Não efetiva operações, não cria títulos e não substitui a conferência fiscal/contábil.

A aplicação continua integrada, com frontend comum, Windows gráfico/tray e servidor Docker. Não há novo executável por tela. Os documentos originais, suas observações e seus perfis anteriores permanecem preservados.

## Fonte de leiaute efetivamente consultada

Foi lida a [árvore XML publicada pela SEF/MG](https://portalsped.fazenda.mg.gov.br/spedmg/nfe/download/EstruturaNFe.html), identificada como `PL_010b_NT2025_002_v1.30`. A referência e a data da verificação estão no perfil de extração. Isso comprova os caminhos explicitamente cobertos, sem certificar aderência a todas as NTs vigentes em 2026. O PDF do MOC nacional não pôde ser lido nesta consulta: o portal nacional apresentou redirecionamento circular e a alternativa do CONFAZ excedeu o tempo de resposta. Não se atribui a esses PDFs validação não realizada.

O novo perfil `nfe-nfce-4.00-item-values-v1` aceita XML NF-e/NFC-e 4.00, modelos 55/65, com NFe isolada ou nfeProc. Reutiliza as proteções do leitor de cabeçalho e acrescenta limites próprios: 10 MiB, 200 detalhes, nItem único, seleção tributária sem ambiguidade e limites para campos/decimais. Esses limites são do aplicativo, não uma declaração de todos os limites do XSD oficial. Não há validação XSD completa, assinatura ou autorização.

| Caminho relativo a det | Cobertura observada |
| --- | --- |
| prod | cProd, xProd, NCM, CFOP, uCom, qCom, vUnCom, vProd, vFrete, vSeg, vDesc, vOutro, indTot |
| imposto/ICMS/ICMS00 | orig, CST, vBC, pICMS, vICMS, pFCP, vFCP |
| imposto/ICMS/ICMS10 | orig, CST, vBC, pICMS, vICMS, vBCST, pICMSST, vICMSST, vBCFCP, pFCP, vFCP, vBCFCPST, pFCPST, vFCPST |
| imposto/PIS/PISAliq | CST, vBC, pPIS, vPIS |
| imposto/COFINS/COFINSAliq | CST, vBC, pCOFINS, vCOFINS |

Outros grupos são identificados como não extraídos. Valores de CBS/IBS não são extraídos nem calculados. Não são acrescentados suporte a outros grupos de ICMS/PIS/COFINS, CT-e, NFS-e, eventos ou itens SPED por inferência.

## Origem, ausência e memória

Cada campo guarda caminho completo, texto observado, valor normalizado e eventual crítica. O texto observado é o texto decodificado pelo parser XML; a representação lexical de bytes/entidades continua no arquivo original, vinculado por SHA-256. Campos ausentes permanecem ausentes. Decimal fora do perfil é exibido com crítica e não pode ser copiado como base/total.

O localizador usa a posição real `infNFe/det[ordinal]/prod`; nItem é conservado separadamente. Por exemplo, nItem 10 no primeiro detalhe continua associado a det[1], sem confundir numeração e posição. Bases homônimas são lidas nos caminhos exatos: base própria, ST e FCP não se misturam. A soma observada de vProd é informativa; não se presume vNF nem total líquido dos itens.

O snapshot `evidencia-itens-xml-v1` vincula empresa, documento, observação ativa, arquivo original, hash da fonte, perfil e valores. Consulta de evidência exige escopo da empresa, mas não exige competência aberta. Alteração de observação/fonte exige nova conferência para fichas ainda não escrituradas.

## Preparação em lote

Em Escrituração, o operador seleciona de 1 a 50 documentos organizados sem operação existente, declara entrada/saída, política aprovada e data na competência aberta. Havendo múltiplas observações, escolhe a origem. A natureza deve ser confirmada pelas partes do documento e pelo CNPJ da empresa; casos ambíguos exigem tratamento individual. NFC-e de saída sem destinatário é admitida quando o emitente identifica a empresa.

São oferecidos três modos:

1. **Cabeçalho:** reutiliza a proposta existente, sem nova extração de valores.
2. **Observar XML:** anexa evidência dos itens sem transformá-los em itens tributários.
3. **Propor itens XML:** propõe descrição/NCM/localizador, com escolhas explícitas para copiar vProd ao total atribuído e bases cobertas. Base solicitada ausente/inválida bloqueia o lote inteiro. Não há substituição silenciosa por zero.

CFOP observado fica na evidência; não é convertido em CFOP da empresa. Tratamentos, componentes tributários e justificativa de não tributação ficam sem decisão. Frete, descontos, seguro, outros valores, alíquotas e impostos observados não geram fórmulas ou regras legais automaticamente. Divergência entre soma dos vProd copiados e vNF gera aviso; a reconciliação posterior dos itens continua obrigatória.

A prévia é somente leitura, limitada a 8 MiB. Registra política/contas, versões dos módulos, versão da competência, propostas, origens e críticas. Uma pendência impede toda a aplicação. Após confirmação explícita, motivo e referência da conferência, o backend recalcula a prévia e compara seu hash. Alterações intermediárias obrigam nova conferência.

A aplicação salva apenas rascunhos versionados e seu manifesto em uma transação. Falha interna desfaz todas as gravações. Repetir a mesma tentativa/conteúdo retorna o resultado preservado; conteúdo diferente é recusado. Resposta de rede perdida não duplica operações. Os bloqueios fiscal e contábil são respeitados para criar rascunhos; recepção e consulta continuam independentes do fechamento.

O manifesto `preparacao-documentos-v1` preserva propostas e hashes, versões criadas, escolhas, autor, motivo e referência. Pode ser consultado e exportado em JSON operacional. A interface lista as 50 preparações mais recentes por competência; registros anteriores continuam preservados e consultáveis por identificador. Não é exportação de obrigação fiscal.

## Contrato técnico e migração

O esquema **17** acrescenta `document_preparation_batches`, sem reescrever originais ou memórias anteriores. A migração deve ser conferida numa cópia privada autorizada antes de uso operacional. Executáveis anteriores ao esquema 17 não devem abrir o banco atualizado.

- `src/nfe_item_values.py`: leitor independente de valores observados.
- `src/document_preparation.py`: validação, prévia, transação, idempotência e histórico.
- `src/persistence.py`: esquema e composição do serviço.
- `src/tax_api.py`: consultas com workspace.read e empresa; prévia/aplicação com workspace.write e CSRF.
- `src/tax_engine.py` / `src/tax_items.py`: vínculo opcional da evidência à memória tributária.
- Frontend compartilhado: seleção, cópias explícitas, inspeção, confirmação e histórico; ponto de composição com a frente contábil.

Com evidência XML, a memória documental usa `tributacao-parametrizada-v2` e a memória por item usa `tributacao-itens-v4`. Sem evidência, os perfis anteriores permanecem iguais. Alteração ou remoção da evidência de uma ficha calculada exige novo cálculo. Históricos escriturados conservam seus snapshots, sem recálculo por alteração posterior da fonte.

## Validação e limites restantes

Testes sintéticos cobrem separação dos caminhos, ausência e decimal inválido, NFC-e, grupos não cobertos, limites, prévia sem escrita, escolhas explícitas, reconciliação, integridade de originais, migração real 16→17, rollback, concorrência, idempotência, alterações após prévia, períodos encerrados, escopo e CSRF. A interface é exercitada no modo local e no portal, incluindo resposta perdida, repetição, exportação, navegação e tela estreita. Resultados efetivos, SHA, composição contábil, builds e CI são registrados no PR e na conversa; resultados de versões anteriores não são atribuídos ao novo SHA.

Continuam pendentes: amostras autorizadas representativas; homologação da alocação líquida e das regras por empresa/jurisdição; outros grupos fiscais e documentos; cargas oficiais completas de cadastros; captura externa; layouts oficiais de obrigações; importadores bancários e conferência de PDF/imagem; integração/revisão/release da versão combinada. Testes de software não certificam tratamento legal ou direito a crédito.

Os binários/prints legados continuam sem leitura: a materialização anterior falhou com `library file transfer failed: download failed`. Não houve inspeção de seus bytes/pixels, recuperação de código-fonte ou execução desses executáveis. Este incremento usa código existente, requisitos autorizados e os caminhos XML efetivamente consultados.
