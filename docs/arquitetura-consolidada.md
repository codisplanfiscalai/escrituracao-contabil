# Arquitetura consolidada e plano de integração

Análise de 04/11/2026. Este documento diferencia o código existente, recursos identificados nos materiais fornecidos e a arquitetura proposta. Não declara recursos futuros como implementados.

## Evidência e abrangência

Inventário completo dos dois pacotes: 1.083 arquivos, sendo 695 da referência administrativa e 388 da referência fiscal. Todos os arquivos foram inventariados por caminho, tamanho e SHA-256; arquivos textuais foram indexados e os 502 arquivos Python passaram por análise sintática AST sem erros. Somam aproximadamente 207 mil linhas textuais, incluindo documentação, testes, arquivos gerados e dependências fornecidas. Isso não significa leitura manual linha a linha, execução integral dos dois produtos nem auditoria de vulnerabilidades.

A revisão de fluxos cruzou módulos, modelos, rotas, testes e documentação: identidade, autorização, sessões, MFA, e-mail, portais, processamento documental, cobrança, SPED, editor, consolidação, auditoria, persistência, filas, distribuição e CI. Os anexos originais permanecem intactos e não são incorporados ao repositório. Dependências e ativos de terceiros exigem preservação de suas próprias licenças; a identidade dos produtos de referência não entra nos novos arquivos.

A retomada inicial foi conferida no SHA 8f8e075566ca718708945520f6fea6e80b5c6451. Durante a análise, main avançou para o merge 959d325fa12040a755ffa874847fdec34aae0a02 e a linha funcional recebeu 35096b18eaa45a8a24403a930642dda86f90166c. A integração utiliza esta última revisão funcional, preservando editor assistido, associação de cobranças, correções HTTP e esquema 5.

## Decisões centrais

1. Preservar os módulos de domínio e suas invariantes; ampliar por contratos e adaptadores. Não substituir o banco, framework, interface e motor simultaneamente.
2. Usar Python no backend. As duas referências já possuem FastAPI; a adaptação de uma API autenticada é coerente e evita introduzir PHP/Laravel apenas para reproduzir telas.
3. Evoluir o portal com Vue 3 em módulo separado; introduzir TypeScript quando houver migração incremental do build. Reaproveitar padrões e componentes isoláveis; não transportar toda a árvore de templates ou seu build acoplado ao domínio escolar.
4. Manter SQLite no modo local de compatibilidade até existir migração testada. O destino compartilhado pode usar PostgreSQL, com adaptadores de persistência e migração explícita. Não compartilhar arquivo SQLite em pasta de rede.
5. Separar administração Windows, serviços de negócio e controle de infraestrutura. O aplicativo do operador não deve conter uma cópia divergente do motor contábil.
6. Ter um serviço de identidade e uma política de autorização. Não instalar duas autenticações e dois cadastros de usuários concorrentes.
7. Não habilitar cálculo de CBS/IBS nesta consolidação. Preservar dados originais e os limites de escopo já estabelecidos.

## Componentes e responsabilidades

| Componente | Responsabilidade | Fronteira |
|---|---|---|
| Windows Desktop | Configuração local, tray, estado, notificações, comandos operacionais | Não classifica tributos nem escreve diretamente no banco remoto |
| API Python | Identidade, autorização, contratos de aplicação, orquestração | Não executa comandos de shell arbitrários recebidos da interface |
| Núcleo documental | Originais, hash, chave, observações, conciliação, revisão | Não transforma conflito em vencedor silencioso |
| Núcleo contábil | Planos, mapeamentos, partidas, snapshots e fechamento | Não infere conta/contrapartida e não reescreve lote fechado |
| Módulo fiscal | Perfis versionados, parsers, editor, validação e exportação | Exportação depende de perfil/destino explícito |
| Portal administrativo | Empresas, usuários, permissões, parâmetros e operação | Menu visível não substitui autorização da API |
| Portal do cliente | Documentos e acompanhamento das empresas autorizadas | Não herda vínculos escolares ou permissão administrativa global |
| Portal público futuro | Conteúdo publicado, com domínio e identidade próprios | Não consulta dados privados por seleção implícita de empresa |
| Jobs e outbox | Processamento longo, retries, idempotência e eventos | Nunca confirma duas vezes o mesmo efeito de negócio |
| Storage | Originais/artefatos por hash, acesso controlado e retenção | Hash não substitui política de backup nem assinatura |
| Docker/GHCR | Execução padronizada e distribuição por versão/digest | Registro de imagens não é servidor de aplicação |

Fluxo previsto: Windows e portal acessam a API autenticada por HTTPS; a API usa serviços de domínio; tarefas longas entram em fila persistente; workers acessam banco/storage; eventos operacionais retornam à interface. O acesso ao runtime Docker fica em agente administrativo separado, com comandos permitidos e escopo de instalação. Nenhum socket Docker é entregue ao navegador ou à API de negócio.

## Matriz de preservação e reaproveitamento

| Recurso encontrado | Decisão | Integração/aceite |
|---|---|---|
| Identidade Escritura e ícones | Preservar | Reproduzir PNG/ICO e validar recursos PE |
| Empresas, períodos, planos e hierarquia | Preservar | Mesmos IDs e versões; referência não copia movimentos |
| Mapeamentos com vigência/aprovação | Preservar | Destino analítico e regras atuais do motor |
| Originais XML/SPED e observações | Preservar | Reimportação não duplica entidades ou efeitos |
| Revisões e associações de cobrança | Preservar | Fingerprints, correspondência 1:1 e caducidade |
| Partidas explícitas e editor assistido | Preservar | Centavos exatos, equilíbrio e JSON avançado |
| Evidências de fechamento | Preservar | Histórico, hashes, download e imutabilidade |
| Login/sessões/refresh | Adaptar | Um serviço, revogação e contexto de empresa validados no servidor |
| Perfis e capacidades | Adaptar | Tenant/escritório, empresa e usuário; catálogo fiscal/contábil próprio |
| Primeiro acesso/reset de senha | Adaptar | Convite/token de uso único, expiração, entrega SMTP testável |
| TOTP e recuperação | Adaptar | Ativação confirmada, segredo protegido, prevenção de replay e revogação |
| Layout, menus, formulários e busca | Adaptar | Componentes desacoplados e identidade própria |
| Portal externo | Adaptar estrutura | Remover vínculos aluno/responsável; criar vínculo cliente/empresa |
| E-mail transacional | Reaproveitar contrato | Configuração, teste, fila, tentativas e diagnóstico sem segredo |
| Webmail completo e provisionamento de correio | Posterior, opcional | Não são pré-requisitos de login ou recuperação de senha |
| Auditoria transversal | Integrar | Ator real, motivo, correlação e histórico; preservar trilhas de domínio |
| Backup/restore/diagnóstico | Adaptar | Restauração ensaiada, isolamento e versão de esquema |
| Integrações/webhooks | Adaptar infraestrutura | Assinatura, idempotência e contrato por conector |
| OCR, assinatura e certificados | Catalogar para extensão | Reutilização técnica futura; não prometer habilitação imediata |
| XML 55/65/57, eventos e ZIP | Integrar por perfil | Modelos distintos, limites, chave/hash e origem preservada |
| Conversão XML → EFD | Integrar sob contrato | Cadastros/competência/contabilista confirmados; sem crédito presumido |
| FAT/DUP e geração de parcelas | Preservar comportamentos úteis | Original/manual/derivado separados; simular antes de materializar |
| TXT financeiro de integração | Adaptar por versão do importador | Comparar bytes/campos/encoding e validar instalação de destino |
| C140/C141 em modelo 55 | Isolar compatibilidade | Não ativar como perfil oficial sem especificação demonstrada |
| Parser/serializer e fechamentos | Reaproveitar com caracterização | Ordem/hierarquia, C990 e Bloco 9 consistentes |
| Editor SPED e edição em lote | Integrar gradualmente | Fonte intacta, cópia editada, diff e validação antes/depois |
| Comparação SPED × planilhas/PDF | Integrar | Chave/documento/participante, critérios de associação e pendências |
| Consolidação NFC-e e relatórios XLSX | Integrar separadamente | Resumo consultivo não substitui documentos fiscais individuais |
| Regras fiscais específicas de UF/custo | Manter como políticas opt-in | Revisão por vigência/contexto; não generalizar automaticamente |
| Workflow de competência | Adaptar | Não confundir reabertura fiscal com estorno de lote contábil fechado |
| Jobs/leases/retries/outbox | Reaproveitar padrões | Claims atômicos, recuperação e consumidores idempotentes |
| Build/release/GHCR/manutenção | Implementar agora | Fluxo dedicado documentado; sem nomenclatura herdada |
| Matrículas, turmas, frequência, notas, diário escolar | Excluir do produto novo | Não incluir tabelas, rotas, menus ou permissões desses domínios |

## Diferenças que impedem cópia direta

**Autenticação acoplada.** A referência administrativa contém classes de escola, vínculos por escola, perfis acadêmicos e cabeçalhos próprios dentro das rotas de autenticação. Renomear escola para empresa seria insuficiente: autorização, convite, bootstrap e portal precisam de modelo próprio. O mecanismo de cancelar requisições quando muda a organização é útil e deve ser preservado.

**Dois frontends distintos.** Um build usa Vue global com templates pré-compilados e namespaces; o outro usa Vue SFC, Vite e módulos TypeScript. Não juntar bundles ou copiar dist. Selecionar componentes e portar contratos para um único build, mantendo a interface atual até haver equivalência funcional.

**Comportamento local e persistido.** A referência fiscal contém motores Python e rotinas locais TypeScript/Web Worker, inclusive rascunhos em IndexedDB e parâmetros de navegador. Preservar o modo local como capacidade explícita; upload/persistência no servidor deve ser uma ação consciente. Comparar fixtures entre os motores antes de substituir cálculos.

**Documentação divergente sobre faturamento.** Há documentos que restringem C140/C141 ao modelo 01 e código/testes que também aceitam entrada regular modelo 55. Uma camada altera métodos de validação em runtime e usa visão temporária do modelo 55 como 01. Não transportar esse monkey patch global: registrar perfis de compatibilidade independentes, com política explícita e validação de destino. A existência de teste do produto não equivale à validação no PVA.

**Arredondamento e truncamento.** O motor financeiro Python usa centavos inteiros; partes TypeScript usam Number e arredondamento. O serializador TXT contém campos fixos que podem truncar texto e substituição de caracteres não representáveis. Importar comportamento por fixtures, com diagnósticos explícitos de perda de informação; não alterar regras silenciosamente.

**Tributação específica.** Há regras para ST/lubrificantes e tratamento de IPI como custo de compra. São regras do domínio e não componentes administrativos neutros. Catalogar versão, entrada, saída e testes; ativar somente em contexto parametrizado e validado. Não estender a todo contribuinte por analogia.

**Banco e filas.** SQLAlchemy/Alembic/PostgreSQL, S3, Redis e RabbitMQ aparecem nos materiais; a base atual usa stdlib/SQLite. Não introduzir todos de uma vez. Começar pela API/contratos, adicionar jobs persistentes e storage quando necessário, depois migrar dados com reconciliação. Não manter dois escritores independentes para os mesmos eventos contábeis.

## Windows e Docker: transição original

O incremento de distribuição entrega aplicativo gráfico com tray e controles do serviço local de compatibilidade. O núcleo fiscal/contábil continua inalterado. Os checks Windows passam a exigir PE GUI e ausência de console no EXE.

O modo Docker compartilhado exige primeiro API autenticada, identidade real e isolamento de empresas. Na análise inicial, o contêiner ainda não fornecia essa fronteira. Requisitos identificados para evolução: cadastro de instalações/endpoints, validação TLS, autenticação de operador/dispositivo, capacidades anunciadas pela API, consulta de versões e health/readiness, logs paginados e comandos administrativos com autorização e idempotência.

Em instalação remota, o cliente Windows conversa com um agente no host dos contêineres. Iniciar/parar/reiniciar deve selecionar apenas serviços cadastrados dessa instalação, sem receber comandos arbitrários. Iniciar toda a infraestrutura não pode depender exclusivamente da API de negócio que está parada. Credenciais ficam no cofre do sistema operacional; tokens de sessão, segredos de e-mail e credenciais GHCR não entram em arquivo de configuração comum.

Fechar a janela ou ESC recolhe o aplicativo; Sair o encerra. Reinício de servidor não deve apagar dados, migrar banco implicitamente ou confundir encerramento do cliente com desligamento remoto. Configurações globais pertencem ao servidor; preferências da estação pertencem ao aplicativo.

## Sequência de integração e critérios de aceite

| Etapa | Entrega | Condição para avançar |
|---|---|---|
| 1. Distribuição e baseline | main/develop, SemVer, CI, GUI, releases, hashes e limpeza | Testes existentes preservados; Windows x86/x64 e Docker verificados |
| 2. Contratos de aplicação | Fachada de serviços, ActorContext, TenantContext, API versionada | Mesmas respostas/efeitos da base; isolamento e concorrência testados |
| 3. Identidade e administração | Login, usuários, permissões, sessões, reset, 2FA e SMTP | Nenhum acesso cruzado; revogação imediata e segregação real |
| 4. Portal próprio | Layout, menus e fluxos administrativos; portal cliente | Paridade dos fluxos atuais e autorização em cada operação |
| 5. Serviços Docker e Windows | API servida, instalação, agente e comandos administrativos | Operação pela GUI sem terminal; testes de desconexão/reconexão e parada |
| 6. Cobertura documental/fiscal | Modelos/ZIP/eventos, editor, comparação e consolidação | Fixtures de caracterização, originais imutáveis e nenhuma regressão |
| 7. Integração contábil externa | Importação de planos e perfis de exportação | Layout real, campos/encoding e resultado no importador conferidos |
| 8. Escala e operação | Migração PostgreSQL, jobs/outbox/storage e recuperação | Contagens/hashes/saldos reconciliados; restore ensaiado; rollback definido |

A interface nova pode ser introduzida por módulo, mantendo a anterior acessível durante a transição. Ativar por capacidade/feature flag, comparar resultados em paralelo sem materializar efeitos duplicados e retirar o caminho anterior somente após equivalência demonstrada.

## Invariantes de regressão

- Uma reimportação não cria novo documento, título, parcela ou lançamento indevido.
- XML/SPED entram em qualquer ordem sem duplicação; valores divergentes permanecem visíveis.
- FAT sem DUP permanece cobrança existente com pendência; ausência de vencimento não vira D+30 automaticamente.
- Decisão documental ou associação depende da versão atual das fontes; alteração exige revisão.
- Partidas permanecem equilibradas por documento/grupo/lote, com valores exatos.
- Fechado não é sobrescrito; pagamentos, estornos e outros eventos exigem identidade própria.
- Exclusão respeita dependências; originais, auditoria e evidências não são removidos por limpeza de cache.
- Fiscal oficial, compatibilidade de importador e relatório consultivo têm perfis diferentes.
- Mudança de empresa invalida requisições e rascunhos do contexto anterior.
- Autorizações reais precedem exposição em rede; token local não vira login multiusuário.

## Limites da análise

A suíte da base funcional foi executada; as duas aplicações de referência não foram implantadas integralmente neste ambiente. A análise estrutural cobre os pacotes, e a revisão de comportamento se concentra nos fluxos que serão integrados. Cada módulo ainda requer testes de caracterização antes de portar implementação. A análise não substitui homologação fiscal, testes com os layouts reais já fornecidos nem ensaio em instalações Windows/Docker de produção.

## Implementação corporativa 0.3.0

A evolução de identidade e portal foi implementada em módulos novos, preservando o motor e o esquema contábil. Há API FastAPI autenticada, portal Vue com templates pré-compilados, administração, cliente, TOTP, sessões, reset e SMTP. O aplicativo Windows executa o portal local autenticado e administra contêineres por agente HTTPS independente. A integração visual preserva os componentes operacionais existentes dentro da área de trabalho autenticada. Os detalhes de operação, permissões, implantação e limites estão em [portal-corporativo.md](portal-corporativo.md).

A decisão de manter os componentes contábeis em uma área integrada evita reescrever os fluxos de revisão, conciliação e fechamento ao mesmo tempo que se introduz autenticação. A autorização é aplicada na API que reutiliza a mesma fachada de domínio. O layout e a navegação novos não autorizam operações por conta própria.
