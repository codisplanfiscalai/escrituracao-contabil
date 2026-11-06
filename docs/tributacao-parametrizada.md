# Tributação e apuração parametrizadas por empresa

## Resultado e fronteira do motor

Implementado um motor percentual configurável para ICMS, ISS, PIS e COFINS, com regras versionadas por empresa, modelos copiáveis, cadastros de CFOP/NCM/receita/serviço, memória de cálculo e apuração dos fatos escriturados. Não há alíquotas legais, enquadramentos, tabelas normativas ou direito a crédito presumidos. CBS/IBS continuam fora do cálculo, conforme o escopo do repositório.

A fórmula disponível é `base declarada × taxa percentual informada ÷ 100`, com Decimal e arredondamento explicitamente escolhido: meio para cima ou truncamento em centavos. Não existe avaliação de código ou fórmula arbitrária recebida do navegador. O perfil suporta bases não negativas com até duas casas e taxas de 0 a 100, com até seis casas decimais. Outras fórmulas exigem perfis próprios e testes antes de uso.

## Cadastros por empresa

CFOP, NCM, códigos de receita e códigos de serviço possuem tipo, código, descrição, vigência, origem/versão da tabela, estado, versão local, responsável e motivo. As versões anteriores permanecem preservadas. Os códigos não são tratados como prova de validade legal nem determinam, isoladamente, incidência, base, alíquota, crédito ou efeito na apuração.

CFOP e NCM têm validação estrutural de quatro e oito dígitos, respectivamente. Serviço e receita permitem identificadores textuais limitados, porque sua jurisdição/leiaute não foi presumida. A referência de origem deve identificar a tabela e versão efetivamente conferidas, inclusive ente/município quando aplicável. Não foi implementada carga automática de tabelas oficiais, importação em lote ou sincronização externa.

Uma regra que referencia código exige cadastro ativo e vigente na própria empresa. Na aplicação, as versões das tabelas efetivamente usadas integram a memória de cálculo. Se a tabela ou a regra aplicável mudar, a operação ainda não escriturada precisa ser recalculada. Alterar tabelas ou ativar regras que alcancem competência fiscal encerrada é recusado até reabertura motivada.

Como referência de uma futura carga controlada, a Receita Federal descreve o [Sistema Classif](https://www.gov.br/receitafederal/pt-br/assuntos/aduana-e-comercio-exterior/classificacao-fiscal-de-mercadorias/classif) com histórico e arquivos da NCM. A consulta não resultou em carga de códigos ou alíquotas neste projeto. Resultados de busca de CFOP com indicação de revogação/ausência de efeitos não foram usados como tabela normativa.

## Regras e modelos

Cada regra tem identificador, nome, tributo, natureza da operação, modelo opcional, escopos opcionais de CFOP/NCM/serviço, código de receita opcional, campo da base, taxa, efeito na apuração, arredondamento, vigência e referência da validação pelo responsável. Efeito é uma escolha explícita: débito, crédito ou informativo. A natureza entrada/saída não concede crédito automaticamente.

Estados: rascunho, aprovada e inativa. A aprovação exige parâmetros completos, códigos disponíveis e referência da validação. Uma nova versão de rascunho não desativa silenciosamente a versão aprovada. A seleção considera a data de escrituração declarada, a vigência e o escopo; a referência dos parâmetros contábeis não desloca essa vigência automaticamente. O responsável precisa validar a data/evento aplicável ao tratamento. Para seleção, a versão aprovada/inativa aplicável mais recente governa cada identificador. Uma versão expirada não faz uma regra antiga reaparecer. Duas regras aplicáveis ao mesmo tributo bloqueiam o cálculo, sem critério de prioridade inventado.

Modelos estruturais vêm sem tributo, alíquota, efeito, vigência ou aprovação preenchidos. Um modelo particular pode ser preservado a partir de uma regra aprovada. Sua cópia para outra empresa gera uma regra em rascunho, com vínculo à origem e referência de validação do destino em branco. Aprovar no destino requer nova validação; códigos precisam existir e estar vigentes no destino. Alterar a cópia não modifica a regra ou o modelo de origem. A API verifica acesso às duas empresas.

## Cálculo e escrituração

Na ficha de uma operação salva, o operador gera a prévia de tributação. O motor seleciona automaticamente as regras aplicáveis e apresenta base, taxa, resultado sem arredondamento, resultado em centavos, efeito, regra e tabelas usadas. A aplicação explícita da prévia cria memória imutável e outra versão de rascunho da operação na mesma transação. Não cria movimentos contábeis ou títulos por esse ato.

O cálculo tem chave de tentativa idempotente. Repetir a tentativa recupera o resultado sem outra aplicação. A interface preserva a tentativa na guia para recuperar uma resposta perdida. Depois do cálculo, ainda é necessário conferir e escriturar a operação. Alteração de dados fiscais, origem ou parâmetros impede a conferência até gerar nova memória. Operações já escrituradas não são recalculadas.

Valores manuais anteriores permanecem disponíveis. Substituir um cálculo automático por valores informados exige motivo explícito e outra versão; a memória anterior permanece no histórico. O XML original não é alterado. O motor não valida assinatura, autorização ou esquema completo dos documentos e não substitui as conferências de origem existentes.

NCM é um escopo declarado para o cálculo documental, não uma classificação automática dos itens. Quando os itens observados não compartilham o NCM da regra, a aplicação sobre o total é recusada. Tributação item a item, mistura de tratamentos, reduções, ST, DIFAL, retenções, exceções e regimes especiais ainda exigem perfis e homologação próprios. O motor atual não declara cobrir esses casos.

## Apuração automática e memória

A prévia da competência lê fatos já escriturados. Valores gerados pelo motor usam sua memória original e efeito parametrizado. Valores informados são preservados sem recálculo e precisam de regra aprovada que declare seu efeito. Valor sem classificação, regra ambígua, documento pendente ou memória inválida impede validar a apuração.

A soma agrupa tributo e código de receita declarado. Registra débitos, créditos, informativos e `saldo_aritmetico = débitos − créditos`. Não gera vencimento, DARF, guia, compensação, transferência de saldo ou obrigação acessória. Saldo negativo não é transportado automaticamente para outra competência.

O operador preserva uma versão da apuração, revisa fatos/regras/bases/efeitos e valida o snapshot atual. Alteração relevante dos fatos ou parâmetros exige nova versão. JSON para conferência inclui linhas, origens, versões, tabelas, hashes e responsável. O hash identifica o snapshot canônico; não é assinatura digital nem certificação fiscal.

Estorno contábil de uma operação tributada não presume reversão dos tributos. A apuração aponta a necessidade de ajuste fiscal explícito vinculado. O ajuste referencia a operação original, exige motivo e valores/efeito definidos por regra. O motor não escolhe a contrapartida tributária legal.

Quando houver regras aprovadas na competência ou versões de apuração parametrizada, o fechamento fiscal exige apuração atual validada. O fechamento global anterior também verifica essa condição, evitando contorno do bloqueio. Sem parametrização automática, mantém-se o fluxo anterior de conferência externa declarada. Contábil e outras empresas/competências permanecem independentes.

## Integração e permissões

O recurso Tributação e apuração faz parte da mesma aplicação e das mesmas guias. Não foi criado executável por tabela, regra ou relatório. O modo local e o portal usam os mesmos serviços.

Leitura exige acesso à empresa. Configuração, modelos, tabelas e validação exigem `workspace.review`; aplicação do cálculo na operação exige `workspace.write`. CSRF e escopo permanecem no servidor. O portal externo de clientes não recebe essas rotas.

As partidas contábeis continuam explícitas. O cálculo tributário não escolhe contas, não desdobra créditos/obrigações e não altera automaticamente a contabilização. A frente contábil pode consumir `fiscal.*_base`, `fiscal.*_amount` e `tax_calculation` do payload preservado, mediante políticas aprovadas. O livro operacional recebe os valores fiscais da operação; a memória completa tem exportação JSON própria. Nenhum desses arquivos é apresentado como importação Prosoft ou SPED homologado.

## Migração e coordenação

Esquema **13**, aditivo sobre o esquema 12: `tax_catalog_versions`, `tax_rule_versions`, `tax_template_versions`, `tax_calculations` e `tax_assessment_versions`. Cadastros, bloqueios de módulos, originais, títulos, movimentos e snapshots anteriores são preservados. Não há atualização retroativa automática de documentos ou impostos.

Novos módulos: `src/tax_catalog.py`, `src/tax_engine.py`, `src/tax_assessment.py` e `src/tax_api.py`. Pontos compartilhados: `src/persistence.py`, `src/local_app.py`, `src/server/app.py`, `src/work_store.py`, `src/module_closure.py`, controlador/template/render do workbench e menu do portal. A frente contábil precisa reconciliar esquema 13, payload tributário e bloqueios antes do merge. Não criar outra migração 13 independente com conteúdo diferente.

## Validação e pendências

Fixtures usam códigos e taxas inteiramente sintéticos. Cobrem precisão/arredondamento, vigência, ambiguidade, cópia por empresa, validação no destino, cadastros, idempotência, dados alterados, apuração, fechamento global/por módulo, exceção manual, mistura de NCM, ajuste vinculado e migração 12→13.

O navegador verifica os quatro cadastros, regra aprovada, cópia independente, cálculo/conferência/escrituração, apuração, memória JSON, fechamento fiscal e layout móvel. Verificação final: `python scripts/build.py check` aprovado com **279 testes da aplicação, 18 de distribuição e 27 dos auxiliares de CI**, com uma omissão DPAPI por exigir Windows. Também passaram templates, sintaxe, matemática decimal, ícones e smoke autenticado. `qa/tax_browser.py`, `qa/integrated_flow.py` (local/portal) e `qa/workspace_navigation.py` passaram, este último com 19 recursos e larguras de 1440 a 320 px. Capturas sintéticas desktop/mobile foram inspecionadas visualmente. `git diff --check` passou.

Para operação real ainda são necessários modelos/tabelas do responsável com origem e vigência verificadas, aprovação dos tratamentos e efeitos, caracterização de casos reais, perfis especiais, validação Windows x86/x64 e homologação fiscal/Prosoft. Os executáveis e prints fornecidos continuam sem leitura de bytes/pixels; não há engenharia reversa concluída. O Analisador Fiscal IOB permanece referência futura, sem integração implementada. Não houve publicação de PR, release ou implantação.
