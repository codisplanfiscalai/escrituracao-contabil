# Integração contábil com preparação XML e esquema 17

## Base e composição

Base fiscal: [PR #18](https://github.com/codisplanfiscalai/escrituracao-contabil/pull/18), branch `feat/preparacao-documentos-itens-xml`, HEAD **`2a68f7452e739438cc2922dc2a3b5702a96291ea`**. O incremento contábil do [PR #17](https://github.com/codisplanfiscalai/escrituracao-contabil/pull/17), `18fb4ffab5f826cd95eaeca089b41f740864d6fd`, foi reaplicado na árvore isolada `/workspace/escrituracao-contabil-compat17`, branch `feat/contabil-compat-esquema17`.

Os seis commits anteriores aplicaram sem conflitos, com novos identificadores `ad0e429`, `1498f65`, `998681f`, `9c62924`, `330b7ac` e `6616074`. O complemento desta etapa reconcilia as expectativas/fixtures e acrescenta testes contábeis de preparação/evidência. Não aplicar cumulativamente os commits originais ou as composições anteriores sobre esta árvore. Os PRs e branches anteriores são preservados.

O patch temporário citado no PR fiscal não estava disponível neste executor; as alterações foram refeitas diretamente após leitura do código/testes da base e validadas nesta composição. Não se atribuem a este SHA os resultados da composição temporária fiscal ou os builds do PR #18.

Não há nova migração contábil 17/18. Persistência, fechamento, preparação XML, leitor de itens, lote e motor tributário, ajustes/saldos, templates e renders permanecem idênticos à base fiscal. O painel contábil compõe o controlador Vue conservando o mixin e as ações fiscais. A aplicação continua integrada, com Windows gráfico/tray e execução servidor Docker.

## Expectativas e migração

Seis expectativas em cinco testes contábeis históricos passaram de 16 para 17. As fixtures que representam esquemas 10, 13, 14 e 15 retiram também `document_preparation_batches`, ausente nessas versões. A verificação continua preservando dados, hashes, memórias, partidas e bloqueios; não se limita ao número da versão.

A nova fixture 16→17 cria, antes da migração, movimentos escriturados com memórias documentais v1, manifesto do lote tributário, ajustes, apuração e ambos os módulos encerrados. Retira a estrutura exclusiva de 17, marca 16 e reabre pelo mecanismo normal. Compara integralmente as tabelas preservadas e o relatório/hash, exige integridade referencial e confirma histórico de preparações inicialmente vazio. Trata-se de banco sintético que representa o esquema anterior, sem alegar migração de dados reais.

## Contratos entre preparação, tributação e livros

- Preparar documentos cria rascunhos e manifesto; observar/copiar valores XML não cria partidas ou títulos.
- A evidência XML é conservada separadamente dos valores atuais e das decisões tributárias. Não define CFOP da empresa, tratamento, tributo, incidência ou alíquota legal.
- Com evidência, memórias documentais v2 e por item v4 coexistem e preservam seus vínculos individuais. O lote não agrega nem compensa seus efeitos nos livros.
- Diário, Razão e Balancete recebem as contas, datas e valores explicitamente informados somente após conferência/escrituração individual. Cálculo tributário conserva as partidas propostas.
- Históricos escriturados conservam payload, evidência, memória e hashes de relatórios após observação posterior da fonte; consulta não recalcula ou reescreve o passado.
- Repetir a preparação original após escrituração/fechamento recupera o manifesto sem novas operações ou partidas.
- Fechamento contábil impede preparação de rascunhos mistos mesmo com fiscal aberto. Recepção e consulta de evidência continuam possíveis e não contornam o bloqueio.
- Manifestos, evidências e relatórios permanecem restritos à empresa proprietária.

## Testes acrescentados e resultados

`tests/test_accounting_preparation_schema17.py` acrescenta quatro cenários conjuntos:

1. Evidência e memória por item v4 sem movimentos até escrituração; depois duas partidas somam débitos/créditos de 100,00 em cada relatório. Mudança posterior da fonte e repetição após fechamento não alteram o histórico ou os originais.
2. Lote com memórias XML documental v2 e por item v4 mantém seus vínculos e os livros vazios até escrituração individual; depois quatro partidas somam 200,00. Acesso por outra empresa é recusado.
3. Contábil fechado/fiscal aberto bloqueia preparação, mantém relatório e permite somente recepção/consulta, sem manifesto novo.
4. Migração sintética 16→17 preserva livro/hash, originais, partidas, cálculos, lote, ajustes, apuração e bloqueios.

Execução direcionada `test_accounting*.py`: **52 testes aprovados**. A suíte completa, navegadores, Docker e CI devem ser registrados pelo HEAD final efetivamente executado na descrição do PR, na conversa e em `artifacts/validacao-esquema17.md`. Esse artefato local é ignorado pelo Git para manter estável o SHA validado.

## Publicação, builds e pendências

A revisão autorizada é em rascunho contra a branch do PR #18, contendo apenas o incremento contábil. Sem merge, release, implantação ou alteração das branches anteriores.

Os workflows de build por PR filtram main/develop e não esta base empilhada. Windows x86/x64 exige build nativo deste HEAD; os builds fiscais anteriores não validam esta composição. O dispatch pelo CLI foi anteriormente bloqueado por Forbidden em api.github.com antes do envio, e o conector disponível não oferece a ação. Não repetir sem alteração de disponibilidade nem contornar o bloqueio. Docker local comprova somente a imagem construída/testada, sem publicação em registro.

Somente fixtures sintéticas, sem homologação fiscal, Prosoft/PVA, regras ou alíquotas legais presumidas. CBS/IBS continuam excluídos. A cobertura/leiaute XML é a descrita na documentação fiscal da base, sem ampliar por inferência. Centros de custo, critérios/importadores de conciliação e demais requisitos ainda não concluídos permanecem pendentes.

Os anexos legados seguem sem bytes/pixels acessíveis por falha de transferência já registrada. Não houve nova tentativa sem mudança de disponibilidade, execução de EXE desconhecido, inspeção visual alegada ou promessa de recuperar código-fonte completo. O levantamento permanece aberto.
