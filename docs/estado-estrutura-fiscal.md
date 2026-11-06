# Estado da estrutura fiscal e próximos aceites — 06/11/2026

A continuidade após o PR #16 está em [Preparação de documentos e valores por item](preparacao-documentos-itens-xml.md), com esquema 17 e evidência por campo. A revisão abaixo conserva o escopo e a data de sua elaboração.

A continuidade seguinte cobre [eventos de NF-e/NFC-e e conferência](eventos-nfe-conferencia.md), com esquema 18, sem aplicação automática de cancelamento ou correção.

## Evidência e escopo desta revisão

Revisão do código na base `3673c5a1212c29aff0c600e11bfd329f5d96022a` (PR #14), com consulta dos PRs abertos #8 a #15 e da develop remota `22ebdb14d812980dac532cd7c0403c2f811f559e`. Esses PRs estavam em rascunho e não integrados à develop na consulta. O código disponível na branch fiscal não equivale a uma release instalada ou homologada.

A diretriz vigente é uma aplicação integrada com módulos e relatórios configuráveis, clientes segregados da empresa usuária, Windows gráfico/tray e servidor Docker. Relatórios antigos que descrevem somente integração Prosoft ou dizem que não há apuração são registros históricos; não representam o estado atual. A homologação externa e a entrega completa continuam pendentes.

## Incrementos publicados e dependências

| PR | Conteúdo comprovado no código | Dependência |
| --- | --- | --- |
| #8 | Cadastros de clientes/organização, busca sem competência, bloqueios por módulo, regras/modelos/cadastros fiscais e apuração | develop |
| #10 | Tributação por item, tratamentos mistos, reduções e perfis declarados ST/DIFAL/retenção | #8 |
| #11 | Importação canônica CSV/JSON de cadastros, arquivo/hash/origem/jurisdição, ativação revisada e vigência | #10 |
| #13 | FCP separado e grupos por dentro declarados, memória e reconciliação | #11 |
| #14 | Ajustes da apuração, transporte explícito de saldo, reservas, cancelamento e proteção da origem | #13 |
| #15 | Relatórios contábeis e testes conjuntos reconciliados com o esquema 15 | #14 |

Os PRs contábeis #9 e #12 são composições anteriores, preservadas no remoto. Não se deve aplicar todas as versões contábeis cumulativamente ou contar commits fiscais repetidos como incrementos independentes. O #15 é a composição contábil mais recente inspecionada, HEAD `5d78613b858cbd8a4f130bf55292cbc49eb75cf7`.

O novo incremento `feat/tributacao-lote-conferida` parte do #14 e se destina a PR em rascunho para develop. Sua cadeia fiscal é este incremento → #14 → #13 → #11 → #10 → #8. A composição com #15 deve ser testada separadamente e seu esquema reconciliado. Não há autorização implícita de merge, release ou implantação.

## Cobertura atual e lacunas operacionais

| Área | Existe | Falta para ampliar o uso |
| --- | --- | --- |
| Empresas | Organização usuária separada; cliente com dados básicos, fiscais, trabalhistas, contábeis e gerais versionados; escopo por empresa | Conferência cadastral/tributária com responsáveis e casos reais autorizados; campos declarados não determinam regime automaticamente |
| Recepção e busca | Originais/revisões; XML/SPED e arquivos compactados com limites; recepção e pesquisa sem competência aberta | Busca externa/SEFAZ, certificados/contratos e fila de captura externa não implementados |
| Escrituração | Operação salva/versionada, fonte selecionada, ficha fiscal, partidas e cobrança; conferência/escrituração transacionais | Reduzir digitação de valores por item e testar volume/casos operacionais autorizados |
| XML de documentos | Perfil de cabeçalho/cobrança NF-e/NFC-e 4.00 e identidades de produtos | Bases/valores monetários por item ainda não propostos a partir do XML; eventos, CT-e e NFS-e não têm cobertura de importação no fluxo atual |
| SPED de entrada | Leitor parcial e versionado, incluindo C100 e grupos de cobrança/cadastro no perfil suportado | Outros registros/casos e versões; o perfil parcial atual delimita 020/2026 e não é leitor universal |
| Tributação | Regras aprovadas por empresa/data/escopo, modelos independentes em rascunho, perfis aritméticos e memória | Parametrização/homologação por tributo/jurisdição; campos/códigos isolados não determinam incidência |
| Cadastros fiscais | CFOP/NCM/receita/serviço; importação canônica revisada com origem e vigência | Cargas oficiais completas, adaptadores nativos por edição/órgão e atualização automática não concluídos |
| Apuração | Fatos escriturados, efeitos declarados, ajustes, reservas e transporte explícito por componente/receita | Restrições legais, códigos oficiais de ajuste, pagamentos/compensações e segregação automática de saldo por UF/município/regime |
| Livros | Livros/exports operacionais preservados; Diário/Razão/Balancete configuráveis no #15 | Leiautes oficiais completos e validação com ferramentas/importadores confirmados |
| Financeiro | Títulos vinculados, vencimentos/saldos, liquidação parcial manual e estorno | Importadores de extratos OFX/CNAB/TXT e extração de PDF/imagem com conferência e associação não implementados |
| Fechamento | Bloqueios por cliente/competência/módulo; recepção independente; origem com saldo transportado protegida | Homologar o procedimento operacional e as correções em períodos/obrigações já entregues |
| Distribuição | Código comum, Windows GUI/tray, Docker e workflows GHCR preservados | Integração/revisão dos PRs, release autorizada e homologação da versão combinada no ambiente de destino |

## Próximo incremento escolhido: tributação em lote

As regras já calculam uma operação por vez, mas o operador precisa abrir e aplicar o cálculo em cada ficha. Esse trabalho repetitivo limita a utilidade com dezenas/centenas de documentos. A evolução em lote reutiliza exclusivamente o motor aprovado existente e não depende de inventar novos leiautes ou regras legais.

O operador seleciona de 1 a 100 operações salvas da mesma empresa/competência. A interface permite filtrar fichas sem memória e selecionar explicitamente as visíveis; desmarcar o filtro permite escolher fichas já calculadas para novo cálculo conferido. A prévia registra versões, hashes, memórias e pendências de cada ficha. A resposta é limitada a 8 MiB; lotes maiores precisam de seleção menor. Uma pendência impede a aplicação de todo o lote. Não há descarte silencioso das operações que falharam.

Após conferir todas as memórias e informar motivo, a aplicação cria novas versões de rascunho numa única transação. Falha em qualquer ponto desfaz cálculos, revisões, tentativas e manifesto do lote inteiro. Repetição com a mesma chave/conteúdo retorna o resultado preservado; conteúdo diferente é recusado. Alteração de regra, fonte ou ficha depois da prévia exige nova conferência.

A aplicação em lote não confere ou escritura operações, não cria partidas/títulos e não concede efeitos legais. Cálculo documental v1 e por item v2/v3 permanecem distintos, com suas memórias originais. O resumo por componente soma valores calculados por item; efeitos mistos exigem conferir as linhas, sem deduzir saldo líquido apenas do total positivo.

Fichas selecionadas com alterações locais não salvas bloqueiam a ação na interface. Após sucesso, as fichas abertas nesta instância são sincronizadas com as versões atuais; outras guias/operadores conservam seus rascunhos e precisam reconciliá-los com o histórico, sob os controles existentes de versão e memória.

O manifesto e as memórias são consultáveis/exportáveis como JSON operacional, inclusive depois de mudanças posteriores das fichas. Não são arquivo SPED, prova de obrigação entregue ou leiaute Prosoft.

## Contrato e migração deste incremento

Esquema **16**, aditivo e transacional, com `tax_calculation_batches`. O manifesto liga entrada e saída de cada operação às memórias existentes; não regrava documentos ou apurações anteriores. Bancos no esquema 16 exigem executável compatível. O PR #15, ainda no esquema 15, precisa reconciliar suas expectativas de migração na composição.

`src/tax_batch.py` contém seleção, prévia, aplicação atômica e histórico paginado. `src/tax_engine.py` passa a aceitar transação externa interna, obrigatoriamente ativa; o uso individual conserva sua transação anterior. `src/persistence.py` registra esquema/mixin. `src/tax_api.py` exige escopo da empresa, CSRF e `workspace.write` para prévia/aplicação; consultas usam `workspace.read`. A conferência/escrituração continuam com as permissões próprias existentes.

O frontend compartilhado é o ponto de composição com a frente contábil. Não são alterados o núcleo de contabilização, liquidação, cobrança, regras legais, integração bancária, packaging ou arquitetura de executáveis.

## Plano restante e materiais necessários

1. **Consolidar a versão combinada.** Revisar a cadeia fiscal e a composição contábil mais recente, reconciliar o esquema final e executar testes/builds nesse conjunto. Merge e release dependem de autorização específica. Antes de atualizar um banco operacional, testar migração e restauração em cópia privada autorizada.
2. **Reduzir digitação por item.** Propor valores observados do XML com caminhos exatos, origem e perfil de extração separado; distinguir bruto, descontos, frete, outros valores e tributos, sem transformar bruto em líquido por suposição. Material: XMLs autorizados/anonimizados representativos e casos esperados; conferir MOC e NTs aplicáveis ao período antes de ampliar o contrato. Referência histórica localizada: [MOC 7.0 — Anexo I](https://www.nfe.fazenda.gov.br/portal/exibirArquivo.aspx?conteudo=J+I+v4eN00E%3D), novembro/2020; não comprova cobertura das atualizações de 2026.
3. **Homologar parâmetros e modelos por empresa.** Definir empresa/jurisdição/regime, operações prioritárias, tratamentos/efeitos e resultados esperados sob responsabilidade fiscal. Não instalar modelos prontos como regras legais aprovadas por padrão. CBS/IBS permanecem fora deste motor.
4. **Concluir fontes de cadastros.** Identificar edição e vigência de CFOP/NCM, órgão/documento de receita e município/padrão de serviços. Obter arquivos oficiais acessíveis e comprovar transformação, revisão e aplicação. A importação canônica existente não certifica origem oficial ou completude.
5. **Eventos e novos documentos.** Definir prioridades entre cancelamentos/correções, CT-e e NFS-e, com leiautes, versões, municípios e amostras autorizadas. Eventos não devem apagar movimentos nem determinar retificação por suposição.
6. **Extratos e baixa por arquivo.** Começar por formatos/versionamento de bancos efetivamente utilizados. OFX, CNAB e TXT exigem identificação/proveniência e reconciliação; PDF/imagem precisam de extração conferida. Correspondência sugerida não autoriza baixa automática.
7. **Livros e saídas externas.** Definir obrigação/importador, versão e leiaute exigido; construir adapters separados e testar sua aceitação no ambiente confirmado. JSON/CSV operacional não será rotulado como obrigação ou importação homologada. Para Prosoft, versões/rotinas/leiautes e resultados de teste continuam necessários.
8. **Piloto operacional.** Validar recepção → organização → parametrização → cálculo → conferência/escrituração → financeiro/livros → apuração → fechamento e correções, numa empresa e recorte definidos. Aprovação de testes de software não substitui homologação fiscal ou operacional.

Não é necessário fornecer credenciais ou documentos reais em Git/CI. Nenhum material privado é presumido acessível. Os binários/prints legados continuam bloqueados pela transferência da Library (`library file transfer failed: download failed`); não houve bytes/pixels inspecionados nem execução de software desconhecido.

## Critérios verificáveis e resultados

Testes sintéticos do lote cobrem prévia sem gravação, pendências individuais, aplicação atômica, rollback após gravação parcial interna, idempotência, concorrência, alterações posteriores à prévia, mistura documental/item/FCP, limites, integridade de originais/manifestos, histórico paginado, permissões e migração preservando memórias e bloqueios. O navegador cobre guias não salvas, correção de pendência, confirmação, resposta perdida, repetição sem duplicação, sincronização das fichas, download, reload, contexto e mobile.

Os resultados reais de testes locais, composição contábil, builds e CI do novo SHA são registrados na descrição do PR e na conversa. Os builds anteriores não são atribuídos automaticamente ao novo incremento. O projeto ainda não é declarado fiscalmente homologado ou completo.
