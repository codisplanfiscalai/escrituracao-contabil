# FCP e cálculo por dentro com parâmetros declarados

Este documento registra o incremento do PR #13 no esquema 14. A evolução posterior para ajustes e saldos entre competências, com migração aditiva para esquema 15, está em [Ajustes e saldos da apuração](ajustes-saldos-apuracao.md).

## Escopo e dependências

Incremento da branch `feat/fcp-calculo-por-dentro`, baseado no commit `db62bc86adf66d72e18d76a27aed21ac844dcdd1` do PR #11. Dependências: este incremento → #11 → #10 → #8, todos destinados a develop. A develop conferida permanece em `22ebdb14d812980dac532cd7c0403c2f811f559e`. Não há merge, release ou implantação nesta entrega.

A aplicação integrada recebe dois perfis aritméticos por item: FCP separado por modalidade declarada e recomposição de base por dentro. Nenhum perfil determina incidência, enquadramento, alíquota, direito a crédito ou obrigação legal. Não são carregados dados oficiais ou parâmetros legais. CBS/IBS permanecem fora do cálculo.

## FCP por modalidade

O componente é identificado como `FCP:IDENTIFICADOR`, com identificador explícito de até 30 caracteres, iniciado por letra maiúscula e seguido de letras maiúsculas, números ou sublinhado. O identificador não corresponde automaticamente a modalidade legal, guia ou jurisdição.

A regra exige método `fcp`, identificador da modalidade, formação da base (`declarada` ou `por_dentro`), taxa, redução inclusive zero, arredondamento, efeito (`debito`, `credito` ou `informativo`), vigência e referência de validação. Com base declarada, o campo escolhido precisa existir no item; `fcp_base` é um novo campo disponível. Não existe preenchimento automático de base a partir do total.

Modalidades diferentes permanecem separadas na memória e na apuração. FCP é armazenado em `payload.tax_components`; não é somado ao ICMS próprio do cabeçalho. Aplicar o cálculo não modifica partidas contábeis, títulos ou valores financeiros.

## Grupo por dentro

ICMS, ISS, PIS e COFINS podem usar o método `por_dentro`. FCP participa por meio de `fcp` com `base_mode=por_dentro`. Este perfil exige:

- Campo `net_base` informado em cada item, separado do total líquido atribuído ao documento.
- Declaração `input_basis=liquido_sem_componentes_do_grupo`: o valor informado exclui os componentes listados no denominador.
- Lista de 1 a 10 componentes, identificadores e taxas. O próprio componente deve constar com taxa igual à da regra.
- Regra aprovada e aplicável na mesma empresa e no mesmo item para cada componente listado. Todas devem declarar grupo, base, redução, arredondamento e política de diferença compatíveis.
- Política explícita `bloquear` ou `preservar_sem_rateio` para diferenças de arredondamento.

Taxas e redução usam textos decimais, de 0 a 100 e até seis casas. A soma das taxas do grupo deve ser menor que 100. O cálculo usa Decimal com precisão 50:

```text
liquida_reduzida = net_base × (1 − reducao / 100)
denominador = 1 − soma_taxas_do_grupo / 100
bruta_nao_arredondada = liquida_reduzida / denominador
base_bruta = arredondar_centavos(bruta_nao_arredondada)
valor_componente = arredondar_centavos(base_bruta × taxa_componente / 100)
diferenca = base_bruta − liquida_reduzida − soma_valores_componentes
```

Base e tributos são arredondados por item, por meio para cima ou truncamento conforme aprovado. A redução ocorre antes da recomposição. Diferença não nula bloqueia quando a política é `bloquear`. Com `preservar_sem_rateio`, a memória registra a diferença exata sem redistribuir centavos ou alterar outros valores.

Exemplo exclusivamente sintético: base líquida 100,00, redução zero e grupo de 18% + 2% produzem denominador 0,80, base bruta 125,00 e componentes 22,50 + 2,50. Não representa alíquotas ou incidência recomendadas.

O perfil suporta componentes com a mesma base e redução. Não suporta ST, DIFAL ou retenções dentro do denominador, bases legais distintas entre integrantes, partilhas, bases duplas ou fórmulas arbitrárias. A base recomposta não é obrigada a ser igual ao total do item: ela é uma base tributária explicitamente declarada e exige conferência.

## Bloqueios e rastreabilidade

Faltas de base, modalidade, semântica da base, política, integrantes, regra aprovada ou compatibilidade impedem o cálculo. Também bloqueiam denominador nulo/negativo, taxas inválidas, componentes duplicados, parâmetros extras e resultados fora do limite monetário suportado. Não se completam grupos com regras de outra empresa.

Novas regras usam os mecanismos existentes de vigência, catálogo, versionamento e validação por empresa. Copiar modelo gera rascunho independente e remove a referência de validação da origem. Alterações de item, fonte ou regra aplicável invalidam a memória para conferência/escrituração até novo cálculo. Os fechamentos por empresa, período e módulo continuam em vigor.

FCP ou por dentro geram memória `tributacao-itens-v3`, com bases declaradas, regras/catálogos, parâmetros, valores anteriores ao arredondamento, precisão aritmética, denominador, componentes e reconciliação do grupo. A apuração preserva esses grupos com identificadores da operação e do cálculo; a interface mostra a reconciliação e exporta a memória JSON.

Perfis anteriores continuam produzindo memória `tributacao-itens-v2` com o formato anterior; o modo documental v1 permanece disponível. Não há migração SQL: o esquema continua 14. A compatibilidade SQL não torna versões antigas capazes de operar os novos perfis JSON; bancos contendo regras ou memórias v3 exigem uma versão que os compreenda.

## Contrato com a contabilidade e distribuição

Não são modificados o esquema SQL, persistência, domínio das operações, métodos de contabilização ou liquidação. A integração deve consumir linhas da memória com componente, efeito, base, taxa, regra e vigência por política aprovada. Efeito informativo não deve ser convertido automaticamente em débito ou crédito. Não deduzir contrapartidas ou líquido financeiro apenas do nome do componente.

Arquivos de produção: novo `src/tax_grossup.py`; alterações em `src/tax_items.py`, `src/tax_engine.py`, `src/tax_assessment.py`, `src/web/workbench.js`, template e render gerado. O frontend é o ponto comum com a frente contábil. A integração isolada usa o PR #12 (`bd45a656497cd7537b2931311386c31eb7a11742`), compatível com esquema 14. Resultados reais da combinação são registrados no PR e na conversa.

A arquitetura continua única, com Windows gráfico/tray e execução servidor em Docker. Não é criado executável por perfil ou relatório, serviço obrigatório, dependência externa ou processo separado.

## Validação e limites

Testes sintéticos cobrem FCP separado, grupos completos/incompletos, divisão periódica, redução, arredondamento, diferença sem rateio, entradas inválidas, ausência de base, isolamento entre empresas, modelos independentes, memória obsoleta, idempotência, apuração e encerramento. O navegador percorre autoria do grupo, aprovação, cálculo, conferência, escrituração, exportação JSON, layout móvel e troca de empresa nos modos local e portal. A suíte geral e as regressões documentais, por item, de cadastros, navegação e fluxo integrado são executadas antes da publicação.

Resultados, SHA e CI são informados na descrição do PR e na conversa do projeto. Testes de software não comprovam homologação fiscal. Permanecem necessárias fontes normativas verificadas, parâmetros aprovados por empresa/jurisdição, validação dos efeitos e conferência de casos reais autorizados. Este perfil não cobre todos os métodos legais de cálculo por dentro, nem produz guias ou obrigações acessórias.

Os anexos de referência continuam bloqueados na transferência: não há bytes ou pixels locais acessíveis. Nenhum executável desconhecido foi executado e nenhuma conclusão de engenharia reversa ou de inspeção de telas é atribuída a este incremento. Nenhum documento real é incluído em Git ou CI.
