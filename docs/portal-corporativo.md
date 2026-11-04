# Portal corporativo e operação Windows

## Componentes implementados

O portal usa Vue 3 local, templates pré-compilados e recursos sem CDN. O layout incorpora navegação lateral, grupos de menus, cabeçalho, cartões, tabelas, formulários, diálogos e telas de acesso adaptados à identidade Escritura. O portal público tem entrada independente em `/public`; a área do cliente é filtrada por perfil e empresas autorizadas.

A API FastAPI autentica cada operação e chama a fachada `dispatch` e os mesmos módulos contábeis existentes. O SQLite de escrituração permanece no caminho anterior, sem copiar documentos ou alterar regras de cálculo. Identidade, sessões, configuração e fila de e-mail ficam em banco separado na pasta `identity`. O ator registrado pelo motor passa a ser o identificador do usuário autenticado. A interface anterior continua integrada em `/workspace`, com a mesma funcionalidade e estilo alinhado ao portal.

| Área | Operação disponível |
|---|---|
| Primeiro acesso | Administrador inicial, chave de instalação de uso único para configuração |
| Identidade | Login, logout, expiração absoluta/inatividade, revogação por conta e sessão |
| Usuários | Cadastro, edição, ativação/inativação, perfil e empresas permitidas |
| Perfis | Catálogo de permissões, perfis padrão preservados e perfis personalizados |
| Segurança | TOTP confirmado, prevenção de reutilização, recuperação por códigos de uso único |
| Senhas | Solicitação por e-mail, token expirável e consumível uma vez; 2FA mantido quando habilitado |
| E-mail | SMTP TLS, segredo cifrado, teste de entrega, fila persistente e diagnóstico sem conteúdo |
| Cliente | Empresas autorizadas, períodos, documentos e upload de XML/SPED |
| Operação | Competências, planos, mapeamentos, documentos, conciliação, revisão e escrituração existentes |
| Administração | Parâmetros gerais, ordem dos menus e histórico administrativo |
| Windows | Aplicação GUI, tray, portal local autenticado, configuração e operação de instalação Docker por HTTPS |
| Agente | Consulta, início, parada, reinício e logs somente dos contêineres rotulados da instalação |

## Windows

Extraia todo o ZIP e abra `EscrituracaoContabil.exe`. O aplicativo abre a administração da estação e mantém o ícone na bandeja. Inicie o serviço local, use **Copiar chave do primeiro acesso** e **Abrir portal**. Cadastre o administrador na tela de configuração. Não existe senha padrão. A configuração só aceita essa chave enquanto não houver usuários.

A pasta de dados padrão continua no perfil do usuário. Os bancos existentes não são movidos. Para alternar a pasta, interrompa primeiro o serviço. Fechar a janela ou ESC recolhe a administração; Sair encerra o serviço que pertence à estação. Isso não para contêineres remotos.

Na aba **Servidor Docker**, informe a URL HTTPS do portal, a URL do agente (por exemplo, `https://seu-dominio/agent`) e a credencial fornecida pelo administrador da instalação. A credencial é armazenada com DPAPI, vinculada ao usuário Windows; não aparece em `remote.json`. A CA privada é opcional e deve ser selecionada quando a instalação usa certificado de infraestrutura interna. TLS não é desabilitado. Redirecionamentos do agente são recusados.

Selecione o serviço retornado pelo agente antes de executar comandos. A parada e o reinício pedem confirmação porque afetam os operadores conectados. As chamadas de rede rodam fora da thread da interface. Perda de conexão é exibida no histórico; resultado inconclusivo não é reaplicado automaticamente.

## Docker e HTTPS

As configurações de implantação ficam em `deploy/`. `compose.local.yaml` publica apenas em `127.0.0.1:8765`. `compose.yaml` usa proxy HTTPS, volume persistente e servidor sem porta publicada diretamente. O domínio real e a URL pública são parâmetros obrigatórios. Não há implantação automática em infraestrutura do usuário.

Para uma instalação administrada, preencha os parâmetros a partir de `example.env`, selecione uma versão ou digest já testado e execute o Compose no host Docker. Esses são procedimentos do administrador da infraestrutura; o operador Windows usa somente a interface gráfica.

```bash
docker compose --env-file deploy/installation.env -f deploy/compose.yaml --profile management up -d
```

O arquivo de instalação com valores reais não deve ser versionado. O proxy requer DNS/certificado compatíveis com o domínio informado. Em infraestrutura interna, use a terminação TLS aprovada e a CA correspondente na estação. O teste em CI usa dados sintéticos e não configura DNS, SMTP ou certificados reais.

O administrador do host recupera a chave de primeiro acesso em `/data/setup.token` do serviço api e a credencial do agente em `/agent-data/agent.token` do serviço agent. Entregue-as por um canal privado; não coloque em logs, prints públicos, argumentos de processos ou documentos do repositório. As chaves de cifragem ficam junto da instalação em `/data/master.key` (ou arquivo indicado por `ESCRITURA_KEY_FILE`). Backup de identidade precisa preservar essa chave. Perder a chave impede a recuperação dos segredos cifrados.

O agente tem acesso privilegiado ao socket Docker. Por isso é serviço separado, opcional, com credencial administrativa própria e sem montagem dos dados contábeis. A API de negócio e o navegador não recebem esse socket. A lista de serviços exige simultaneamente `io.escritura.installation` e `io.escritura.managed=true`; os mesmos rótulos são reconferidos em cada comando. Não existem rotas para shell, exec, remoção de volumes, alteração de imagens ou comandos arbitrários.

## Permissões e isolamento

Administrador tem acesso global às empresas da instalação. Demais usuários têm vínculos explícitos por empresa. O backend verifica os vínculos a cada requisição, independentemente do menu. Clientes não acessam rotas internas de contabilização, cadastro de usuários ou parâmetros globais. Alterar perfil, senha, ativação ou empresas revoga sessões anteriores. As páginas de gestão global de usuários e perfis exigem administrador; permissões específicas de trabalho permitem separar preparação e revisão.

As sessões têm oito horas de duração máxima e trinta minutos de inatividade. Cookies são HttpOnly e SameSite Strict; Secure é usado no endereço HTTPS. Requisições de alteração exigem Origin permitido e token CSRF derivado da sessão. Senhas usam PBKDF2-HMAC-SHA256 com salt exclusivo e 600 mil iterações. TOTP e segredos SMTP são cifrados com Fernet. Os códigos de recuperação e tokens consumíveis são persistidos como hashes.

SMTP usa TLS direto ou STARTTLS com validação de certificado. A fila preserva tentativas, limpa o conteúdo após o envio e limita as tentativas. Uma interrupção depois da aceitação SMTP pode resultar em reenvio; não existe garantia de entrega exatamente uma vez. O Message-ID estável facilita correlação. Logs não registram senha, token ou corpo de e-mail.

## Verificação e preservação

A suíte cobre escopo de empresa, recusa de operações de cliente, revogação, último administrador, TOTP/replay/códigos, reset, fila, agente com comandos restritos/idempotência e DPAPI no Windows. O smoke executa o processo real, configura conta sintética, autentica, cadastra empresa, verifica CSRF/origin, encerra sessão e repete após reiniciar. O teste de navegador cobre primeiro acesso, login, layout, cadastro, área de trabalho, cliente e viewport móvel.

A compatibilidade com documentos já existentes é sustentada pela suíte original do motor, mantida sem alterações. Não houve substituição dos parsers, regras tributárias, precisão monetária ou fechamento. Os perfis fiscais e integrações externas continuam sujeitos à especificação e homologação do destino; portar regras não comprovadas das referências não faz parte da infraestrutura de autenticação.
