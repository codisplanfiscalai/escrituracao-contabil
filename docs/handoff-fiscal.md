# Handoff — Escritura, incremento fiscal de 04/11/2026

## Identificação e objetivo

- Repositório: https://github.com/codisplanfiscalai/escrituracao-contabil
- Branch: `feat/fiscal-entry-ledger`, destinada a PR rascunho para `develop`.
- Base inspecionada: `a1e8932949d28eba9dfe604d660d4b0f61f59f6b` (pré-release 0.3.0-dev.6.1).
- Commit exato de implementação/testes: `29e114eaa6a908e95296b0fefa9cc9902e57e11a`.
- Este handoff é um commit documental posterior; use o HEAD publicado da branch e confira o SHA antes de continuar.
- Objetivo: produto persistente multiempresa de escrituração fiscal/contábil, Windows offline com GUI/bandeja e servidor, com integração Prosoft comprovada. Produto completo ainda não entregue.
- Remoto conferido antes da publicação: develop permanecia na base acima e não havia PR aberto concorrente. Main não foi alterada; nenhuma implantação autorizada nesta etapa.

## Decisões e autorização

O usuário autorizou remover as restrições arbitrárias a modelo 65 e emissão fora da competência. Emissão, entrada/saída, escrituração e período-base são fatos distintos. Agosto-base/setembro-movimentos de 2026 é cenário inicial configurável, sem copiar movimentos de agosto. As quantidades relatadas (62 entradas, 34 emitidas em agosto, 28 em setembro; 363 NFC-e e 4 NF-e nas saídas) não foram reconferidas em arquivos reais.

Nova tela fiscal reúne entradas, saídas e serviços com inclusão/edição manual, guias persistentes e terceiros. Escrituração contábil manual geral e edição foram incluídas no plano, ainda não implementadas. Consulte [contrato funcional e próximos aceites](escrituracao-fiscal-manual.md).

## Arquitetura e arquivos relevantes

- Python, SQLite e camadas existentes de ingestão, reconciliação, mapeamentos, contabilidade e evidências; sem mudança abrupta de arquitetura.
- `src/persistence.py`: esquema 6 aditivo, arquivos originais e validação XML 4.00 55/65; mesma API de domínio para desktop e servidor.
- `src/fiscal_ledger.py`: fichas e revisões imutáveis de conteúdo, revisão explícita, controle por empresa/competência, propostas para períodos protegidos, vínculo explícito a documento e origem/hash.
- `src/fiscal_workspace.py`: terceiros por CPF/CNPJ/empresa, observações de nomes/papéis, revisão concorrente; guias por operador/empresa/período, versões e encerramento lógico.
- `src/reconciliation.py` / `reconciliation_store.py`: perfil XML `nfe-nfce-4.00-header-billing-v4`, SPED `efd-icms-ipi-020-c100-v2`; preservação dos perfis anteriores e reanálise explícita de arquivos rejeitados.
- `src/accounting_store.py`: snapshot inclui ficha fiscal; versão não revisada, fonte alterada ou divergência fiscal/contábil exigem tratamento; fechado não é sobrescrito.
- `src/local_app.py`, `src/server/app.py`: rotas reutilizam escopo da empresa, autenticação/CSRF e permissões de escrita/revisão existentes. Cliente externo não acessa os endpoints internos.
- `src/web/*`: formulário adaptável, seleção de fonte/terceiro, revisão/histórico, guias e controle de período. `src/portal/app.js`: navegação aguarda persistência da guia antes de substituir iframe.
- `tests/test_fiscal_ledger.py`, `tests/server/test_fiscal_http.py`, regressões contábeis e `qa/fiscal_browser.py` cobrem o incremento.

## Entregue e limites

| Área | Implementado nesta etapa | Limite explícito |
|---|---|---|
| XML | Cabeçalho 55/65; 65 sem destinatário; datas independentes; originais e avisos | Sem autorização, assinatura ou XSD integral |
| SPED | C100 parcial 020/2026, modelos 55/65, situações 00/01/06/07; DT_DOC e DT_E_S | Outros casos preservados como pendência; não gera SPED completo |
| Manual fiscal | Cabeçalho, datas, operações, serviço/ISS informado, revisões e motivos | Sem itens/tributos completos, NFS-e municipal ou cálculo ISS |
| Guias | Rascunhos persistentes e privados ao operador, concorrência e navegação segura | Não constituem fila de tarefas persistente |
| Terceiros | CPF/CNPJ, papéis, nomes de origem/divergências; XML e CNPJ de emitente pela chave SPED | Sem endereço/inscrições, estrangeiros ou parser 0150 completo |
| Períodos | Fechar/reabrir revisados; registrar exportação externa com referência; propostas | Não aplica retificação externa e não gera arquivo ao marcar exportação |
| Contabilidade | Protege snapshots e impede ignorar edição fiscal | Manual geral, estorno/ajuste, agregação diária, folha e CTBLCTOS pendentes |
| Prosoft | Limites preservados e adapters planejados separadamente | Nenhum layout inventado ou homologação executada |

Ficha manual com chave pode receber vínculo explícito ao documento importado depois, sem duplicação, mantendo a versão antiga sem fonte. Sem chave confiável, manter conferência humana. Terceiros de arquivos antigos exigem reanálise explícita; a migração não reinterpreta silenciosamente os originais.

## Execução e validação

```bash
python -m pip install --only-binary=:all: --require-hashes -r requirements-server.txt
python -m src.server.runtime --host 127.0.0.1 --database /caminho/privado/escrituracao.sqlite3
python scripts/build.py check
python qa/portal_browser.py --screenshots /tmp/portal-qa
python qa/fiscal_browser.py --screenshots /tmp/fiscal-qa
```

Portal em http://127.0.0.1:8765; token inicial em `identity/setup.token` junto ao banco. Nunca publicar o token/banco. QA de navegador requer Playwright/Chromium conforme `.github/workflows/tests.yml`. No Windows distribuído, abrir o executável GUI existente; comandos acima são ferramentas de desenvolvimento, não uma distribuição CLI.

Resultados locais no commit de implementação: 182 testes da aplicação; 18 de empacotamento (um DPAPI omitido no Linux); 18 de entrega aprovados. Smoke do portal/persistência, ícones, compileall, matemática Decimal/JS, node syntax, actionlint e diff-check aprovados. Chromium passou nos fluxos fiscal e portal; screenshots desktop e 390 px inspecionados, sem transbordamento horizontal/erros JS. Fixtures inteiramente fictícias.

CI confirmada no SHA `aa831a9362852ce3a446d6e6afbca6197b1708c9`: [run 41916458183](https://github.com/codisplanfiscalai/escrituracao-contabil/actions/runs/41916458183), todos os cinco jobs aprovados — Python 3.10/3.12/3.13, workflow lint e Portal browser (inclui regressão fiscal). Este registro documental é posterior àquela execução.

A criação do PR rascunho `feat/fiscal-entry-ledger` → `develop` foi negada pela revisão automática por falta de evidência de autorização explícita para publicar o PR. A branch já estava publicada; o PR não foi criado (consulta confirmou lista vazia), sem execução incerta, merge ou deploy. Histórico autorizado consultado; não houve tentativa por outra ferramenta. Autorização específica foi solicitada e permanece necessária antes de retentar.

A CI de Windows x86/x64 e contêiner deve ser conferida no SHA do PR novo; esses jobs não foram disparados porque o PR está bloqueado. A aprovação da release-base não comprova este incremento. Não houve teste Prosoft/PVA, homologação fiscal, teste real com documentos DIX ou deploy de produção.

Migração 5→6 é aditiva e testada preservando originais. Antes de atualizar um banco operacional, manter backup privado e testar restauração; binário antigo não deve abrir banco migrado de versão maior. Não remover tabelas para simular downgrade de produção.

## Próximos passos priorizados

1. Conferir PRs/branches/CI novamente antes de editar. Resolver falhas reais no novo SHA, validar x86/x64 e imagem construída. Não modificar main/develop diretamente nem fazer merge.
2. Implementar contabilidade manual/edição com identidade própria, partidas exatas equilibradas, vigência/contas analíticas, revisão e estorno/ajuste de fechado; seguir os aceites do documento funcional.
3. Completar itens fiscais, plano de escrituração padrão, justificativas/exceções, livros e apuração por contratos comprovados. Evoluir participantes/0150 e aplicação controlada de retificações.
4. Recuperar contratos/amostras acessíveis antes de pedir novamente. Seis formatos posicionais Prosoft e CTBLCTOS LC1/LC2 são adaptadores distintos de SPED oficial. Validar estrutura e depois importar no Prosoft de teste; reportar separadamente os resultados.
5. Planejar processamento diário agregado e identidade de origem para impedir duplicidade fiscal/folha/CTBLCTOS; reconciliação com Prosoft, contas a pagar/receber e livros completos ainda pendentes.
6. Fila local SQLite recuperável, ZIP/7z/RAR integrados com limites/segurança, paridade funcional desktop/servidor. GHCR/base/dependências continuam sujeitos a fornecedores e precisam de digests, licenças e política de atualização comprovados; não prometer independência absoluta.
7. APIs NF-e/NFC-e são expansão futura. CBS/IBS fora da apuração/classificação deste produto.

## Bloqueios e restrições

- Print `libfile_e109f96529f8819184c83c0c7091f4a6`: materialização autorizada da Library falhou com `library file transfer failed: download failed`; não houve imagem acessível nem inspeção. Nenhuma rota alternativa usada. Tela construída com identidade existente, sem copiar Prosoft.
- Layouts/exemplos reais Prosoft não foram materializados nesta etapa. Não presumir que arquivos existam neste ambiente nem contornar falha de acesso.
- Não publicar dados reais, documentos fiscais, bases, screenshots com dados reais ou segredos. Não criar credenciais/acesso persistente ou implantação de produção.
- Gerador SPED é referência de comportamentos, sem copiar código/ativos. Projeto CBS permanece independente.
- Não confundir testes locais, CI, validação de layout, importação Prosoft e homologação oficial.
