# Integração contábil com tributação em lote e esquema 16

## Base e composição

Base fiscal: [PR #16](https://github.com/codisplanfiscalai/escrituracao-contabil/pull/16), branch `feat/tributacao-lote-conferida`, HEAD **`9b0a4fb97dd916de854b28515ca99ddb89cb0a00`**. O incremento contábil do PR #15, `5d78613b858cbd8a4f130bf55292cbc49eb75cf7`, foi reaplicado na árvore isolada `/workspace/escrituracao-contabil-compat16`, branch `feat/contabil-compat-esquema16`.

A aplicação foi limpa, sem conflitos. Os cinco commits contábeis anteriores tornaram-se `730af92`, `aa47e4b`, `b36daaa`, `66f1db5` e `99045e7`; o complemento desta etapa atualiza expectativas, prepara fixtures antigas corretas e acrescenta testes conjuntos de lote/livros. Não reaplicar também os commits originais sobre essa composição.

Não houve alteração da persistência fiscal, nova migração 16/17, mudança no motor/serviço de lotes, guardas, templates ou renders da base. O mixin e as ações fiscais permanecem no controlador Vue junto ao painel contábil. A revisão autorizada é em rascunho contra a branch do PR #16, preservando as revisões anteriores; não há merge, release ou implantação autorizados.

## Expectativas e fixtures

Cinco expectativas de versão nos contratos contábeis históricos foram reconciliadas de 15 para 16. As fixtures que simulam bancos 10, 13 e 14 também passaram a retirar `tax_calculation_batches`, ausente nesses esquemas. Os testes de migração continuam conferindo dados, memórias, hashes, movimentos e fechamentos, não apenas o número da versão.

Os nomes históricos de arquivos/classes de teste foram preservados para rastrear os contratos de origem; docstrings e assertivas indicam a versão corrente. Não foi editado o esquema do produto para fazer os testes passarem.

## Contrato contábil do lote

A seleção revisada e aplicação atômica de tributação criam novas versões de rascunho e memórias individuais. Não conferem, escrituram, geram partidas/títulos ou consolidam contabilidade automaticamente. Cada operação continua passando pelas guardas e pela conferência/escrituração explícita.

Um lote pode preservar memórias documentais v1, itens v2 e FCP/cálculo por dentro v3, sem reduzir seus efeitos a um número único de cabeçalho. O relatório contábil conserva cada operação, plano, data, partida e hash de origem. Tributos calculados não mudam as contas ou contrapartidas informadas.

Falha depois de aplicar o primeiro cálculo deve desfazer versões, memórias, pedidos, manifesto e auditoria da tentativa inteira, conservando movimentos anteriormente escriturados. Uma repetição idempotente após escritura/fechamento recupera o manifesto original sem duplicar movimentos ou refazer o lote.

## Cobertura acrescentada

`tests/test_accounting_batch_schema16.py` acrescenta quatro cenários sintéticos:

1. Aplicação de lote de 100,30 e 200 cria somente rascunhos; o livro entra em 100,30 e depois 300,30 apenas ao escriturar individualmente. Repetição após fechamento conserva manifesto, quatro partidas e duas memórias.
2. Falha no segundo cálculo preserva um livro anteriormente escriturado de 100,30 e todas as contagens de versões, memórias, pedidos, auditoria, partidas e títulos. Nova tentativa aplica rascunhos; só escrituração explícita leva o total a 225,30.
3. Lote com perfis v1/v2/v3 conserva suas memórias. O livro continua vazio até a escrituração individual; depois contém três eventos e seis partidas, totalizando 300,90, sem compensação pelo saldo tributário.
4. Migração sintética 15→16 conserva originais, cálculos individuais, ajustes/apuração, hash do livro e ambos os bloqueios. O histórico de lotes começa vazio e as chaves estrangeiras permanecem íntegras.

A execução direcionada `test_accounting*.py` passou com **48 testes**. Suíte completa, navegadores, imagem Docker e CI devem ser registrados pelo SHA final efetivamente executado; o registro final fica na conversa, descrição do PR e `artifacts/validacao-esquema16.md`, sem atribuir à composição os resultados anteriores.

## Validação e limites de publicação

O fluxo de navegador de lote deve verificar prévia, seleção, confirmação, aplicação de rascunhos e manifesto, preservando os relatórios e as rotinas tributárias anteriores. O contexto de empresa/período, origem e bloqueios continua sendo validado no servidor.

Windows x86/x64 exige build nativo do SHA final. Os workflows por PR filtram main/develop e não disparam automaticamente para uma base empilhada; o dispatch pelo CLI foi anteriormente recusado ao consultar api.github.com e a conexão GitHub disponível não oferece a ação. Não repetir sem mudança de disponibilidade, contornar o bloqueio ou tratar testes Linux como Windows. Docker local aprovado comprova apenas a imagem efetivamente testada, sem publicação em registro.

Não há alíquotas ou regras legais presumidas, CBS/IBS, dados reais ou homologação Prosoft/PVA. Centros de custo e critérios de conciliação continuam pendentes. Os anexos legados permanecem sem bytes/pixels e nenhum executável desconhecido foi executado. Todas as fixtures desta revisão são sintéticas.
