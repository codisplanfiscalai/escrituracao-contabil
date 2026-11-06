# Integração contábil com ajustes de apuração e esquema 15

Registro histórico do esquema 15 e PR #15. A composição com cálculo em lote e esquema 16 está em `frente-contabil-integracao-esquema16.md`; não atribuir os resultados abaixo a versões posteriores.

## Composição e isolamento

Base fiscal: HEAD **`3673c5a1212c29aff0c600e11bfd329f5d96022a`** do [PR #14](https://github.com/codisplanfiscalai/escrituracao-contabil/pull/14), branch `feat/ajustes-saldos-apuracao`. O incremento contábil do PR #12 (`bd45a656497cd7537b2931311386c31eb7a11742`) foi reaplicado em `/workspace/escrituracao-contabil-compat15`, branch `feat/contabil-compat-esquema15`.

A aplicação foi limpa, sem conflitos. Os quatro commits contábeis anteriores tornaram-se `eb6439f`, `3679b96`, `a672568` e `f1280c8`; o complemento desta etapa ajusta as expectativas para 15 e acrescenta testes conjuntos. Não reaplicar também os commits originais sobre essa composição. A branch fiscal e os PRs anteriores são preservados; não há merge, release ou implantação autorizados.

Não foi criada uma migração contábil 15/16. A persistência, `tax_balances.py`, FCP/cálculo por dentro, apuração, guardas de módulo, templates e render gerado permanecem os da base fiscal. O código de produção contábil continua sendo a consulta GET sobre o livro canônico e sua composição no controlador Vue. Partidas/títulos não são inferidos de saldos tributários.

## Reconciliação dos testes

Quatro assertivas ainda esperavam 14 nos arquivos de integração de esquemas anteriores e de itens; foram reconciliadas para 15. As fixtures de migração 10→atual e 13→atual passaram a remover também `tax_assessment_adjustment_versions`, pois essa estrutura não pertence aos bancos antigos simulados. Não foram removidas verificações de bytes, hashes, movimentos, memórias ou fechamentos.

Os arquivos de teste que mencionam 13/14 nos nomes preservam a origem histórica dos contratos, e suas docstrings identificam a execução atual em 15. Os testes de migração continuam verificando dados preservados, não apenas o número de versão.

## Contratos conjuntos

- Ajuste exclusivo da apuração e transporte de saldo usam as versões de `tax_assessment_adjustment_versions`. Eles não criam `work_operations`, partidas, títulos ou baixas. O relatório contábil não transforma seus valores em saldos iniciais.
- Cancelamento acrescenta história, libera reserva e invalida a apuração de destino, sem reescrever o livro ou a memória da origem. Fechamento contábil permanece independente das operações exclusivas do fiscal, que continuam sujeitas às próprias guardas.
- Um ajuste de apuração não substitui o ajuste fiscal vinculado a uma operação original. Estorno de operação tributada continua bloqueando a validação da apuração enquanto a cobertura por componentes não estiver explicitamente conferida no fluxo próprio.
- FCP e cálculo por dentro preservam os componentes e a conciliação da memória v3. O exemplo sintético de base líquida 100, tributos 25 e base declarada 125 gera somente as duas partidas explicitamente informadas de 125, sem contabilizar automaticamente 100 ou 150.
- A migração 14→15 é consumida da base fiscal e preserva originais, cálculos, apurações anteriores e bloqueios. CBS/IBS seguem fora do cálculo; os testes não conferem direito legal a crédito ou compensação.

## Cobertura acrescentada

`tests/test_accounting_assessment_schema15.py` acrescenta quatro cenários sintéticos:

1. Operação contábil de 100,30 com tributo 10,03 e ajuste de apuração a crédito de 3: a apuração passa a 7,03, mas relatórios/hashes, partidas e títulos permanecem idênticos, inclusive após cancelamento.
2. Transporte declarado de 60 sobre saldo 100 reserva 60/disponibiliza 40 sem criar abertura contábil. A origem não reabre enquanto houver reserva; cancelamento libera capacidade, preserva a memória original e mantém o fechamento contábil do destino.
3. Migração sintética 14→15 conserva memória v3 de FCP/cálculo por dentro, originais, partidas, apuração, hash do livro e ambos os bloqueios de módulo, com chaves estrangeiras íntegras.
4. Ajustes manuais da apuração para ICMS/FCP não satisfazem a exigência de ajuste fiscal vinculado do estorno. Continuam somente os dois eventos contábeis explícitos e suas quatro partidas.

A execução direcionada `test_accounting*.py` passou com **44 testes**. A suíte completa, navegadores, imagem Docker e eventual CI devem ser registrados pelo SHA final efetivamente executado; a conversa e `artifacts/validacao-esquema15.md` guardam os resultados finais sem atribuir à composição os checks anteriores.

## Publicação e limites

Se a validação conjunta for aprovada, a revisão é empilhada em rascunho contra `feat/ajustes-saldos-apuracao`, contendo somente o incremento contábil, testes/QA e documentação. O estado publicado e os links ficam na descrição do PR e na conversa. Não alterar ou fechar PRs anteriores como parte dessa ação.

Windows x86/x64 exige um workflow nativo no SHA final. Os filtros de build por PR cobrem main/develop, não bases empilhadas; o dispatch disponível via CLI foi anteriormente recusado em api.github.com, e a conexão GitHub não oferece essa ação. Não repetir a tentativa sem mudança do bloqueio nem tratar CI Linux como build Windows. Docker local construído e testado, quando registrado, não equivale a publicação da imagem ou release.

Permanecem fora da homologação: parâmetros e hipóteses legais de créditos/ajustes, integração Prosoft/PVA, dados reais, centros de custo e critérios de conciliação. Os executáveis/prints legados continuam sem bytes/pixels acessíveis e não foram executados. Todas as fixtures desta integração são sintéticas.
