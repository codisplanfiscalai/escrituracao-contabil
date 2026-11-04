# Evidências de lote fechado — contrato antes da implementação

Fluxo: consultar lote fechado e seu snapshot → solicitar evidências com hash conferido e motivo → preservar arquivos determinísticos no banco → consultar histórico → baixar artefatos com registro da entrega local. O perfil `accounting-evidence-v1` é próprio da aplicação; não é Prosoft, EFD, arquivo de importação, assinatura digital ou comprovante de escrituração externa.

## Artefatos e integridade

Cada lote fechado tem no máximo uma exportação deste perfil. A exportação contém:

- `evidence.json`: envelope versionado, identificação do lote, revisão e evento de fechamento local, hash do snapshot, snapshot integral com empresa/período/plano, decisões documentais, fontes/observações, contas/mapeamentos e partidas/totais. Valores monetários continuam texto decimal. Não inclui bytes originais XML/SPED; inclui hashes, observações preservadas e localizações. Os originais permanecem no banco local.
- `postings.csv`: uma linha por partida, com contexto, IDs/versionamento, origem escolhida, revisão, conta, mapeamento, histórico, valor e hash do snapshot. É uma visão tabular; o JSON é a representação integral. Campos textuais de entrada são prefixados por um apóstrofo para evitar interpretação como fórmulas ou perda de zeros/chaves longas em planilhas. Para recuperar o texto exato dessas colunas, remova somente o primeiro apóstrofo; o manifesto lista as colunas. Valores decimais e IDs inteiros próprios não recebem prefixo.
- `manifest.json`: perfil, lote, hash do snapshot, totais/contagens, declaração de uso histórico e hashes SHA-256/tamanhos de `evidence.json` e `postings.csv`, com formato CSV. O SHA-256 do próprio manifesto consta dos metadados persistidos, sem auto-referência circular.

JSON canônico UTF-8 sem BOM, chaves ordenadas, separadores compactos, sem floats/NaN e com quebra de linha final. CSV UTF-8 com BOM, delimitador vírgula, CRLF e aspas produzidas pelo módulo csv. Nenhum instante ou motivo da solicitação é inserido nos artefatos; assim, a repetição devolve bytes idênticos. Instantes/motivos/ator das solicitações ficam na auditoria externa aos arquivos. Ator é o operador local declarado, não identidade autenticada.

Antes da primeira exportação: exigir lote fechado, metadados de revisão e fechamento, hash informado igual ao hash persistido e ao hash recalculado do snapshot, evidência auditada de fechamento coerente e vínculos internos entre linhas/revisões/fontes/contas. Validar valores/totais de forma independente da situação atual das fontes. Não recalcular o snapshot a partir de fontes ou mapeamentos atuais. Alterações posteriores podem gerar bloqueios atuais no lote, mas não alteram o histórico exportável nem os arquivos anteriores.

Uma exportação existente é reutilizada e conferida pelos hashes persistidos; adulteração ou arquivo ausente interrompe a entrega. Os hashes detectam inconsistência em relação ao banco, sem atestar autenticidade externa ou proteger contra alguém que possa adulterar simultaneamente conteúdo e hashes do próprio banco.

## Persistência e contratos para API

Migração aditiva transacional 1/2/3→4, sem reescrever dados ou snapshots. Novas tabelas guardam metadados da exportação e os três artefatos BLOB, ligados ao lote e empresa. Criação dos artefatos e auditoria pertencem à mesma transação. Índice único por lote/perfil impede duplicação concorrente. Toda repetição e leitura de arquivo registra ator, instante, identificadores e hashes; entrega registrada significa disponibilização pelo programa, não confirmação de salvamento pelo navegador nem transmissão externa.

Métodos do armazenamento:

- `create_evidence_export(company_id, batch_id, snapshot_hash, reason)`: retorna metadados com `id`, `profile`, `batch_id`, `snapshot_hash`, `manifest_sha256`, `artifacts` (nome, MIME, SHA-256 e tamanho), `duplicate`. Exige motivo e hash conferido.
- `list_evidence_exports(company_id, batch_id=None)`: lista metadados da empresa, sem bytes.
- `read_evidence_artifact(company_id, export_id, name)`: retorna nome, MIME, SHA-256, tamanho e `content` bytes, após verificar escopo/integridade e auditar a disponibilização.

Interface HTTP/visual implementada em Contabilização local, nos lotes fechados. O navegador confere SHA-256 e tamanho antes de disponibilizar o download. Rotas: GET/POST `accounting-evidence`; GET `accounting-evidence-file` com `company_id`, `export_id`, `name`. Nomes aceitos são os três nomes fixos; nenhum caminho do cliente é usado para gravar ou ler arquivos. Autorizações loopback/token/Host/Origin existentes permanecem aplicáveis. A criação de evidências não altera `ready_for_export=false`, que continua significando ausência de exportador Prosoft.

## Aceite e limites

Testes fictícios para lote não fechado ou sem revisão, isolamento, hash adulterado, vínculos/totais inconsistentes, repetição e concorrência, bytes idênticos entre sessões, snapshot histórico após novas fontes/mapeamentos/revisões, CSV seguro, trilha persistente e rollback em falha de auditoria/migração. Nenhuma regra fiscal, classificação CBS/IBS, conta ou formato Prosoft será inferido. Sem transmissão, certificado, assinatura, reconciliação Prosoft ou homologação.

## Resultado e verificação

Implementado em `src/evidence_export.py`, integrado a `AccountingStore` e ao esquema 4. Os metadados retornam os três artefatos, inclusive o próprio manifesto, com tipos/tamanhos/hashes para conferência no cliente. A entrega verifica todos os arquivos do conjunto antes de registrar a disponibilização de um deles.

Em 2026-11-04, 15 testes novos de evidências passaram. A suíte compartilhada completa passou com 125 testes, incluindo os dois testes HTTP acrescentados pelo integrador; `compileall`, `node --check` e `git diff --check` passaram. Estes resultados locais não comprovam execução Windows, Chromium, compatibilidade Prosoft ou validação fiscal. Testes contêm somente dados fictícios; conexões SQLite de preparação usam fechamento explícito para preservar portabilidade Windows.
