# Integração contábil com importação fiscal e esquema 14

## Base e composição

Base fiscal conferida: [PR #11](https://github.com/codisplanfiscalai/escrituracao-contabil/pull/11), HEAD **`db62bc86adf66d72e18d76a27aed21ac844dcdd1`**. A combinação foi preparada na árvore isolada `/workspace/escrituracao-contabil-compat14`, branch `feat/contabil-compat-esquema14`. Os PRs #9, #10 e #11 não foram alterados; não houve merge, release ou implantação.

O PR contábil #9 continua no HEAD `c4a7a31404f49ba53a01db64192be10e00804a1a`. Seus dois commits e o teste adicional da validação por item `d7a0ffa490353ae07da4dd870aa6b5572694f2c0` foram reaplicados sobre o HEAD do #11 como `be6ef36`, `c0dfa88` e `c6502a9`, sem conflitos. O complemento desta branch atualiza expectativas de testes, acrescenta cobertura de catálogos e mantém os documentos anteriores identificados como históricos.

Não foi criada uma migração contábil 14 ou 15. Persistência, importação de cadastros, motor tributário, fechamento por módulo, templates e renders da base #11 permanecem intactos. A única composição de código de produção continua em `src/web/workbench.js`, preservando o mixin tributário e todos os campos/ações da base fiscal junto ao painel de relatórios. `src/accounting_api.py` registra a consulta GET existente; `src/work_reports.py` continua reutilizando o livro canônico, sem escrever movimentos ou recalcular tributos.

## Expectativas reconciliadas

Antes do ajuste, foram reproduzidas as duas falhas informadas em `tests/test_accounting_schema13.py`: o banco retornava 14, mas os testes ainda esperavam 13. As expectativas desses dois testes foram corrigidas para 14. O teste posterior de convivência de memórias v1/v2 em `tests/test_accounting_tax_items.py` também continha uma assertiva 13, reconciliada para 14.

O cenário de migração sintética 10→versão atual passou a remover também as três tabelas que só existem a partir de 14, antes de abrir a fixture antiga, evitando que a preparação já contenha estruturas futuras. Não foram enfraquecidas as verificações de originais, movimentos, hashes ou vínculos.

## Contratos fiscais e contábeis

Catálogos importados são dados recebidos e revisados, por empresa, sistema, jurisdição, edição e vigência. Não constituem carga normativa oficial, classificação tributária automática ou tabela legal certificada. O contábil não infere contas a partir de CFOP/NCM nem consome o cabeçalho como saldo tributário líquido.

As linhas de memória por item preservam `catalog_references` e `import_origin`, incluindo hash bruto, edição, referência da aplicação e datas de origem. Alteração de catálogo aplicável a um rascunho exige recálculo antes da conferência/escrituração; a tentativa recusada não pode produzir movimento, título ou evento parcial. Após a escrituração, a memória histórica permanece preservada.

Ativação com vigência local futura não reescreve o livro do mês encerrado. Recepção de novo arquivo continua permitida; ativação que alcance fiscal encerrado é recusada. Relatórios de fiscal/contábil encerrados continuam consultáveis. ST, DIFAL, retenções e efeitos por item permanecem separados e não compensam automaticamente partidas ou títulos. CBS/IBS continuam fora do cálculo.

## Testes conjuntos acrescentados

`tests/test_accounting_catalog_schema14.py` acrescenta três testes, usando apenas fixtures sintéticas:

1. Origem importada preservada nas duas linhas de cálculo com efeitos mistos; apuração −1,47 e partidas de 100,30; recepção após fechamento, bloqueio de ativação retroativa, aplicação futura sem alteração do relatório histórico, memória ou estados fiscal/contábil; isolamento de empresa.
2. Alteração aplicável do catálogo invalida o rascunho e bloqueia a postagem sem movimentos ou títulos parciais. Recálculo gera outra memória com a edição nova e permite escrituração explícita; a edição anterior permanece preservada.
3. Migração sintética 13→14 preserva bytes/hashes dos originais, payloads das partidas, memória tributária por item, hash do relatório e os dois bloqueios de módulo. Novos catálogos começam vazios e `foreign_key_check` permanece sem erros.

A execução direcionada de todos os arquivos `test_accounting*.py` passou com **40 testes** depois dos ajustes. A validação completa, os cenários de navegador e, se executado, o build/smoke Docker devem ser registrados pelo SHA final da composição, sem atribuir à combinação os resultados remotos dos PRs anteriores. O registro final desta execução fica na conversa e no relatório gerado fora do Git em `artifacts/validacao-esquema14.md`.

## Entrega e limites

A branch é uma candidata de integração pronta para revisão, não um merge ou release. Não alterar os PRs existentes nem presumir que publicar essa referência foi autorizado por esta validação. O esquema 14 exige o código atual; a aceitação de perfis JSON e as guardas dos incrementos anteriores devem continuar presentes no executável distribuído.

Windows x86/x64 exige execução nativa ou o workflow de build no SHA publicado. O executor de validação é Linux; a ausência de dispatch na conexão GitHub e a recusa anterior do CLI para `api.github.com` não devem ser contornadas nem apresentadas como um build realizado. O smoke Docker local, quando concluído, comprova a imagem construída, não publicação em registro ou homologação operacional.

Permanecem pendentes os builds/CI remotos específicos desta composição, a decisão de publicação/revisão integrada e a homologação com dados reais e parâmetros autorizados. Os anexos legados continuam sem bytes/pixels acessíveis; nenhum executável desconhecido foi executado e nenhuma regra foi deduzida de tela não inspecionada. Centros de custo, critérios de conciliação, integração Prosoft/PVA e fontes normativas completas permanecem fora desta entrega.
