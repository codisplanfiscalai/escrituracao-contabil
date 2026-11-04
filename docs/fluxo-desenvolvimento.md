# Desenvolvimento, versões e distribuição

## Branches e promoção

`main` contém a linha estável de distribuição. `develop` integra funcionalidades e produz pré-releases. Branches `feature/*`, `feat/*`, `fix/*`, `ci/*`, `chore/*` e `hotfix/*` partem de develop e retornam por PR. Main recebe PR de develop do mesmo repositório, com título `release(patch|minor|major): descrição`.

Estável significa canal de distribuição: não significa homologação fiscal do produto. Não há deploy em produção ou merge automático. Cada PR executa testes e builds sem permissão de publicação. A preparação de release abre ou atualiza uma PR; quem integra em main aciona automaticamente a release estável.

| Evento | Resultado |
|---|---|
| PR para develop/main | Política de branch, testes Linux, testes das ferramentas, lint, Windows gráfico x86/x64 e Docker; sem publicação |
| Push em develop | Testes + builds; release GitHub marcada como prerelease; imagem versionada e alias develop |
| Push em main | Testes + builds; release estável; imagem versionada, aliases latest, MAJOR.MINOR e MAJOR |
| Reexecução da publicação | Confere release completa existente; não substitui tags ou artefatos publicados |
| PR encerrada | Remove somente caches próprios associados à referência exata daquela PR |
| Manutenção semanal | Remove caches próprios antigos, preservando o mais recente por branch/plataforma |

A bootstrap desta estrutura preserva a revisão funcional existente em develop. O histórico anterior permanece disponível. Não copiar bancos ou arquivos fiscais para o Git.

## SemVer

`VERSION` é a fonte central, conferida contra `pyproject.toml`. Tags são numéricas, sem prefixo: `0.2.1`. Em develop, a CI deriva `0.2.1-dev.RUN.ATTEMPT`; exemplo: `0.2.1-dev.42.1`. A versão estável correspondente supera a pré-release em ordenação SemVer. O número identifica a execução do workflow develop; o manifesto registra também o SHA exato.

- PATCH: correções compatíveis e ajustes de distribuição.
- MINOR: funcionalidades compatíveis.
- MAJOR: quebra de contrato público ou compatibilidade.
- Migração de esquema exige plano de backup/compatibilidade independentemente do número SemVer.

Antes do próximo ciclo, elevar VERSION/pyproject para uma versão ainda não publicada. A publicação nunca reutiliza uma versão estável para outro commit. As versões das ferramentas de build permanecem fixadas separadamente; não confundir versão da aplicação com Python, Node ou PyInstaller.

```bash
python scripts/ci/version.py check
python scripts/ci/version.py bump patch
python scripts/ci/version.py set 0.3.0
python scripts/ci/flow.py start feature/minha-alteracao --apply
python scripts/ci/flow.py prepare-release --bump patch --apply
python scripts/ci/flow.py sync --apply
```

`prepare-release` exige develop limpa e atualizada, calcula a versão a partir de main, sincroniza os dois arquivos de versão, faz commit/push somente se necessário e abre/atualiza a PR develop → main. Atualize CHANGELOG antes de executá-lo. Sem `--apply`, mostra o plano. Não executa merge.

## Scripts de build

Estes comandos são ferramentas de desenvolvimento. O usuário final abre o aplicativo Windows gráfico; não precisa de terminal.

```bash
python scripts/build.py check
python scripts/build.py container
python scripts/build.py container --no-cache
bash scripts/build-all.sh
```

No Windows, com Python 3.13.17 da arquitetura correta, Node 24.22.2 e Docker disponível para a etapa de contêiner:

```powershell
python scripts/build.py windows --arch x64 --install-build-tools
.\scripts\build-all.ps1
.\scripts\build-all.ps1 -PythonX86 C:\Python313-32\python.exe -PythonX64 C:\Python313\python.exe
```

O script PowerShell completo produz x86, x64 e contêiner. No Linux, o script completo executa checks e Docker; a CI Windows produz os binários nativos. Não há compilação Windows cruzada disfarçada. Falta de ferramenta ou teste reprovado interrompe o build. Saídas anteriores não são removidas implicitamente: use a limpeza local explícita antes de repetir.

## Artefatos e GHCR

A etapa de build gera ZIPs Windows, manifestos individuais, SHA-256, `container.tar.gz` e manifesto do contêiner. A publicação baixa os artefatos desta mesma execução e confere SHA fonte, arquitetura, subsystem GUI, ícones, tamanhos e hashes. A imagem salva é carregada e publicada sem reconstrução. `release.json` relaciona fonte, versão, canal, digest GHCR e arquivos; `SHA256SUMS.txt` permite conferência externa. A release também inclui um ZIP do código versionado.

Namespace: `ghcr.io/codisplanfiscalai/escrituracao-contabil`. As releases respeitam a visibilidade atual do repositório, sem alterá-la; em repositório público, os anexos da release também são públicos. O pacote GHCR permanece privado e sua visibilidade é conferida antes/depois do push. A identidade usa o token efêmero da execução. Forks/PRs não recebem permissão de publicação; não há PAT embutido.

Uma release é montada como rascunho, recebe os arquivos e tem os bytes baixados e conferidos antes de ser publicada. Repetição de release concluída verifica os artefatos existentes. Se a tag ou imagem versionada pertence a outro conteúdo, a execução falha. Rascunhos incompletos podem ser retomados. Falha depois do push não desfaz a imagem: consultar a execução e o manifesto antes de repetir.

Os aliases avançam apenas quando o SHA ainda é a ponta da branch e uma versão estável superior não foi publicada. Uma execução antiga não rebaixa latest/develop. Alterações GHCR/releases são serializadas no job de publicação.

## Cache e limpeza

```bash
python scripts/ci/cleanup.py local
python scripts/ci/cleanup.py local --apply
python scripts/ci/cleanup.py cache --days 14
python scripts/ci/cleanup.py cache --days 14 --apply
```

Local: somente build/dist/artifacts e caches de ferramentas/bytecode em áreas conhecidas. Recusa links simbólicos, destinos fora do projeto e diretórios com arquivos versionados. Não seleciona data, private, SQLite, XML, backups ou documentos do usuário.

GitHub: somente chaves com prefixo `escritura-`. Paginação completa; PR deve estar encerrada e a referência precisa coincidir exatamente. A rotina periódica mantém o cache mais recente de cada branch/plataforma e exige antiguidade. Não exclui releases, imagens, tags, volumes Docker ou artefatos de negócio. Artefatos temporários de Actions têm retenção de 14 dias; os anexos publicados em releases seguem o ciclo de vida da release.

## Proteções administrativas

```bash
python scripts/ci/flow.py bootstrap --protect
python scripts/ci/flow.py bootstrap --protect --apply
```

Usa a autenticação existente do gh e exige permissão administrativa para configurar proteção. Cria develop apenas se ausente. Preserva proteções já existentes. Configura PR obrigatório, checks, bloqueio de exclusão/force-push e conversas resolvidas. O número mínimo de revisores é zero para permitir fluxo de mantenedor único; aumentar conforme a equipe. A presença do script não significa que as regras foram aplicadas no servidor.

Checks recomendados: Branch policy, Tests Python 3.10/3.12/3.13, Workflow lint e Build gate. É necessário que o GitHub permita Actions e escrita de pacotes para os jobs de distribuição. Nenhuma configuração é contornada pelo pipeline.

## Recuperação

1. Falha em build: corrigir na branch de trabalho e integrar em develop; não publicar manualmente arquivos sem manifesto.
2. Falha na publicação: conferir release em rascunho, tag, imagem e SHA; executar novamente os jobs com falha. Conteúdo divergente exige nova versão.
3. Release estável com defeito: restaurar a implantação para o digest anterior, preservando o banco; produzir hotfix com novo patch e nova PR. Nunca mover a tag antiga.
4. Banco migrado: rollback do EXE/imagem não faz downgrade de esquema. Recuperar somente backup compatível e previamente validado.
5. Produção: este fluxo distribui software; o workflow de homologação existente executa teste efêmero e não implanta serviço permanente.

Referências de operação: [eventos do GitHub Actions](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow), [API de caches](https://docs.github.com/en/rest/actions/cache), [Container Registry](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry). O fluxo encadeia jobs reutilizáveis diretamente e não depende de uma tag criada por GITHUB_TOKEN disparar outro workflow.
