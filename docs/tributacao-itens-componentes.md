# Tributação por item e componentes declarados

Este documento registra o incremento v2 do PR #10. A evolução posterior de FCP e grupos por dentro, com limites próprios e memória v3, está em [FCP e cálculo por dentro](fcp-calculo-por-dentro.md). As exclusões desses dois perfis abaixo descrevem somente o escopo original v2.

## Escopo e dependência

Incremento fiscal separado, dependente do PR #8 e do esquema 13. A branch de integração anterior não foi alterada. A base de código deste incremento é `64378f695919c3816840b9eb29c669c762fc6ca1`; a develop conferida ao iniciar era `22ebdb14d812980dac532cd7c0403c2f811f559e`. O PR deste incremento destina-se a develop e fica em rascunho enquanto sua dependência e a integração contábil forem reconciliadas.

A aplicação permanece única. O incremento acrescenta perfis aritméticos configuráveis; não carrega tabelas oficiais, alíquotas, enquadramentos ou direitos a crédito. CBS/IBS continuam fora do cálculo. As denominações ST, DIFAL e retenção identificam perfis limitados que precisam de validação para o caso concreto, não cobertura legal universal.

## Itens, tratamentos e fonte

`payload.tax_items` contém de 1 a 200 itens, cada qual com identificador único, descrição, CFOP/NCM/serviço declarados, tratamento de escopo, origem/conferência, localizador na fonte, componentes esperados e valores. O total líquido atribuído aos itens deve somar exatamente o total do documento. Frete, descontos, acréscimos e outros rateios não são calculados automaticamente.

Componentes são declarados explicitamente: ICMS, ISS, PIS, COFINS, ICMS_ST, ICMS_DIFAL e RETENCAO:IDENTIFICADOR. Uma retenção exige identificar o tributo retido na regra, sem catálogo normativo presumido. Itens sem componentes exigem motivo e não podem contrariar regras aprovadas aplicáveis. As regras encontradas devem corresponder exatamente aos componentes declarados; falta de cobertura e ambiguidade bloqueiam o cálculo.

Natureza, modelo e data de escrituração vêm do documento. CFOP, NCM, serviço e tratamento vêm do item. Vigências e catálogos continuam verificados na empresa. Duas regras para o mesmo componente de um item são recusadas. Regras documentais aplicáveis também impedem o modo por item: a adaptação deve ser explícita, sem somar duas vezes o mesmo fato.

Quando a observação selecionada contém produtos estruturados, todos precisam corresponder a um localizador distinto e o NCM declarado deve conferir com o observado. A interface pode propor esses vínculos, descrições e classificações. A proposta deixa valores e tratamentos para conferência. O extrator atual não fornece bases e totais monetários por produto nesse contrato; não se afirma extração automática desses valores. Fonte alterada ou excluída bloqueia o cálculo.

## Perfis aritméticos disponíveis

Todas as taxas, reduções e margens são informadas como texto decimal. A redução precisa ser explicitada, inclusive zero. O responsável escolhe o arredondamento: meio para cima ou truncamento. O perfil exige declarar base em centavos antes da taxa; o tributo é arredondado em cada item antes de somar. A memória preserva os valores anteriores aos arredondamentos.

| Perfil | Operação suportada | Parâmetros adicionais obrigatórios |
| --- | --- | --- |
| Percentual por item | Base reduzida arredondada × taxa ÷ 100 | Redução e arredondamento da base |
| Retenção declarada | Base reduzida arredondada × taxa retida ÷ 100 | Identificador do tributo retido; redução e arredondamento |
| ST com margem declarada | Arredondar(base × (1 + margem/100) × (1 − redução/100)) × taxa/100 − dedução declarada | Margem, dedução própria em cada item, política para resultado negativo |
| DIFAL por diferença declarada | Base reduzida arredondada × (taxa de destino − taxa de origem) ÷ 100 | Taxa de origem, política para resultado negativo |

Taxas e redução: 0 a 100, até seis casas. Margem do perfil ST: 0 a 1000, até seis casas. A dedução ST é um valor monetário declarado por item, inclusive zero; não é calculada a partir de outro tributo. Não há dependência automática entre regras.

Resultado negativo bloqueia o cálculo ou é zerado somente quando essa política estiver explicitamente aprovada. A memória sempre registra o resultado anterior à política. Não há geração de crédito por resultado negativo.

Bases distintas de origem/destino, cálculo por dentro, FCP, partilha, PMPF, pautas, regimes especiais e exceções não são inferidos ou cobertos por esses perfis. Não existe avaliação de código ou fórmulas arbitrárias.

## Memória, aplicação e apuração

O perfil `tributacao-itens-v2` registra itens de entrada, fonte selecionada, regras/catálogos, base original, base expandida, base reduzida, taxa efetiva, valor bruto, dedução, resultado antes da política negativa e valor final. Guarda também os critérios de arredondamento e conciliação.

A aplicação idempotente cria uma nova versão de rascunho, como no fluxo anterior. ICMS/ISS/PIS/COFINS comuns são totalizados nos campos fiscais existentes. `payload.tax_components` mantém os componentes calculados, incluindo ST/DIFAL/retenções. Componentes especiais não são misturados ao ICMS próprio e não alteram partidas ou títulos automaticamente. Os totais comuns do cabeçalho somam valores positivos por item; quando os efeitos diferem, a contabilização precisa consultar as linhas/efeitos da memória, não deduzir o saldo tributário do cabeçalho. A interface apresenta prévia por item/componente e identifica separadamente as retenções nos totais da apuração.

Conferir e escriturar exige memória válida. Alterar itens, componentes, fonte ou parâmetros aplicáveis exige recálculo. Itens/componentes enviados sem memória não podem ser conferidos ou escriturados. A exceção manual motivada retira o modo por item da nova versão e preserva a memória anterior no histórico.

A apuração lê as linhas calculadas por item e preserva identificador, fonte, fórmula, parâmetros e etapas. Retenções com identificadores diferentes permanecem separadas, mesmo com o mesmo código de receita. Efeito débito/crédito/informativo continua declarado pela regra; o nome do perfil não determina o efeito.

Estorno contábil não reverte tributos automaticamente. Ajustes fiscais vinculados precisam declarar os componentes do original, incluindo componentes especiais. O sistema verifica cobertura explícita, sem escolher o valor, a natureza legal ou a contrapartida tributária do ajuste.

O fechamento fiscal e os controles existentes continuam exigindo a apuração atual validada. A recepção de arquivos permanece independente da abertura de competência. O cálculo não cria guia, vencimento, baixa bancária, crédito legal ou obrigação acessória.

## Contrato com a frente contábil

Não houve alteração em `src/persistence.py`, `src/work_store.py`, `src/accounting_store.py`, `src/work_domain.py`, `src/finance.py` ou na numeração do esquema. `src/module_closure.py` recebeu uma ampliação de identificação: payloads com itens, componentes, memória ou vínculo de ajuste tributário são fiscais mesmo sem campos de imposto no cabeçalho, impedindo contorno por uma natureza de ajuste. O armazenamento usa os JSONs versionados existentes, com perfil de memória próprio. Registros documentais v1 continuam legíveis e mantêm seus cálculos.

Novos dados exigem este código: um executável anterior não deve ser usado para operar regras com `calculation` ou memórias de itens v2. Reutilizar esquema SQL 13 não implica que versões antigas compreendam os novos perfis JSON. A combinação com a frente contábil precisa ser testada antes de compartilhar dados operacionais. O PR contábil #9 foi identificado sobre a mesma base do #8; entre os arquivos deste incremento, ele também altera `src/web/workbench.js`, ponto de reconciliação do frontend.

Arquivos de produção alterados: `src/tax_items.py` (novo), `src/tax_engine.py`, `src/tax_assessment.py`, `src/module_closure.py`, `src/web/workbench.js`, template e render gerado do workbench. Não foram modificados métodos de contabilização ou liquidação. A contabilidade pode consumir a memória/item e os componentes somente por políticas aprovadas; este incremento não os converte automaticamente em lançamentos.

## Validação e limites de entrega

Fixtures e documentos de teste são inteiramente sintéticos. Os testes verificam tratamentos mistos, reduções, arredondamento por item, perfis ST/DIFAL/retenção, política negativa, cobertura/ambiguidade, origem, NCM, componentes separados, persistência, idempotência, alterações depois do cálculo, apuração, ajustes vinculados e cópia entre empresas.

O cenário de navegador percorre a criação/aprovação do perfil ST, proposta dos vínculos dos produtos, dois itens com taxas diferentes, ST/DIFAL/retenção, conferência/escrituração e exportação da memória da apuração. Verifica layout móvel e ausência de erros JavaScript. Também permanece a regressão do modo documental anterior.

Resultados de execução e o SHA publicado são registrados na descrição do PR e na conversa do projeto. Passar testes de software não comprova homologação fiscal. Ainda são necessárias fontes normativas e parâmetros aprovados para cada empresa/jurisdição, validação com casos reais autorizados, evolução dos perfis não cobertos e validação combinada com a frente contábil.

Os anexos legados continuam sem bytes/pixels acessíveis; este incremento não foi deduzido de executáveis ou telas não inspecionados. Nenhum binário desconhecido foi executado e nenhum dado real foi incluído no Git. Não houve merge, release ou implantação por este incremento.
