# Distribuição do protótipo local

Os pacotes Windows x86 e x64 contêm a **mesma aplicação** de `src/`, incluindo
o frontend vanilla e o servidor HTTP Python. O runtime da aplicação continua
somente stdlib. PyInstaller e suas dependências são ferramentas de build.
Empacotamento e testes técnicos não tornam a aplicação completa nem homologada
para o Prosoft, e não validam resultados fiscais com dados reais.

## Windows

O workflow `Windows distribution` roda em pushes de `main`/`feat/**`, pull
requests e execução manual. Cada arquitetura usa Python **3.13.17** na arquitetura
correspondente e PyInstaller **6.22.3**. O build exige Windows; não existe
compilação cruzada de Linux para Windows neste fluxo. No PR, o pacote é criado
do HEAD exato proposto e esse SHA é registrado no manifesto. Os testes Linux
de PR continuam verificando o merge temporário produzido pelo GitHub. O job de
Windows permanece sem segredos, sem publicação e com token somente de leitura.
O runner `windows-2022` é x64; o smoke x86 usa compatibilidade de 32 bits desse
Windows. Isso não
equivale a testar todas as versões/edições do Windows nem um SO Windows x86.

Cada job descobre toda a suíte de testes, instala wheels fixadas por versão e
SHA-256 com `--require-hashes --only-binary=:all:`, gera o diretório do programa,
confere o cabeçalho PE (`0x14c` x86 / `0x8664` x64) e inicia o executável real.
O smoke verifica HTML/JS/CSS, token de sessão, proteção de origem, POST com empresa
fictícia, SQLite externo, encerramento, reinício e persistência. Nenhum dado real
é utilizado. Os artefatos ficam disponíveis por 14 dias na execução do Actions:

- ZIP com `EscrituracaoContabil.exe` e o diretório `_internal` necessário;
- manifesto JSON com commit fonte, Python, PyInstaller, arquitetura, tamanhos e
  SHA-256 de cada arquivo;
- arquivo `.sha256` do ZIP, conferido novamente antes de preparar o release.

Extraia o ZIP inteiro em uma pasta separada dos dados e execute
`EscrituracaoContabil.exe`. Abra o endereço `http://127.0.0.1:8765` informado no
console; `Ctrl+C` encerra a aplicação. Não execute diretamente dentro do ZIP nem
copie apenas o EXE. O banco padrão Windows fica em
`%LOCALAPPDATA%\EscrituracaoContabil\accounting.sqlite3`. É possível escolher outro
diretório privado **fora da instalação**, com `--database`, e outra porta com
`--port`. A pasta do executável não aceita o SQLite. O programa permanece
monousuário em loopback, sem autenticação de rede. Não utilize proxy público,
túnel ou encaminhamento de portas.

Build local no Windows, com o Python correto e uma venv:

```powershell
python -m venv .venv-build
.venv-build\Scripts\python -m pip install --only-binary=:all: --require-hashes -r packaging/requirements-build.txt
.venv-build\Scripts\python -m unittest discover -s tests -v
.venv-build\Scripts\python packaging/build_windows.py --arch x64
```

Para x86, crie a venv usando um interpretador x86 e passe `--arch x86`.
O script recusa arquitetura incorreta e um diretório `dist/<arch>` já existente;
remova somente a saída de build anterior ao repetir. Os arquivos gerados em
`build/`, `dist/` e `artifacts/` não são código-fonte para commit.

Os executáveis ainda não possuem assinatura Authenticode, instalador/MSI,
atualizador automático ou aprovação por antivírus/SmartScreen. Versões fixas e
manifestos permitem rastrear entradas e saídas; **não garantem build idêntico
bit a bit**. Imagens dos runners hospedados e metadados de ZIP/PE podem variar.
Assinatura exigiria processo e credencial próprios, não provisionados aqui.

## Imagem OCI e GHCR

O `Dockerfile` usa `python:3.13.17-slim-bookworm` fixado também no digest do índice
OCI `sha256:e32be0e55814a08977501ca863271d9bd02443710db8f2afaf8372e2c4508530`.
O digest foi obtido do registry oficial e conferido calculando SHA-256 do
manifesto em 2026-11-04. A imagem executa como UID/GID 10001; não instala pacotes
durante o build. O contexto tem allowlist explícita. O estágio `test` contém a
suíte; `final` contém o runtime e o smoke sintético, sem a suíte inteira.
Construir `final` isoladamente não executa o estágio `test`; os workflows
executam explicitamente os dois builds nessa ordem.

```bash
docker build --target test -t escrituracao-test .
docker build --target final -t escrituracao-local .
docker run --rm --network none --read-only --cap-drop ALL \
  --security-opt no-new-privileges \
  --tmpfs /tmp:rw,nosuid,nodev,mode=1777 \
  --entrypoint python escrituracao-local packaging/smoke_test.py
```

O HTTP permanece em `127.0.0.1` **dentro** do contêiner, sem `EXPOSE`, `-p`, rede
host ou mudança de bind. Portanto, essa imagem é uma unidade de execução e
homologação técnica isolada; ela não entrega a UI ao navegador do host. Use o
EXE ou Python nativo para trabalho interativo local. O fluxo não transforma o
servidor em serviço público ou multiusuário. O smoke usa banco temporário privado
e o remove ao terminar. Uma execução persistente isolada exige volume privado
em `/data`, acessível somente ao operador/UID definido; não é implantada por
estes workflows. Docker não é isolamento entre operadores do mesmo host.

O workflow de contêiner constrói/testa em pushes/PRs. Só publica no GHCR por
`workflow_dispatch`, com `publish=true`, na branch `main`, após o ambiente
`package-review`. Usa somente `GITHUB_TOKEN` efêmero com `packages: write` nesse
job; não cria PAT. Faz login depois dos testes, publica a tag `sha-<commit>` e
registra o digest. A tag contém o commit por convenção; consumir sempre o digest
é a garantia contra substituição de tags. Não há tag `latest` ou push automático
de PR. Pacote novo deve permanecer privado conforme a política do repositório;
nenhuma visibilidade é alterada pelo workflow.

## Release e deployment com aprovação

Antes do primeiro uso, o administrador deve configurar os ambientes
`release-review`, `package-review` e `homologation` com revisores obrigatórios,
restrição à branch `main` e bloqueio de autoaprovação, conforme suporte do plano
GitHub. **Declarar `environment:` no YAML não configura essas proteções.**
Também deve proteger `main` com revisão e checks de CI; isso não é alterado
automaticamente. Sem essa configuração, não considere o gate humano efetivo.

`Manual draft prerelease` só aceita execução em `main` com uma tag existente
`vX.Y.Z`, contida no histórico de `origin/main`, correspondente à versão do
`pyproject.toml`. Primeiro valida os metadados sem executar código da tag, depois
reconstrói/testa ambas as arquiteturas no SHA resolvido com permissão de leitura.
O job com `contents: write` verifica os manifestos desse mesmo SHA e cria apenas
um **rascunho de prerelease**. Publicação final depende de ação humana separada.
Tags devem ser protegidas contra alteração; nada aqui faz merge ou cria tag.

`Manual ephemeral homologation deployment` recebe o digest de uma imagem já
aprovada no GHCR do próprio repositório. Após aprovação de `homologation`, obtém
a imagem com `packages: read`, executa o smoke em runner descartável, sem rede,
com filesystem somente leitura e dados temporários, e descarta a instância.
Esse é um deployment técnico **efêmero**. Não provisiona servidor permanente,
domínio, certificado, serviço público, ambiente de produção ou dados reais.

Workflows manuais novos ficam disponíveis no GitHub após chegar à branch padrão;
os builds Windows/contêiner já podem ser avaliados pelo push/PR desta proposta.
Nenhum release, pacote GHCR ou deployment foi publicado pela criação dos arquivos.

## Manutenção e evidências

Atualizações de Python, imagem, Actions e dependências devem ser PRs revisados,
com consulta à origem oficial, atualização dos hashes e repetição dos dois builds
Windows e do teste da imagem. `packaging/dependency-sources.json` registra as
wheels e hashes consultados no PyPI. Actions estão fixadas no SHA resolvido de
seus repositórios oficiais. A versão Python Windows foi conferida no manifesto
de `actions/python-versions` para x86 e x64. Não se usa `pip install latest`.

A execução local Linux valida código-fonte e contêiner. A confirmação de EXEs
Windows depende dos jobs Windows e seus artefatos, e deve ser registrada por
execução/commit; o YAML sozinho não é evidência de build bem-sucedido. Continuam
pendentes homologação Prosoft, dados/exemplos autorizados, instalador/assinatura,
matriz de sistemas operacionais e testes de uso com o operador.

Fontes oficiais: [PyInstaller](https://pyinstaller.org/en/stable/),
[Python para Actions](https://github.com/actions/python-versions/blob/main/versions-manifest.json),
[pacote PyInstaller no PyPI](https://pypi.org/project/pyinstaller/6.22.3/),
[Docker Official Python](https://github.com/docker-library/python),
[GHCR e GITHUB_TOKEN](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry),
[ambientes e proteção de deployment](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments).
