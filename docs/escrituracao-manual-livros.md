# Escrituração manual e livros locais

O motor `manual-journal-v1` permite escriturar partidas explícitas sem exigir XML,
SPED ou mapeamento de uma conta de origem. A seleção do plano e de contas
analíticas é obrigatória. Cada grupo deve equilibrar débitos e créditos na mesma
data, dentro da competência dos movimentos. Valores são textos decimais com até
duas casas e são somados com `Decimal`; floats são recusados.

O lançamento passa por `previa`, `revisado` e `fechado`. Uma edição cria nova
revisão, preserva o snapshot anterior como `substituido` e exige nova revisão
explícita antes do fechamento. A edição compara `expected_version` para impedir
sobrescrita de uma alteração concorrente. Empresa, período e plano permanecem
vinculados ao lançamento. O fechamento recebe o hash da revisão conferida.

`request_key` identifica a tentativa de gravação por empresa. Repetir a mesma
chave e conteúdo devolve a revisão original; mudar o conteúdo com a mesma chave
é recusado. O replay de uma tentativa antiga não recupera essa revisão como
vigente. Gravação, auditoria e reserva da chave são transacionais.

Lançamentos fechados permanecem preservados. O estorno cria outro lançamento
com as mesmas contas, grupos, históricos e valores, lados invertidos e vínculo
`reversal_of` com o original. Pode usar outro período, com data igual ou posterior
à última partida original. O estorno também exige revisão e fechamento. Há um
único estorno vinculado por original; repetir exatamente os mesmos parâmetros
devolve o estorno existente. Edição de estorno e estorno de estorno não são
oferecidos neste incremento. Ajustes adicionais podem ser escriturados como
lançamentos manuais explícitos.

O operador informa uma referência e o motivo de cada decisão. Essa referência é
declarada pelo operador: não constitui vínculo documental validado. Evitar
duplicidade entre um lançamento manual e um documento já contabilizado exige
conferência humana; não há inferência automática de equivalência entre eles.

## Livros de movimentos

`accounting-movement-books-v1` reúne lotes documentais fechados e lançamentos
manuais fechados do mesmo período e plano. A leitura ocorre em uma transação
SQLite. Prévia, revisão ainda aberta e versões substituídas não entram nos livros.
Os snapshots históricos e seus hashes são verificados antes de compor os livros.
Uma mudança posterior na fonte importada não reescreve um lote fechado.

- Diário: ordem por data, tipo de origem, identificador e número da partida.
- Razão: movimentos por conta, com acumulado de débitos menos créditos.
- Balancete de movimentos: débitos, créditos e diferença por conta movimentada.

Não há saldos de abertura neste incremento. O acumulado do Razão é a diferença
dos movimentos selecionados e não representa o saldo patrimonial da conta.
`opening_balances_included=false` e `balance_convention` registram esse limite
no JSON. Contas sem movimentos não aparecem no balancete. Períodos distintos
continuam separados mesmo quando usam o mesmo mês de processamento.

Cada linha identifica origem manual/documental, versão, hash, conta, data,
histórico e referência. Linhas documentais mantêm também documento e observação
de origem. No conjunto de fontes, lançamentos manuais registram o vínculo de
estorno, quando existente.

## Exportação preservada

A exportação exige o `book_hash` da prévia atual e motivo. Preserva cinco arquivos
no SQLite privado: `books.json`, `diario.csv`, `razao.csv`,
`balancete-movimentos.csv` e `manifest.json`. O manifesto identifica o contexto,
o hash dos livros, o hash SHA-256 e o tamanho de cada arquivo de conteúdo. O hash
do próprio manifesto é preservado no registro de exportação. O download verifica
o conjunto de arquivos, os hashes e a correspondência com o manifesto.

CSVs usam UTF-8 com BOM, vírgula e CRLF. Colunas textuais recebem um apóstrofo
inicial para preservar códigos e impedir fórmulas em planilhas; remover exatamente
o primeiro apóstrofo recupera o texto. O JSON preserva os textos originais. Novos
fechamentos alteram a próxima prévia, mas não os arquivos de uma exportação já
preservada. Uma prévia antiga é recusada quando os livros mudaram. Repetir uma
exportação da mesma prévia reutiliza o conjunto preservado e registra a repetição
na auditoria.

São arquivos locais de conferência. Não são ECD/EFD nem CTBLCTOS importável.
Não houve homologação no Prosoft ou validação em PVA. Os indicadores
`prosoft_validated=false`, `pva_validated=false` e `externally_posted=false`
acompanham os livros. Não se calcula CBS/IBS.

## Contrato para a interface

As rotas abaixo estão disponíveis no servidor local e no portal autenticado,
sob `/api/`. GET exige permissão `workspace.read`; gravação exige
`workspace.write`; revisão, fechamento e geração de exportação exigem
`workspace.review`. Todas respeitam o escopo de empresas do portal. O cliente
externo não recebe essas rotas. POST usa as proteções de origem e CSRF existentes.

| Método e rota | Campos principais | Resultado |
| --- | --- | --- |
| GET `manual-journals` | `company_id`, opcionais `period_id`, `journal_id` | Revisões vigentes; com `journal_id`, histórico de versões |
| POST `manual-journals` | `company_id`, `period_id`, `plan_id`, `entries`, `reference`, `reason`, `request_key`, opcionais `journal_id`, `expected_version` | Revisão salva |
| POST `manual-review` | `company_id`, `journal_id`, `snapshot_hash`, `reason` | Revisão conferida |
| POST `manual-close` | Mesmos campos de revisão | Lançamento fechado |
| POST `manual-reversal` | `company_id`, `journal_id` original, `period_id` destino, `date`, `reason`, `snapshot_hash` original | Prévia de estorno vinculado |
| GET `accounting-books` | `company_id`, `period_id`, `plan_id` | Diário, Razão, balancete, totais, fontes e `book_hash` |
| GET `accounting-book-exports` | `company_id` | Exportações preservadas e metadados de arquivos |
| POST `accounting-book-exports` | `company_id`, `period_id`, `plan_id`, `book_hash`, `reason` | Identificador e arquivos da exportação |
| GET `accounting-book-file` | `company_id`, `export_id`, `name` | Bytes com tipo de conteúdo e `Content-Disposition: attachment` |

Uma partida manual em `entries` contém `date` ISO, `group`, `side` (`D`/`C`),
`amount` como texto decimal, `account_id` e `memo`. `expected_version` é um número
inteiro JSON: zero na criação e a versão vigente na edição. As respostas seguem
o envelope existente `{data: ...}`, exceto o download de arquivo.

Schema SQLite 7: as tabelas de lançamentos manuais e livros são adicionadas em
migração transacional. Registros e snapshots das tabelas anteriores são
preservados. A interface visual pertence à frente de interface; este incremento
fornece o serviço e o contrato para conectá-la sem alterar os arquivos web.

## Verificação e referências

Os testes usam exclusivamente empresas, planos, referências e documentos
sintéticos. Cobrem revisão/fechamento, edição concorrente, replay de tentativas,
rollback, estorno entre períodos, precisão decimal, combinação com lotes
documentais, isolamento por empresa, permissões e downloads, integridade dos
arquivos e proteção contra fórmulas em CSV.

Verificação local deste incremento: `python scripts/build.py check` passou com
201 testes da aplicação, 18 de empacotamento (um teste de DPAPI omitido por exigir
Windows) e 18 da esteira de entrega, além de compilação, sintaxe JavaScript,
validação de ícones e smoke local do portal. `actionlint` 1.7.12 e
`git diff --check` passaram. Não foram executados build nativo Windows,
homologação Prosoft/PVA ou implantação.

Os anexos `Prosoft.zip` e `geradorsped-main.zip` foram resolvidos pela Library,
mas a materialização foi bloqueada pelo proxy do ambiente com HTTP 403 no host
de download. Não foi possível ler o PDF de layout ou o código do gerador.
Portanto, os tamanhos informados de LC1/LC2 não foram tratados como especificação
suficiente para criar um exportador CTBLCTOS. Anexos e dados privados não foram
incorporados ao repositório.
