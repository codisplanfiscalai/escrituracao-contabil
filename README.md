# Escritura

Aplicação de escrituração fiscal e contábil, com portal Vue, API Python, SQLite, aplicativo Windows gráfico com área de notificação e execução em servidor Docker.

Uma aplicação integrada: menus, módulos e relatórios compartilham contexto e serviços internos, com filtros e opções. Os executáveis externos são referências para levantamento; não haverá um EXE por tela ou relatório.

[Tributação e apuração por empresa](docs/tributacao-parametrizada.md): regras percentuais versionadas para ICMS/ISS/PIS/COFINS, cadastros de CFOP/NCM/receita/serviço, modelos copiáveis em rascunho e memória de cálculo. Não há alíquotas ou tratamentos legais pré-carregados. Cada modelo precisa de validação no destino; cálculo e apuração permanecem sujeitos à conferência.


Incremento de 06/11 em revisão no [PR #8](https://github.com/codisplanfiscalai/escrituracao-contabil/pull/8): [análise dos anexos, cadastro separado da empresa usuária, busca sem competência, contratos e validação](docs/analise-referencias-2026-11-06.md). A transferência dos executáveis/prints falhou; sua tecnologia e suas telas não foram verificadas. O cadastro complementar está em Empresas, e a empresa usuária em Configurações. Esses dados declarados não ativam cálculo fiscal/trabalhista. A busca em Recepção consulta fontes já recebidas sem exigir competência. Windows inicia no tray; `--show-window` abre a administração. A mudança de inicialização ainda exige validação nativa x86/x64.

A jornada foi reformulada: **receber → identificar e organizar → escriturar → conferir → consultar livros e financeiro → encerrar e exportar**. Importar e lançar manualmente são entradas para a mesma escrituração. Guias permitem alternar atividades; editores de usuários e perfis também usam guias. No portal, os modais são restritos à configuração transitória do 2FA e aos códigos de recuperação.

- [Novo domínio, migração, regras e limites](docs/reformulacao-fiscal-contabil.md)
- [Validação executada e diferenças concretas](docs/validacao-reformulacao.md)
- [Auditoria de todos os recursos e caminhos de navegação](docs/auditoria-navegacao-guias.md)
- [Revisão de integridade, dados e contexto de build](docs/revisao-local-pre-publicacao.md)
- [Portal, primeiro acesso e instalação](docs/portal-corporativo.md)
- [Windows offline, Docker e dependências](docs/distribuicao-offline-ghcr.md)
- [Branches, builds e releases](docs/fluxo-desenvolvimento.md)

## Trabalhar na aplicação

1. Cadastre a empresa. Os códigos do Prosoft são opcionais.
2. Em **Recepção**, envie XML, SPED ou pacotes. Não é necessário definir competência nem plano para receber. A caixa de entrada preserva originais, identificação e erros por arquivo.
3. Importe o plano em **Plano e políticas**, usando CSV com `codigo;descricao;tipo;natureza;superior`. Outras colunas são preservadas como atributos. Contas analíticas, hierarquia e versões são explícitas; não são deduzidas pelo nome.
4. Configure **Competências**: mês dos movimentos e referência dos parâmetros são independentes. Políticas aprovadas podem propor contas de débito e crédito por natureza e referência.
5. Organize cada fonte na competência escolhida. Em **Escrituração**, abra o documento ou um lançamento manual. A mesma ficha reúne fatos fiscais, partidas e cobrança; dados ausentes permanecem pendentes. Salvar versão não cria movimentos.
6. Confira a versão completa e escolha **Escriturar**. Movimentos e títulos são gravados na mesma transação. Alterações exigem outra versão e conferência; efetivados mantêm snapshot imutável.
7. Declare os **Saldos iniciais** com partidas ou confirme expressamente saldo zero. **Financeiro** prepara liquidações com partidas próprias, sem reconhecer novamente compras/vendas. Estornos são operações vinculadas e conservam o histórico.
8. Consulte **Livros e relatórios**: diário, razão, balancete com continuidade, livro fiscal e financeiro. Exporte o pacote operacional JSON/CSV/ZIP com manifesto e hashes. **Encerramento** exige resolver pendências e declarar a abertura; reabertura exige motivo.

Fichas incompletas são preservadas no banco por usuário, empresa e competência e recuperadas após recarga. Formulários gerais conservam estado ao alternar recursos; seus rascunhos sem senhas ficam no navegador por usuário. Arquivos ainda não enviados precisam ser selecionados novamente após recarregar a página.

## Migração

O esquema 13 acrescenta regras/tabelas/modelos tributários, memórias de cálculo e apurações versionadas, sem recálculo retroativo. O esquema 12 acrescentou [encerramento independente fiscal/contábil por empresa e competência](docs/encerramento-por-modulo.md), preservando o controle global anterior. O esquema 11 acrescentou cadastros versionados de clientes e da empresa usuária. O esquema 10 adicionou o novo modelo em transação, preserva originais, decisões, rascunhos, movimentos fechados e arquivos exportados. Fechamentos/exportações fiscais anteriores continuam protegidos. Movimentos contábeis anteriores entram nos livros sem ser recriados. Em **Histórico**, rascunhos elegíveis podem ser retomados para nova conferência. Lotes documentais antigos exigem abrir cada documento para definir seus componentes.

A interface anterior foi substituída. Seus endpoints de gravação fiscal, contábil, documental e financeira retornam HTTP 410; consultas históricas continuam disponíveis. Faça backup privado antes de atualizar. Uma migração testada com bases sintéticas não substitui conferir a cópia privada do banco existente.

## Limites comprovados

- NF-e/NFC-e 4.00 modelos 55/65: cabeçalho, itens observados e cobrança quando identificada. Sem validação de assinatura, autorização ou esquema XSD completo. Serviços e folha admitem valores informados manualmente; não há cálculo de folha, CBS/IBS ou geração de obrigações. Tributação percentual e apuração aritmética dependem de regras explicitamente aprovadas; regimes especiais e validação legal integral permanecem pendentes.
- SPED: preservação do original e perfil explícito parcial EFD-ICMS/IPI 020 para cabeçalho/C100 55/65. C140/C141 não são convertidos em cobrança por suposição. Outros perfis permanecem pendentes.
- ZIP integrado. 7z/RAR dependem de libarchive e estão indisponíveis no Windows congelado atual; RAR5/comprimido não homologado. Até 10 MiB por envio web, 500 entradas totais e 100 MiB expandidos. Links, pacotes aninhados e criptografia são recusados.
- Exportação operacional própria disponível. Geração de obrigação SPED, PVA/transmissão e importação Prosoft permanecem indisponíveis sem perfis verificados. Os leiautes reais tiveram HTTP 403; o download autorizado do ZIP do gerador da Library falhou na rede. Nenhuma compatibilidade ou homologação é alegada.
- Financeiro de competências reconstrói liquidações e estornos do novo livro pelas datas econômicas. Cancelamentos/estornos anteriores sem competência econômica ficam identificados como limitação histórica. Sem conciliação bancária automática.
- Builds Windows precisam de execução nativa x86/x64. Mudanças locais não são uma distribuição validada; não publicar nem implantar por inferência.

## Executar e verificar

No Windows, extraia o pacote completo e abra `EscrituracaoContabil.exe`. Use a janela e o ícone da área de notificação. Para servidor, siga a instalação documentada e mantenha dados/chaves em volume privado; acesso em rede exige HTTPS e autenticação.

Para desenvolvimento:

```sh
python -m pip install --only-binary=:all: --require-hashes -r requirements-server.txt
python -m src.server.runtime --host 127.0.0.1 --database /caminho/privado/escrituracao.sqlite3
```

Abra `http://127.0.0.1:8765` e configure o administrador com a chave em `identity/setup.token`, junto ao banco. O servidor privado `python -m src.local_app` usa somente loopback, para testes e integração local; não oferece autenticação compartilhada.

```sh
python scripts/build.py check
python qa/portal_browser.py
python qa/fiscal_browser.py
python qa/workspace_navigation.py
python qa/navigation_audit.py
python scripts/smoke_import_ui.py
python qa/integrated_flow.py
```

As verificações de navegador exigem Playwright e Chromium. As fontes usadas nos testes são sintéticas. Não adicione bancos, documentos fiscais, credenciais, certificados ou anexos reais ao Git/CI/artefatos públicos. Os documentos anteriores em `docs/` registram o histórico dos incrementos; o contrato operacional vigente é a [reformulação](docs/reformulacao-fiscal-contabil.md).
