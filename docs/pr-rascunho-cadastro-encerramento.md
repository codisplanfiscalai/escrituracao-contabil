# PR fiscal em rascunho — publicado

PR: [#8](https://github.com/codisplanfiscalai/escrituracao-contabil/pull/8). Destino: `develop`. Origem: `feat/cadastro-clientes-busca-fontes`. Publicação inicial no SHA `7bbc57bc29bd623ade57a19ab8873453f4d9e1e7`.

Título sugerido: `feat: parametrizar tributação e apuração por empresa com cadastros e bloqueios`

## Descrição proposta

A parametrização fiscal precisava separar empresas, preservar versões e permitir cálculo/apuração sem presumir enquadramentos legais. O incremento acrescenta regras percentuais explícitas para ICMS/ISS/PIS/COFINS, tabelas de CFOP/NCM/receita/serviço com origem e vigência, modelos copiados em rascunho e nova validação no destino. Nenhuma alíquota ou tabela normativa é pré-carregada.

O cálculo Decimal registra base, taxa, arredondamento, regra/tabelas e memória em nova versão da operação, antes da conferência e escrituração. A apuração soma fatos escriturados pelos efeitos declarados, preserva valores manuais e exige revisão. Ambiguidades, dados alterados e ajustes tributários sem vínculo bloqueiam a validação. Não gera guia, vencimento, crédito legal presumido ou obrigação acessória; CBS/IBS permanecem fora do cálculo.

A branch também separa empresa usuária e clientes, adiciona cinco seções cadastrais versionadas, busca fontes sem competência e controla fechamento fiscal/contábil independentemente por empresa e mês. Receber arquivos permanece permitido; efetivar movimentos respeita os bloqueios. As migrações aditivas 10→11→12→13 preservam originais, cadastros, fechamentos e movimentos. Windows inicia no tray, com `--show-window` para abrir a administração. O produto permanece integrado, sem EXE por tela/relatório.

Validação local: `python scripts/build.py check` aprovado — **276 testes da aplicação, 18 de distribuição e 30 das ferramentas/auxiliares de CI**, com uma omissão DPAPI por exigir Windows. Navegador tributário, fluxo integrado local/portal e navegação dos 19 recursos aprovados, incluindo mobile. Cenários cadastral, fiscal e de encerramento foram validados durante os incrementos anteriores. Sem dados reais/anexos no Git.

Antes do merge: reconciliar esquema 13, payload `tax_calculation` e guardas compartilhadas com a frente contábil; executar CI Windows x86/x64 e smoke dos executáveis finais. Ainda exigem parametrização/homologação: tabelas e modelos do responsável, tratamento legal, cálculo por item misto, regimes especiais e integração Prosoft. A transferência dos 13 executáveis e 35 prints falhou; nenhuma tecnologia/tela original foi confirmada. A CI remota está em execução no SHA do PR; não houve release ou implantação.

## Prontidão

Base `develop` `22ebdb14d812980dac532cd7c0403c2f811f559e`, reconferida ao concluir a validação. Alterações publicadas em branch própria e PR em rascunho. Merge depende da integração contábil e das validações de distribuição/homologação aplicáveis.

A publicação da branch e do PR foi executada. Não houve merge, release, mudança de visibilidade ou implantação. A política de branches passou na execução inicial; CI e Build verification devem ser acompanhados no SHA atual do PR. `actionlint 1.7.12` passou localmente, e a CI foi ampliada com os novos cenários de cadastro, encerramento e tributação.
