# Integração contábil com a base fiscal de esquema 13

## Base e resultado

Foi conferido o PR fiscal [#8](https://github.com/codisplanfiscalai/escrituracao-contabil/pull/8), aberto em rascunho para `develop`, e obtido o HEAD exato **`64378f695919c3816840b9eb29c669c762fc6ca1`**. A integração foi preparada na branch local `feat/contabil-compat-esquema13`, árvore `/workspace/escrituracao-contabil-compat13`, criada diretamente nesse commit. A branch fiscal foi preservada; não houve merge de PR, release ou implantação.

O incremento contábil inicial `468539c09e14a4d0f080667156ff8b0d5ba26d87` foi aplicado nessa árvore por cherry-pick. O commit resultante, já com a resolução de conflito, é `724bc85`. O commit posterior desta integração acrescenta testes conjuntos e atualiza a documentação histórica. Para integrar em outra árvore fiscal no mesmo HEAD, usar a sequência de commits posterior a `64378f6`, não reaplicar também o incremento original `468539c`.

## Conflito encontrado e resolução

Houve **um único arquivo com conflito textual**, `src/web/workbench.js`. A frente fiscal acrescentou o mixin `TaxUI`, os campos de busca, `moduleStates`/`moduleClosing` e os fluxos de cálculo/apuração. A frente contábil substituiu a função de renderização para acrescentar seu painel de consultas por Vue Teleport.

A resolução manteve ambas as definições de componentes e criou a aplicação com **`mixins:[TaxUI]` e a renderização contábil**, preservando integralmente o objeto de dados e os métodos da base fiscal. Não foram removidos recursos de tributação, campos calculados, estados de encerramento, busca de fontes, exportação ou contexto por empresa. A execução do navegador tributário completo confirmou que o mixin continua acessível e funcional.

Não houve conflito de esquema: este módulo contábil não acrescenta tabelas ou migrações. `src/persistence.py`, `src/module_closure.py`, `src/work_store.py`, `src/work_books.py`, `src/work_domain.py`, `src/tax_engine.py`, `src/tax_assessment.py`, `src/tax_api.py` e os templates/renders são idênticos ao HEAD fiscal conferido. **Não foi criada outra migração 13, não houve renumeração e não foi simulado suporte à versão 13 apenas alterando o número aceito.**

## Contratos preservados

- `tax_calculation` permanece no payload versionado da operação, com ID, hash e memória de cálculo. `tax_adjustment_of` e sua justificativa continuam explícitos e validados pela base fiscal. Os relatórios leem o livro canônico; não removem campos, recalculam tributos ou criam contrapartidas.
- Um tributo calculado em 2,51 sobre o documento sintético de 100,30 não muda as duas partidas explícitas de 100,30. Um ajuste tributário com partidas explícitas de 2,51 aparece como outro evento no Diário; não é compensado ou omitido pelo saldo da apuração fiscal.
- O hash de origem de cada linha e o hash do livro mantêm o vínculo com os snapshots escriturados, incluindo os campos fiscais calculados. Consultar não grava memórias, movimentos ou novas revisões.
- O fechamento fiscal exige a apuração parametrizada atual validada quando aplicável. O contábil exige a abertura/saldos e suas conferências. As guardas da base fiscal permanecem nas transações de escrita; a rota `accounting-report` continua somente GET e disponível para consulta de períodos encerrados.
- Fiscal encerrado com contábil aberto permite ajuste exclusivamente contábil. Operação mista é recusada se o contábil estiver encerrado, mesmo com fiscal aberto e valores tributários preenchidos. Recepção posterior continua preservando o original; organização em fiscal encerrado não é efetivada.
- Uma regra tributária com nova vigência futura não recalcula a operação já escriturada nem altera seu relatório histórico. Os planos, empresas e competências continuam separados.

## Testes conjuntos acrescentados

`tests/test_accounting_schema13.py` acrescenta seis testes, todos com dados inteiramente sintéticos:

1. Cálculo tributário preserva as partidas e o total contábil; Diário/Razão/Balancete não alteram a memória de cálculo nem gravam dados.
2. Fechamento fiscal depende da apuração validada; relatórios permanecem legíveis após fechar fiscal e contábil; novas escritas são bloqueadas e recepção posterior não contorna a organização bloqueada.
3. Contábil encerrado e fiscal aberto recusam uma operação mista com campos tributários, sem movimentos, operações ou memórias parciais.
4. Ajuste com `tax_adjustment_of` preserva vínculo, memória e partidas explícitas; saldo aritmético fiscal zero não elimina o movimento contábil do ajuste.
5. Regra futura preserva os valores e hashes dos relatórios históricos.
6. Base sintética com estrutura do esquema 10 é reaberta no esquema 13, preservando bytes/hashes dos originais, payloads das partidas, abertura e hash do relatório; `foreign_key_check` sem erros. É um teste de migração com fixture sintética, não atualização de banco real.

Os 12 testes contábeis anteriores também passaram sobre a base 13, incluindo HTTP local/token, portal/autenticação/escopo, rejeição de POST, filtros, hierarquia, precisão e reinício.

## Validação local executada

| Verificação | Resultado |
|---|---|
| `python3 scripts/build.py check` | Exit 0 |
| Aplicação conjunta | **294 testes aprovados** |
| Distribuição | **18 testes: 17 aprovados e um DPAPI omitido no Linux** |
| Ferramentas/auxiliares de CI | **30 testes aprovados** |
| Templates, Python, JS, matemática monetária, ícones e smoke autenticado | Aprovados |
| `python3 qa/accounting_reports.py` | Local e portal aprovados; recorte, saldos, hierarquia, invalidação de filtros, troca de empresa, desktop/móvel |
| `python3 qa/tax_browser.py --screenshots /tmp/contabil13-tax-qa` | Cadastros, regra aprovada, cópia independente, cálculo/conferência/escrituração, apuração, memória JSON e fechamento fiscal aprovados |
| `python3 qa/module_closure_browser.py` | Fechamento/reabertura fiscal independente, contábil aberto e persistência após reload aprovados |
| `python3 qa/integrated_flow.py` | Fluxo local e portal, incluindo escrituração, liquidação, livros e encerramento, aprovado |
| `python3 qa/navigation_audit.py` | Navegação local/portal, guias, permissões, persistência e teclado aprovados |
| `git diff --check` | Aprovado |

As imagens do relatório próprio em desktop e móvel foram inspecionadas por pixels. Não há transbordamento horizontal da página/iframe nos testes; tabelas largas usam rolagem interna. O navegador não registrou erros JavaScript. São telas geradas com fixtures sintéticas, não os prints de referência. O screenshot móvel do cenário tributário herdado pode capturar a transição animada da barra lateral; seus asserts de largura e o fluxo funcional passaram, sem que essa captura isolada seja tratada como homologação visual.

## Limites e entrega

A CI e os builds Windows/Docker aprovados que constam no PR #8 dizem respeito ao seu HEAD fiscal `64378f6`; **não comprovam a combinação local**. Não foram disparados CI remota, Windows x86/x64, DPAPI ou smoke de imagem publicada para o novo conjunto. Nenhum workflow, empacotamento ou Dockerfile foi alterado pelo incremento contábil. `actionlint` não foi reexecutado nesta árvore; o validador foi registrado como aprovado somente pela frente fiscal no seu HEAD.

Não houve push ou publicação de PR da integração, alteração da branch fiscal, merge, release ou implantação. O estado de anexos permanece o documentado no inventário: 13 executáveis e 13 prints contábeis sem bytes locais, com transferência bloqueada. Nenhum binário desconhecido foi executado ou analisado. Centros de custo, critérios de conciliação, leiautes bancários e modelos específicos de referência permanecem abertos; não há validação Prosoft/PVA ou fiscal com dados reais.

Para revisão, comparar a branch `feat/contabil-compat-esquema13` contra `64378f695919c3816840b9eb29c669c762fc6ca1`. A diferença contém o incremento de relatórios, a composição Vue resolvida, seus testes e esta documentação. A revisão não deve substituir a branch fiscal inteira nem reaplicar sua migração 13.
