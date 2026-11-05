# Auditoria de navegação e guias — 05/11/2026

Escopo: caminhos do portal autenticado, modo HTTP local e ações que abrem recursos dentro das telas. Alterações locais na branch `refactor/fiscal-accounting-journey`; nenhuma autorização de publicação ou PR foi presumida.

## Inventário e correções

| Recurso / caminho | Abertura e estado |
| --- | --- |
| Os 18 recursos do menu, inclusive administração e conta | Guia de atividade; instância mantida ao alternar |
| Painel inicial, atalhos de próximos passos, marca, avatar e cartões de empresa | Usam o mesmo roteador de guias; a primeira abertura também cria sua guia |
| Novo usuário e edição de cada usuário | Guias próprias `user-editor/<id ou new>`; deixaram de ser modais |
| Novo perfil e edição de cada perfil | Guias próprias `role-editor/<id ou new>`; deixaram de ser modais |
| Fichas de escrituração, liquidação preparada, abertura e estorno | Guias da operação, com rascunho no banco e recuperação pelo Histórico |
| Decisões e versões de uma fonte | Guia por fonte; consultas diferentes não substituem a anterior |
| Dependências / retirada de uma fonte | Guia por fonte, com motivo e confirmação independentes; fechar/reabrir conserva o motivo |
| Balancete, diário, razão, livro fiscal e financeiro | Cinco guias com painéis próprios mantidos; setas/Home/End e atributos de acessibilidade |
| Nove recursos do modo local | Guias de recursos, com fechamento/reabertura; formulários mantidos ao alternar |

Formulários de parâmetros, filtros, seleção de fonte e preparação de comandos permanecem dentro da guia do respectivo recurso. Salvar, atualizar, confirmar e baixar arquivos são ações da guia, sem abrir outra página de trabalho.

Os modais do portal ficaram restritos à configuração transitória do autenticador 2FA e à exibição dos códigos de recuperação. O fundo fica inerte, Tab/Shift+Tab permanecem no modal e Escape restaura o foco. Senhas não são gravadas com os rascunhos dos editores.

No launcher Windows, a inspeção de `packaging/windows_app.py` confirmou quatro áreas em `ttk.Notebook`: Serviços, Configurações, Servidor Docker e Histórico. Seus diálogos são seletores de arquivo, informações/erros e confirmação de parada/reinício. Não houve mudança no launcher nem execução nativa Windows nesta auditoria.

## Caminhos corrigidos

- Fechar a última guia deixa uma guia inicial utilizável, inclusive quando o endereço já era o da página inicial.
- “Ir para o conteúdo” move o foco, preservando o recurso e o endereço; não passa pelo roteador como se fosse outra página.
- A abertura programática aguarda a rota concluir. Salvar um usuário/perfil retorna à lista correta e atualiza os registros, mantendo os outros rascunhos.
- Voltar/avançar, fechar/reabrir e recarregar recuperam os editores sem trocar seus formulários. Guias restauradas são filtradas pelas permissões atuais.
- Cartões de empresa aguardam a inicialização da área de trabalho antes de aplicar empresa/competência. Foi retirada a restauração por temporizadores e eventos de controles ainda carregando.
- No portal do cliente, mudar de empresa pelo painel recarrega a guia já aberta; não conserva a lista da empresa anterior sob o novo contexto.
- A navegação do modo local também preserva o rascunho antes de trocar de recurso.

## Evidência automatizada

`qa/navigation_audit.py`, incluído no job de navegador da CI, verifica no Chromium:

- editores de dois usuários e um perfil em guias, formulários independentes, fechamento/reabertura, volta/avanço e recarga;
- senha ausente do armazenamento de rascunhos e campos restantes recuperados;
- salvamento real de perfil e retorno à lista com o registro atualizado;
- guia inicial, atalhos, marca/avatar, cartões, endereço inválido normalizado e fechamento da última guia;
- “Ir para o conteúdo” sem alterar a atividade;
- modal 2FA com fundo inerte, foco contido e restaurado;
- troca de empresa de um cliente com dois escopos autorizados, conferindo as duas listas de arquivos separadamente;
- decisões/dependências de duas fontes, motivos separados e retorno às mesmas guias, nos modos local e autenticado;
- os cinco livros em guias, painéis preservados e navegação por teclado;
- fechamento e reabertura das guias de recursos do modo local.

A regressão `qa/workspace_navigation.py` percorre todos os itens disponíveis do menu e confere a guia correspondente, além dos rascunhos por empresa/competência, interrupção de gravação, resposta perdida e larguras 1440/1024/768/390/320. `qa/portal_browser.py`, `qa/fiscal_browser.py`, `scripts/smoke_import_ui.py` e `qa/integrated_flow.py` continuam cobrindo os fluxos reais sobre as telas atualizadas.

Testes usam contas, empresas e documentos sintéticos em bancos temporários. Esta evidência é de navegação e comportamento local; não substitui build nativo Windows, homologação fiscal ou teste em produção. O contêiner eventualmente construído nesta etapa é local; nenhuma imagem foi publicada.
