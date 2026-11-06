# Análise e continuidade — 06/11/2026

## Resultado e estado inicial

Atualização tributária: o estado final usa esquema **13**, com [regras, tabelas, modelos e apuração parametrizada por empresa](tributacao-parametrizada.md). As limitações de ausência de apuração nos incrementos anteriores abaixo são históricas; não havia regras legais fornecidas e nenhum tratamento legal foi presumido no novo motor.

Atualização posterior: o novo requisito de encerramento independente foi implementado sobre este incremento. O estado final usa esquema **12** e guardas compartilhadas em `src/work_store.py`; consulte [contrato e validação do encerramento por módulo](encerramento-por-modulo.md). As menções ao esquema 11 e à ausência de alteração de `work_store.py` abaixo descrevem o primeiro commit cadastral, não o complemento posterior. A [descrição do PR em rascunho](pr-rascunho-cadastro-encerramento.md) foi preparada sem publicação.

O incremento entrega cadastro complementar de clientes, empresa usuária em registro separado, histórico cadastral, busca das fontes recebidas sem competência e inicialização Windows recolhida no tray. Não representa o sistema completo nem recuperação do código dos executáveis fornecidos.

O checkout inicial estava limpo, na branch `work`, SHA `0a2d29b84e37f57eb7622218d48382c6a5362f22`, versão 0.2.1. Antes de editar, foi consultada a `develop` remota: SHA `22ebdb14d812980dac532cd7c0403c2f811f559e`, versão 0.3.0. A branch local `feat/cadastro-clientes-busca-fontes` parte dessa revisão atualizada. As instruções AGENTS.md dessa base foram relidas. Não havia skills locais em `.agents/skills` no ambiente selecionado; foram utilizadas as skills atuais da Library e do ambiente. Nenhum agente adicional foi iniciado nesta tarefa.

A base atual já contém portal Vue, API Python/FastAPI, SQLite, identidade/permissões, recepção sem competência, ficha unificada fiscal/contábil/cobrança, conferência, escrituração, liquidações, estornos, livros e exportação operacional. Os documentos anteriores registram etapas históricas e não substituem a leitura do código atual.

## Aplicação integrada e configurável

Diretriz confirmada pelo usuário: uma aplicação dinâmica e integrada, com menus, módulos e relatórios ajustados por filtros e opções. Não haverá um EXE por cadastro, tela, livro ou variante de relatório. Os nomes dos binários recebidos são referências de levantamento, não unidades de implantação da nova aplicação. O frontend mantém guias e navegação integradas; a ordem dos menus já é configurável. Neste incremento, as cinco seções cadastrais são renderizadas a partir do catálogo de campos fornecido pela API, e a busca usa filtros no mesmo módulo de Recepção. A modularidade fica nos serviços e contratos internos. Relatórios futuros devem compartilhar motor e contexto, com opções explícitas, preservando o isolamento por cliente. Variantes de Diário/balancete não devem originar programas separados nem combinar empresas silenciosamente.

O cliente Windows continua sendo um aplicativo gráfico com tray, e o servidor usa a mesma aplicação e domínio em Docker. A ferramenta de triagem PE é um auxiliar de desenvolvimento, não outro aplicativo operacional. Não foram criados executáveis adicionais.

## Referências localizadas e bloqueio de leitura

Foram resolvidos 13 executáveis e 35 imagens: 27 prints iniciais, de cadastro/fiscal/contas/livros/apuração, e oito prints contábeis recebidos em seguida. Os tamanhos abaixo vêm dos metadados autorizados, não de leitura dos bytes.

| Executável | Referência informada | Bytes nos metadados |
| --- | --- | ---: |
| PRG010100.EXE | Cadastro | 2098704 |
| LFSDOCTOS.EXE | Documentos fiscais | 16602696 |
| LFSCTAPAGREC.EXE | Contas a pagar/receber | 1422864 |
| LFSLIVROS.EXE | Livros fiscais | 10790416 |
| LFSLIVROSAPUR.EXE | Apuração | 777952 |
| CTB010100.EXE | Plano de contas | 984592 |
| CTB020100.EXE | Digitação contábil | 1787408 |
| CTB020400.EXE | Razão | 1357328 |
| CTB020600.EXE | Diário individual | 984592 |
| CTB020800.EXE | Diário consolidado | 1160720 |
| CTB021300.EXE | Balancete em tela | 833040 |
| CTB021400.EXE | Verificação em tela II | 2094608 |
| CTB021500.EXE | Balancete por centro de custo | 595472 |

O fluxo de download da Library falhou com `hosted apps tools/list request failed: network`. A tentativa limitada com destino explicitamente local foi preparada pelos meios suportados e executada uma vez para cada referência; todas retornaram `library file transfer failed: download failed`. Verificação final da pasta consumidora: **zero arquivos**. Portanto, nenhum anexo foi confirmado como existente e legível localmente. A preparação das referências teve sucesso; a transferência dos bytes falhou. Não houve negação de aprovação automática nem execução de resultado incerto a repetir.

A leitura alternativa de cinco imagens devolveu descrições textuais e referências de imagem, sem pixels visíveis para inspeção. Essas descrições não foram adotadas como prova dos campos das telas. Não é possível confirmar tecnologia, bibliotecas, recursos de formulário, regras, hierarquia do plano, critérios de consolidação ou diferenças entre balancetes a partir desses resultados. Nomes de executáveis e extensão EXE não determinam linguagem.

Nenhum executável desconhecido foi aberto, carregado ou executado. Não houve envio de anexos a terceiros, upload de dados reais, publicação, PR, merge ou implantação. Os anexos e auxiliares de transferência ficam fora da árvore Git. Não se solicita reenvio dos arquivos como se não tivessem sido fornecidos: falta restabelecer sua transferência autorizada.

## Preparação da análise estática

`scripts/analyze_reference_pe.py` está disponível para quando houver bytes acessíveis. Lê arquivos de até 64 MiB, verifica limites dos cabeçalhos/seções/RVAs PE, calcula SHA-256, lista DLLs importadas e registra indícios de runtime CLR, Visual Basic, Python e possíveis marcadores Delphi/Borland/PyInstaller. Registra explicitamente que não executou o alvo e não recuperou código-fonte. Referências e saída são recusadas dentro da árvore do repositório.

Foi validado com estruturas PE inteiramente sintéticas, incluindo truncamento e endereço inválido. **Não foi aplicado aos executáveis enviados.** Indícios de runtime não provam linguagem de origem; ausência de indícios não identifica tecnologia. Inspeção de recursos/formulários e descompilação específica permanecem condicionadas ao acesso aos arquivos. Mesmo após esse acesso, não se promete código-fonte completo, comentários, nomes originais ou lógica integral recuperável.

## Cadastro implementado

Clientes continuam identificados por `companies.id`; documentos, planos, competências, títulos e movimentos mantêm seus vínculos existentes. A empresa usuária fica em `user_organization_versions`, sem `company_id`, e não é criada automaticamente na lista de clientes. Nenhuma empresa existente foi presumida como escritório. Cadastro próprio não recebe movimentos nem concede acesso a clientes.

O cadastro complementar usa `client_profile_versions`, com empresa, versão, dados declarados, hash, responsável, motivo e instante. Atualizações exigem versão atual e transação; uma gravação concorrente desatualizada é recusada. Histórico e dados de outro cliente não são mesclados. A migração **10 → 11** é aditiva e não reescreve originais ou movimentos.

Os campos abaixo foram propostos a partir dos requisitos explícitos, sem alegar extração dos prints:

| Seção | Campos implementados |
| --- | --- |
| Identificação existente | Razão social/nome, CNPJ e códigos Prosoft opcionais no cadastro inicial |
| Básicos | Nome fantasia, telefone, e-mail, CEP, logradouro, número, complemento, bairro, município, UF, código IBGE e início das atividades |
| Fiscais | IE, IM, CNAE principal, regime tributário declarado, CRT declarado e atividade |
| Trabalhistas | Código de recolhimento previdenciário, FPAS, código de terceiros, RAT/FAP informados e sindicato |
| Contábeis | Forma de escrituração, contabilista, CPF/CNPJ do contabilista, CRC e encerramento do exercício informado |
| Gerais | Contato responsável e observações |

Esses valores são cadastrais: não selecionam alíquotas, não apuram tributos/folha e não modificam políticas de contabilização. CEP/UF/IBGE, e-mail e data inicial recebem validações de formato; CNPJ não é certificado como autêntico. A atualização da identidade fiscal principal de empresas existentes continua fora deste formulário complementar. Campos opcionais não são completados por suposição. Dados salvos sobrevivem à recarga; campos ainda não salvos não têm recuperação durável implementada neste incremento.

No portal, o complemento está em Empresas; a empresa usuária está em Configurações. Acesso cadastral exige `companies.manage` e escopo de empresa; gravação de clientes preserva a restrição atual de administrador global. A empresa usuária exige `settings.manage`. O portal do cliente não recebe acesso aos dados trabalhistas/cadastrais internos. Ao trocar sessão, os novos objetos de cadastro são limpos da memória.

## Fiscal, livros, apuração e financeiro

Foi acrescentada busca em Recepção, antes de criar/abrir competência. Consulta nome de arquivo, chave, número e CPF/CNPJ identificados; permite tipo XML/SPED, intervalo de emissão e direção entrada/saída. A direção depende do CNPJ do cliente e de identificação não ambígua da contraparte. Fontes sem emissão identificada não passam pelo filtro de datas. A consulta não cria competências, documentos, movimentos ou títulos e retorna até 200 resultados, informando o total para refinar filtros. Pesquisa somente fontes já recebidas; não é busca na SEFAZ nem varredura do computador.

| Frente | Estado real |
| --- | --- |
| Recepção/importação | Já existente sem competência/plano, com originais e revisões; novo filtro de busca |
| Entradas/saídas | Ficha fiscal/contábil/cobrança e efetivação transacional já existentes; não substituem validação tributária integral |
| Livros fiscais | Livro operacional já existente, produzido a partir de operações; não equivale a modelo oficial homologado |
| Apuração | Não implementada; nenhuma regra foi deduzida de prints inacessíveis. CBS/IBS permanecem fora do cálculo |
| Pagar/receber | Títulos, saldo, vencimento, liquidações e estornos já existentes na base; não foram recriados |
| Baixa manual | Fluxo existente prepara operação própria, exige conferência e integra os movimentos internos |
| OFX/CNAB/TXT | Novos parsers/contratos de extrato e baixa por arquivo ainda pendentes; CNAB/TXT exigem leiaute e versão identificados |
| PDF/imagem | Extração/conferência e associação bancária ainda pendentes. OCR não autoriza baixa nem cria correspondência por suposição |
| Integração externa | Sem exportador Prosoft homologado, transmissão/PVA ou integração bancária automática |

## Contratos com a frente contábil separada

A frente contábil separada assumiu o levantamento específico dos anexos contábeis e sua implementação. Esta tarefa não altera seus motores. O código atual já oferece os pontos abaixo, inspecionados no repositório:

| Ponto | Contrato e limite |
| --- | --- |
| Plano | `import_work_plan`: CSV `codigo;descricao;tipo;natureza;superior`; atributos extras, inclusive acesso/classificador, são preservados; hierarquia e contas analíticas explícitas |
| Históricos/lançamentos | `work_revisions` preserva payload, versão, responsável, motivo e hash; partidas têm data, conta, lado, valor e histórico. Não há catálogo novo de históricos padronizados neste incremento |
| Fiscal → contábil/financeiro | `post_work_operation` materializa movimentos e vínculos de títulos na mesma transação; importação sozinha não efetiva escrituração |
| Financeiro → contábil | `prepare_work_settlement` referencia título/hash, valor, data e política; a liquidação não reconhece novamente compra/venda |
| Livros | `work_books`: Diário, Razão, balancete, fiscal e financeiro; valores Decimal, abertura e continuidade, snapshots e exportações próprias |
| Diário consolidado | Semântica do original não confirmada; não criar consolidação entre clientes por inferência |
| Centro de custo | Não há dimensão estruturada implementada no novo contrato; grupo de partidas não deve ser tratado como centro de custo |

Arquivos compartilhados que exigem coordenação: `src/persistence.py` (migração 11 e mixin cadastral), `src/local_app.py` e `src/server/app.py` (rotas/permissões), `src/work_api.py` (leitura de busca), `src/source_evidence.py`, `src/portal/app.js`, templates Vue e seus renders gerados. `src/work_store.py`, `src/work_books.py`, `src/work_domain.py`, `src/accounting_store.py` e `src/finance.py` não foram alterados. Nos testes contábeis/financeiros históricos, somente a versão esperada do esquema foi atualizada para 11. Outra migração deve partir dessa versão para evitar colisão de numeração.

## Windows, Docker e distribuição

Windows passa a iniciar recolhido no tray; `--show-window` abre a administração e `--background` permanece aceito. Se a área de notificação estiver indisponível, a janela é minimizada. O backend continua no processo/thread do aplicativo: não foi introduzida exigência de instalar serviço Windows. Fechar/ESC e Sair mantêm os comportamentos existentes.

Docker, GHCR, dependências e workflows não foram alterados. A API e os dados novos usam as dependências existentes. Builds nativos Windows x86/x64, smoke do executável final e imagem publicada precisam de validação na distribuição correspondente. Não houve publicação/CI remota nem implantação nesta tarefa.

## Validação executada

- Baseline atualizada: `python scripts/build.py check` passou antes das alterações, com 245 testes da aplicação, 18 de distribuição e 27 de CI.
- Incremento: **255 testes da aplicação, 18 de distribuição e 27 de auxiliares de CI aprovados**; um teste DPAPI não se aplica ao Linux.
- Também passaram templates Vue pré-compilados, sintaxe/compilação Python e JavaScript, matemática decimal, ícones e smoke autenticado com banco externo/reinício.
- Testes novos cobrem cadastro persistente, separação escritório/cliente, concorrência, validação, histórico alterado, migração 10→11 preservando originais, permissões HTTP, busca sem competência e triagem PE sintética.
- `qa/company_profiles_browser.py` passou: cinco seções, isolamento entre clientes, empresa usuária, recarga e busca sem competência, sem erros JavaScript ou transbordamento no mobile. Capturas sintéticas da tela de clientes e da recepção mobile foram inspecionadas visualmente; não são prints do sistema de referência.
- `qa/portal_browser.py`, `qa/fiscal_browser.py` e `qa/integrated_flow.py` passaram; o fluxo integrado foi validado nas modalidades local e portal, incluindo recepção, escrituração, liquidação, livros/download e encerramento.
- `git diff --check` passou. Nenhum workflow foi alterado; actionlint não estava disponível no ambiente. Não houve teste nativo Windows, build de imagem, CI remota ou homologação fiscal/Prosoft nesta execução.

## Pendências concretas

1. Restabelecer a transferência autorizada dos anexos; então conferir bytes/hashes, inspecionar pixels e aplicar análise estática por tecnologia identificada.
2. Confirmar campos e operações do sistema de referência, incluindo modelos de livros e apuração; desenvolver regras com vigência, fontes e aceite fiscal explícitos.
3. Implementar importadores bancários por perfil e revisão de extração PDF/imagem, com idempotência, associação explícita, baixa e estorno rastreáveis.
4. Coordenar a migração 11 e os arquivos compartilhados com a frente contábil, sem duplicar seu desenvolvimento.
5. Validar o início no tray nos executáveis Windows x86/x64 e a distribuição Docker antes de publicar qualquer artefato. Publicação/PR/merge/implantação continuam sem execução nesta tarefa.
