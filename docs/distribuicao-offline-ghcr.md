# Distribuição offline, paridade e dependências GHCR

## Arquitetura efetiva

Windows e Docker executam `src.server.app.create_app` e a mesma fachada de domínio. O Windows inicia `PortalServer` em loopback pela janela nativa com tray; Docker inicia `src.server.runtime`. Ambos usam SQLite e armazenamento privado de originais. Não existem adaptadores PostgreSQL/Redis no produto atual: acrescentar contêineres desses serviços não traria persistência nem fila reais. A outbox SMTP já é persistida em SQLite. Não compartilhar o arquivo SQLite por SMB/NFS nem executar várias réplicas escritoras sobre o mesmo volume.

O servidor compartilhado tem API, Caddy HTTPS e agente administrativo opcional no perfil `management`. O agente exige configuração/autorização próprias, acessa o socket Docker e tem privilégios diferentes da API. Não entregar esse socket ao portal. GHCR distribui imagens; não hospeda a aplicação em execução.

## Paridade preservada

| Recurso existente | Windows local | Docker | Evidência/limite |
|---|---|---|---|
| Login, bootstrap, sessões, empresas e permissões | Portal local autenticado | Mesmo portal | `tests/server`, smoke de login/logout/CSRF |
| XML/SPED, conciliação, revisão e cobranças | Mesmos serviços de domínio | Mesmos serviços de domínio | Suíte sintética `tests/`; sem ampliar perfis fiscais |
| Planos, mapeamentos, partidas e evidências | Mesmos IDs, versões e invariantes | Mesmo código | Testes de domínio/HTTP e persistência |
| Ficha fiscal manual | Mesmas rotas e armazenamento | Mesmo código | Testes fiscal HTTP e domínio |
| Interface Vue e área de trabalho | Assets incluídos no pacote | Assets incluídos na imagem | Build verifica render; smoke solicita arquivos locais |
| Reinício e preservação dos dados | Dados fora do EXE | Volume `/data` | Smoke cria dados fictícios e reinicia |
| Janela e tray | Nativos do Windows | Não aplicável ao servidor | PE GUI/tray dependem da CI nativa x86/x64 |
| Controle de servidor pela janela | Agente remoto HTTPS | Agente isolado opcional | Exige conectividade e token do agente |
| SMTP/reset por e-mail | Requer servidor SMTP acessível | Idem | Não há promessa de entrega offline |

Paridade refere-se aos recursos já implementados. Não inclui geração Prosoft, validação fiscal integral ou novos tratamentos tributários. CBS/IBS continuam fora do cálculo. A matriz não representa homologação funcional de produção nem demonstra a equivalência com todos os recursos dos materiais de referência.

## Executar sem internet

**Windows:** transfira o ZIP completo da arquitetura correta, confira `SHA256SUMS.txt`, extraia e abra `EscrituracaoContabil.exe`. Não são necessários Python, Node, Docker ou downloads no computador do operador. `_internal`, bibliotecas e assets devem permanecer juntos. O portal usa navegador local, não CDN. Login e trabalho sobre dados locais funcionam sem internet. SMTP, controle remoto, novas versões e integrações externas exigem conectividade aos respectivos serviços. Fechar/ESC recolhe; Sair encerra o aplicativo e seu serviço local. Faça backup antes de atualizar; downgrade de EXE não desfaz migrações.

**Docker local:** instale previamente Docker Engine e Compose, transfira a imagem exportada pelo build, valide seu hash e carregue-a antes de desconectar. Para um build local 0.3.0:

```sh
docker load --input artifacts/container.tar.gz
ESCRITURA_IMAGE=escritura-build:0.3.0 docker compose -f deploy/compose.local.yaml up -d --pull never
```

Para um pacote de release, use a versão/tag exata de `container.manifest.json`. O `--pull never` evita consultas ao registry; a imagem completa já contém Python e wheels. O serviço fica em `127.0.0.1:8765`. Guarde o volume de dados e os segredos de identidade em backup privado; o arquivo da imagem não contém esses dados. O smoke da imagem final roda com `--network none`, filesystem somente leitura e dados temporários privados.

**Servidor HTTPS offline:** API e Caddy precisam estar carregados (`docker save`/`docker load`) antes da desconexão; o arquivo `container.tar.gz` sozinho contém somente a aplicação. Use `docker compose ... up -d --pull never`. Certificados e confiança dos clientes devem ser provisionados previamente. O Caddyfile padrão usa ACME público e requer DNS/CA acessíveis para emissão/renovação; não se deve prometer HTTPS público indefinidamente offline. A rede local entre clientes e servidor ainda é necessária.

## Inventário e retenção próprios

`packaging/container-images.lock.json` registra somente as dependências reais: Python 3.13.17 slim Bookworm e Caddy 2.10.2 Alpine. Os digests identificam os índices originais completos, incluindo plataformas e atestações. O aplicativo continua homologado tecnicamente apenas para a plataforma realmente construída; espelhar outros manifests não testa outras arquiteturas.

Destinos preparados:

- `ghcr.io/codisplanfiscalai/escrituracao-contabil-deps/python:<versão>-<prefixo-do-digest>`
- `ghcr.io/codisplanfiscalai/escrituracao-contabil-deps/caddy:<versão>-<prefixo-do-digest>`

Esses nomes são destinos planejados, não evidência de publicação. Nenhuma imagem foi publicada como parte desta alteração. Os defaults continuam usando upstream fixado por digest até o espelhamento ser autorizado, executado e verificado. Não há fallback automático de GHCR para Docker Hub.

Para revisar sem rede/escrita:

```sh
python scripts/ci/container_images.py plan
python scripts/ci/container_images.py env --source ghcr
```

Após autorização explícita de publicação, um operador com Skopeo e credencial GHCR com acesso aos pacotes pode executar `mirror --publish`, ou selecionar `mirror` no workflow manual **Dependency image inventory**, na branch `develop`. O workflow usa o environment `dependency-images`; configure seus revisores/proteções antes de utilizá-lo. O modo padrão é `plan`, sem credenciais ou escrita. Não há trigger por push, PR, release ou agendamento.

O espelhamento verifica o digest da origem, copia com `skopeo copy --all --preserve-digests` e confere o digest remoto. Versão existente com outros bytes é recusada; autenticação, indisponibilidade e erro genérico 404 não significam pacote ausente. Somente `manifest unknown` permite a primeira cópia. Preserve licenças/avisos e metadados upstream; não reconstrua a imagem para trocar sua identidade. Restrinja outros escritores: registries não oferecem aqui uma operação de criação de tag condicional/atômica. Configure acesso privado/público dos novos pacotes conforme o repositório; o script não altera visibilidade.

Depois da cópia e antes da ativação:

```sh
python scripts/ci/container_images.py verify --source ghcr
python scripts/build.py container --base-source ghcr
# No servidor, usando os mesmos parâmetros HTTPS do compose principal:
docker compose --env-file deploy/example.env -f deploy/compose.yaml -f deploy/compose.ghcr.yaml config --quiet
```

A composição adicional seleciona exclusivamente Caddy no GHCR. Para iniciar, informe sua imagem de aplicação aprovada por digest em `ESCRITURA_IMAGE`, seu domínio/URL e credencial GHCR quando os pacotes forem privados. O exemplo `:develop` é um canal móvel de desenvolvimento, não uma referência imutável de produção.

A CI normal continua em upstream até definir explicitamente a variável de repositório `ESCRITURA_BASE_SOURCE=ghcr`, depois do espelhamento verificado. O job aceita somente `upstream` ou `ghcr`, faz login com `packages:read` quando GHCR é selecionado e não tenta upstream em caso de erro. Autorize o repositório consumidor nos novos pacotes privados; PRs de forks sem acesso podem falhar nessa opção e precisam de política própria de CI. Não basta criar os pacotes. A publicação existente da aplicação ganha smoke do digest baixado do registro antes de promover aliases/release. A validação desse caminho exige uma futura publicação autorizada; não foi executada nesta tarefa.

Imagens de dependências não entram na limpeza de caches do Actions. Preserve versões/digests referenciados por builds ou releases e mantenha exportações em armazenamento próprio com hashes e backups. Uma tag/digest fixada impede troca silenciosa, mas não impede que o provedor apague os bytes. A cópia GHCR só reduz essa dependência depois de todos os blobs serem transferidos e preservados; GHCR também precisa de controle de retenção e cópia externa.

## Limites da cadeia de build

Execução offline do pacote pronto e reconstrução offline são requisitos diferentes. O espelho de Python/Caddy não torna o build hermético. Permanecem externos:

- PyPI e arquivos de wheels de `requirements-server.txt` e `packaging/requirements-build.txt` (versões/hashes fixados; disponibilidade não garantida). PyInstaller e dependências nativas precisam de wheels por sistema/arquitetura.
- Instaladores CPython e Node/npm, runners Windows/Linux e ações GitHub (ações fixadas por commit; runners possuem toolchains atualizadas pelo provedor).
- Registro npm do rasterizador WASM (lockfile com integridade); Vue e os assets de runtime já estão no repositório.
- Docker/BuildKit, Compose, Skopeo e pacotes apt usados para instalar Skopeo no workflow manual. A versão apt é registrada no log, mas ainda não está fixada como toolchain arquivada.
- GitHub/GHCR, os fornecedores originais durante a primeira cópia e as autoridades de certificados para distribuição HTTPS pública.

Para reconstrução totalmente desconectada ainda faltam um wheelhouse Windows x86/x64/Linux com os hashes atuais, instaladores/toolchains e pacotes npm arquivados e validados, runners/compiladores controlados e teste de reconstrução sem rede. Não há garantia bit a bit do executável ou da imagem inteira. A reprodutibilidade dos ícones tem escopo próprio documentado.

Build em ambiente com CA de proxy pode usar `python scripts/build.py container --proxy-ca /caminho/ca-bundle.pem`; BuildKit monta a CA como secret temporário somente durante o pip, sem alterar a confiança TLS nem incorporar a CA nas camadas. Esse caminho exige BuildKit. Sem a opção, usa-se a confiança padrão.

## Verificações exigidas

`python scripts/build.py check`, `python scripts/build.py container`, `actionlint` e `docker compose ... config --quiet`. O build inclui testes Python na imagem e smoke offline do servidor real. A CI Windows existente deve confirmar GUI/tray, PE x86/x64 e os pacotes baixados; Linux não comprova esses binários. Antes de qualquer release, distinguir checks locais, checks nativos de CI, smoke do digest publicado e homologação de produção. Não publicar, promover, fazer merge ou implantar só por este documento existir.

Referências de implementação: [Skopeo copy](https://github.com/containers/skopeo/blob/main/docs/skopeo-copy.1.md), [Docker Compose up](https://docs.docker.com/reference/cli/docker/compose/up/), [BuildKit secrets](https://docs.docker.com/build/building/secrets/).
