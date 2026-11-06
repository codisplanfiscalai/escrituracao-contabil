# Frente contábil — levantamento aberto e incremento de relatórios

Estado de integração mais recente: `frente-contabil-integracao-esquema14.md` registra a combinação isolada com o HEAD `db62bc86adf66d72e18d76a27aed21ac844dcdd1` do PR #11. Os registros de esquemas 10/13 a seguir são históricos; os anexos continuam sem bytes/pixels acessíveis.

Atualização de integração: os relatórios foram combinados com o HEAD `64378f695919c3816840b9eb29c669c762fc6ca1` do PR fiscal #8 em uma árvore isolada, usando o esquema **13** e o fechamento por módulo implementados naquela frente. Consulte `frente-contabil-integracao-esquema13.md` para conflitos resolvidos e validação conjunta. Os registros abaixo sobre esquema 10, migração fiscal 11 e fechamento ainda não implementado descrevem o incremento contábil inicial; não são o estado da combinação atual.

Registro de 06/11/2026. Os envios e requisitos do usuário continuam em andamento. Este documento não encerra o levantamento nem declara o módulo contábil completo.

## Separação de trabalho e base

Frente contábil autorizada separadamente da fiscal, com análise dos executáveis e prints, documentação dos fatos e construção do módulo. Não foram criados novos agentes. A árvore inicial estava desatualizada; foi inspecionada e permaneceu sem alterações. O trabalho efetivo está em `/workspace/escrituracao-contabil-contabil`, branch `feat/modulo-contabil-integrado`, a partir de `develop` no commit `22ebdb14d812980dac532cd7c0403c2f811f559e`.

A frente fiscal informou commit local `d046d7e214dcf597f64baeed413ba9681407e524`, branch `feat/cadastro-clientes-busca-fontes`, migração 10→11. Esse commit não foi importado para esta árvore. Não há migração contábil neste incremento. Não foram alterados `persistence.py`, `local_app.py`, `server/app.py`, `work_api.py`, `source_evidence.py`, `portal/app.js`, templates ou renders Vue, que pertencem à coordenação fiscal desta rodada.

## Inventário completo recebido diretamente

O recebimento de IDs não comprova disponibilidade dos bytes. Os títulos abaixo são identificações recebidas na tarefa; não constituem leitura independente de barras de título ou prova de equivalência funcional. Os nomes de arquivos das primeiras 11 duplas foram resolvidos por metadados da Library, sem leitura de conteúdo local.

| Referência informada | Executável e Library ID | Print e Library ID | Estado |
|---|---|---|---|
| Plano de contas | `CTB010100.EXE` — `libfile_6b57d9f35c688191946dc91c6e2fd4bd` | `image(20261106-035603).png` — `libfile_cfe6f0a4a6bc8191956f967c41ec2607` | Preparados; transferência falhou |
| Digitação contábil | `CTB020100.EXE` — `libfile_1c30cd247e6c8191964d8a51a7cc9951` | `image(20261106-035646).png` — `libfile_7df16ad95a788191ae4adabc91093f1d` | Preparados; transferência falhou |
| Razão | `CTB020400.EXE` — `libfile_00dbf7fa2e448191ac6761ec068b3fba` | `image(20261106-035821).png` — `libfile_2efac97a4e388191982922577c196ac3` | Preparados; transferência falhou |
| Diário individual | `CTB020600.EXE` — `libfile_596fd8f8b60081918022ff0f5c25cc59` | `image(20261106-035953).png` — `libfile_9bc29a9e8f5481919fe8563a84704326` | Preparados; transferência falhou |
| Diário consolidado | `CTB020800.EXE` — `libfile_ba5aa2fb01348191a2086258856dc886` | `image(20261106-040046).png` — `libfile_06b7085d6f548191b73c5d4fed10344b` | Preparados; transferência falhou |
| Balancete em tela | `CTB021300.EXE` — `libfile_20158943e89481919c0c7af83e0852aa` | `image(20261106-040232).png` — `libfile_54f2ae7cdf788191946926cec3c07538` | Preparados; transferência falhou |
| Verificação em tela II | `CTB021400.EXE` — `libfile_daf7a7f964748191a81bf3868a8e2bda` | `image(20261106-040328).png` — `libfile_8227bb1701f08191b6c8bf4bb66498cc` | Preparados; transferência falhou |
| Balancete por centro de custo | `CTB021500.EXE` — `libfile_6ad4265684388191a4f9f2f06d365df4` | `image(20261106-040528).png` — `libfile_384ca17a3bac8191a1e1178a049e0378` | Preparados; transferência falhou |
| Balancete por centro de custo sintético | `CTB021700.EXE` — `libfile_0db838b2869c8191a8da266ae87c5593` | `image(20261106-040720).png` — `libfile_ef3acb3fa5fc8191936b12dc6e3b7cc3` | Preparados; transferência falhou |
| Balancete de verificação modelo 1 | `CTB030200.EXE` — `libfile_9815881889208191ab457db7eb5c2806` | `image(20261106-040906).png` — `libfile_670d96afe81081919be76b3ed73ce0fd` | Preparados; transferência falhou |
| Razão contábil por centro de custo | `CTB020700.EXE` — `libfile_7108b4fc02248191960548241be84370` | `image(20261106-041031).png` — `libfile_7491caa7b8e481919a35993bd22fa237` | Preparados; sem download após confirmação do bloqueio |
| Conciliação chamada V4 | Nome não verificado — `libfile_6d3ef7e7f46c8191afedadd464dfd6eb` | Nome não verificado — `libfile_828f622ec35081919a4a8c79153e59d4` | IDs recebidos; acesso pendente |
| Outra conciliação contábil | Nome não verificado — `libfile_cdba67ddc64c8191b2cf209e386f3d24` | Nome não verificado — `libfile_b9b4dd3063a0819184e73f8b35246a35` | IDs recebidos; acesso pendente |

**Total: 13 executáveis e 13 prints. Bytes efetivamente legíveis: zero. Executáveis analisados estaticamente: zero. Prints inspecionados por pixels: zero. Código recuperado: nenhum.**

O print `libfile_c9ffedcc5ea88191b75bcdfec6dd0dce` foi explicitamente corrigido pelo usuário como registro do encaminhamento equivocado à frente fiscal. Não integra as 13 referências funcionais acima e não fundamenta requisito de associação fiscal-contábil. O encaminhamento dos IDs corretos não resolveu o acesso aos bytes.

## Bloqueio exato e tentativas realizadas

Foi lida a skill atual da Library e sua referência de materialização. Os dois helpers atuais foram obtidos da mesma skill e mantidos juntos em diretório privado temporário, sem modificar seu código. Como os IDs foram fornecidos diretamente, usou-se `prepare_materialize`, e não a rota de resultados de list/search.

1. Preparação inicial de 20 referências, com destino `/workspace/contabil-reference`: autorizada pela Library; nenhum `workspace_path` retornado. Todos os 20 usos do helper de transferência terminaram com `library file transfer failed: download failed`.
2. Uma tentativa limitada para o print do plano, com destino local explícito `/workspace`: novamente não houve caminho local; o helper também falhou. Não foi instalado arquivo de anexo em nenhum desses destinos.
3. Diagnóstico sem transferência de arquivo confirmou `URLError <urlopen error Tunnel connection failed: 403 Forbidden>` para o domínio de entrega. O executor tem política restrita, e esse destino não está na lista de acesso. Não houve contorno do proxy ou alteração da política.
4. As duas referências do Razão por centro de custo foram preparadas, também sem caminho local; não foram baixadas depois de identificado o mesmo bloqueio. As quatro referências das conciliações foram registradas sem repetir transferências bloqueadas.
5. A leitura alternativa de imagens devolveu ponteiros de imagem, descrição e OCR em estrutura de dados, sem pixels acessíveis. Esses textos não foram tratados como inspeção visual. Não foram estabelecidos campos, marca, versão, tecnologia ou regras com base nesse retorno.

É bloqueio de transferência/rede, sem resultado incerto de execução e sem rejeição de revisão automática de uma ação de publicação. Nenhum binário desconhecido foi executado. Nenhum hash de conteúdo, cabeçalho PE/CLR, importação de DLL, recurso, formulário ou trecho recuperável pôde ser conferido. Não se pede reenvio: os IDs estão registrados, e o próximo passo de acesso depende da disponibilização suportada dos bytes no executor.

## Informações e decisões do usuário

- O produto terá aplicação integrada e dinâmica, com menus, módulos e relatórios filtráveis. Não reproduzir um executável por tela, relatório ou operação. Preservar modularidade interna, Windows gráfico com tray e execução servidor em Docker.
- Os binários são referência de recursos e campos, não autorização para copiar arquitetura, visual ou ativos. Recuperação integral de código-fonte não é prometida.
- Há confirmação explícita do usuário de que a conciliação chamada V4 aceita **TXT, CSV, OFX, QIF e OFC**. Isso é informação fornecida por ele, ainda sem inspeção independente dos arquivos ou validação de leiautes.
- Foram mencionados “conta de acesso” e “terceiro”; significados, vínculos e leiautes permanecem abertos. Não equiparar automaticamente conta de acesso a conta bancária, conta contábil ou credencial.
- O usuário considera possível que a outra conciliação tenha modos manual e automático, mas desconhece os critérios. Isso permanece hipótese, não funcionalidade comprovada. Não classificar as duas conciliações como versões equivalentes nem chamar uma de anterior apenas pelo título.
- O motor de conciliação será próprio e integrado. Critérios de correspondência, tolerâncias, sinais, datas, identificadores e tratamento de repetição dependem de especificação; não foram inventados neste incremento.
- Encerramento e bloqueio deverão ser independentes por empresa, período e módulo fiscal/contábil. A recepção de arquivos permanece possível e não pode contornar bloqueios de efetivação. O Analisador Fiscal IOB foi citado como referência futura, sem anexos ou escopo detalhado.

## Fatos identificados no código do projeto

O repositório atual usa Python, SQLite, serviços compartilhados entre desktop e servidor, FastAPI no portal e Vue 3.5.13 com templates pré-compilados. São fatos do projeto próprio, não identificação da tecnologia dos executáveis anexos.

`work_store.py`/`work_domain.py` já controlam versões de operações, conferência, escrituração e efeitos integrados. `work_books.py` reúne movimentos escriturados, fontes legadas fechadas, abertura declarada, continuidade de competências e histórico financeiro. `accounting_api.py` é o ponto de rotas contábeis já reutilizado por `local_app.py` e pelo portal autenticado. Não foi criado um segundo livro ou cópia de movimentos.

Não havia `.agents/skills` no repositório nem skill local disponível no diretório `.agents` da raiz exposta nesta sessão. Foram respeitadas as instruções do `AGENTS.md` atual. A versão `0.3.0` não foi alterada.

## Implementação deste incremento

Novo `src/work_reports.py`: consultas **Diário, Razão e Balancete**, em um único serviço, sobre o livro canônico existente. Filtros: empresa, competência/ciclo, versão do plano, intervalo de datas dentro da competência, conta ou grupo de contas, nível analítico/sintético do balancete e inclusão de contas sem movimento.

- As relações hierárquicas seguem `parent_code`; códigos não são interpretados por prefixo. Sintéticas acumulam descendentes, e totais gerais são calculados somente nas analíticas, sem dupla contagem de níveis sobrepostos.
- O saldo inicial do recorte soma a abertura do livro e os movimentos anteriores à data inicial. Movimentos após a data final ficam fora. A abertura declarada e sua competência são informadas separadamente; a ausência de declaração não é tratada como abertura externa zero confirmada.
- Razão conserva partidas distintas, sequência de origem, conta, operação, revisão, documento, hash de origem e saldo corrente. Saldos usam débitos menos créditos, com indicador D/C explícito. A natureza credora não inverte silenciosamente o sinal.
- Valores são textos decimais convertidos para centavos inteiros exatos para o recorte. Não se usa float para dinheiro. O serviço reaproveita a validação histórica do livro canônico e confere seu hash antes de filtrar.
- Cada consulta tem o hash do livro e seu próprio hash, além dos filtros. O estado não é gravado no banco; um savepoint mantém leitura consistente sem confirmar ou desfazer a transação do chamador.
- A empresa, ciclo e plano são validados no servidor. Planos com os mesmos códigos não se misturam. Filtros desconhecidos são rejeitados, incluindo `cost_center`, em vez de produzir resultados aparentemente filtrados sem suporte.

Rota somente de leitura: `GET /api/accounting-report`. Exemplo com identificadores fictícios: `company_id=1&cycle_id=1&plan_id=1&report=razao&start_date=2026-09-10&end_date=2026-09-20&account_code=1&level=analitico&include_zero=false`. Parâmetros obrigatórios: empresa, ciclo e plano. Datas ausentes abrangem o mês selecionado. `include_zero` aceita somente `true` ou `false`.

O registro da rota está restrito a `src/accounting_api.py`; os roteadores local e corporativo já a importam. As permissões existentes de leitura e escopo por empresa continuam aplicáveis. POST não é aceito. O cliente externo não ganhou acesso a essa rota interna.

Interface em `src/web/workbench.js`: componente independente em “Livros e relatórios”, usando o painel existente por Vue Teleport, sem mudar templates/renders da frente fiscal ou acrescentar ativos ao empacotamento. Funciona no ambiente local e no iframe do portal. Alterar filtros invalida o resultado; trocar empresa/ciclo desmonta o recorte anterior; atualizar o hash do livro invalida a consulta. O download operacional existente continua sendo do livro completo e é identificado assim na interface.

Não foram implementados a partir das referências ainda inacessíveis: modelos Prosoft específicos, agrupamento do Diário consolidado, centros de custo/rateios, critérios das conciliações, importadores bancários ou automatismo de associação. Não são livros legais assinados, arquivos homologados Prosoft/SPED ou apuração de tributos.

## Contrato de integração com fiscal e financeiro

Fiscal e financeiro continuam produzindo efeitos pela operação integrada existente. Relatórios apenas consultam `work_books(company_id, cycle_id)`; não chamam APIs de importação, baixa ou escrituração e não recalculam tributos. O serviço expõe a versão do plano e o hash canônico para rastreabilidade. CBS/IBS seguem fora do cálculo.

A frente fiscal pode integrar este commit sem disputar a migração 11: os únicos arquivos preexistentes alterados são `src/accounting_api.py` e `src/web/workbench.js`, ausentes da lista de alterações fiscais informada. Os demais são novos arquivos próprios de serviço, testes, QA e documentação. Verificar a lista final de diferenças antes de reunir branches.

Para futuro centro de custo, os IDs devem pertencer à empresa e estar vinculados às partidas/rateios versionados; somas devem reconciliar ao valor da partida. Um filtro por centro não pode ser simulado por texto no histórico. A definição concreta depende dos materiais e requisitos, ainda abertos.

## Novo encerramento independente por módulo — contrato pendente

O encerramento atual da competência é geral. **Este incremento ainda não implementa bloqueios independentes fiscal/contábil.** A migração da frente fiscal já usa 11; a persistência deste novo requisito deverá ser integrada depois dela e receber versão coordenada, sem duas migrações concorrentes com o mesmo número.

Proposta para discussão/implementação conjunta:

1. Chave persistente `(company_id, competence, module)`, com `module` em `fiscal/contabil`, estado `aberto/encerrado`, versão para concorrência, ator, motivo e hash do checklist/snapshot conferido. A competência econômica deve ser a chave de bloqueio; criar outro ciclo, mudar referência dos parâmetros ou trocar plano não pode abrir brecha.
2. Fechar/reabrir exige permissão de revisão da empresa, motivo e comparação de versão/hash; eventos preservados na auditoria. Nunca inferir que apuração foi realizada quando o produto não a executa. Deve haver evidência explícita do atendimento ou tratamento aprovado de cada etapa exigida pelo usuário.
3. Verificar os módulos realmente afetados no servidor, sem confiar em flags do navegador. Operações com efeitos fiscais e contábeis exigem ambos abertos, em uma única transação. Ajuste exclusivamente contábil depende do contábil. Pagamento/recebimento com partidas também depende do contábil, mesmo quando iniciado pelo financeiro.
4. Guardar os pontos `save_work_operation`, revisão, `post_work_operation`, estorno, retomada de legado e aplicação de alteração de competência. Atualizar apenas o botão de escrituração não é suficiente; chamada direta de API e rascunho antigo não podem contornar a guarda.
5. Recepção/original/caixa de entrada continuam permitidos sem plano ou período aberto. Normalização e organização devem distinguir metadados/evidência de novos efeitos escriturados. Fontes recebidas depois do fechamento ficam pendentes para decisão, sem alterar movimentos ou snapshots fechados.
6. Conferência de bloqueio e gravação/encerramento usam a mesma transação de escrita. Corrida entre fechar período e escriturar precisa resultar em uma única ordem válida; se o fechamento vencer, a escrituração posterior falha sem movimentos, títulos ou eventos parciais.
7. Não mapear automaticamente o encerramento geral legado para dois novos encerramentos sem regra de migração explícita. Preservar estados e histórico existentes, e definir a exibição enquanto não houver confirmação por módulo.

Matriz mínima de aceite a executar quando o recurso for implementado: fiscal fechado/contábil aberto e inverso; ambos fechados; empresa e mês diferentes; operação mista atômica; financeiro com partidas; recepção posterior; tentativa por API/rascunho antigo; criação de novo ciclo para o mesmo mês; estorno destinado a período fechado; reabertura com motivo e concorrência; fechamento contra postagem simultânea; rollback; migração preservando originais, movimentos e auditoria. Estes são testes planejados, não resultados executados deste recurso.

## Verificação e limites

O registro final de execução e os arquivos modificados constam em `docs/frente-contabil-validacao.md`. Todos os testes e prints de QA usam dados inteiramente sintéticos. Nenhum anexo de referência, documento real, banco privado, credencial ou executável foi incorporado ao Git. Não houve push, publicação, PR, merge ou implantação.

O trabalho seguinte é liberar o acesso suportado aos bytes, inspecionar os pixels, levantar estrutura estática dos binários sem executá-los, comparar os modelos por evidência e detalhar conciliação/centros de custo. O usuário continua enviando materiais; manter este inventário aberto e preservar a distinção entre confirmação dele, hipótese, leitura de código próprio e inspeção independente dos anexos.
