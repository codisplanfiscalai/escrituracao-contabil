# Instalação e distribuição

O fluxo atual está descrito em [Desenvolvimento, versões e distribuição](fluxo-desenvolvimento.md). Builds incluem a mesma lógica funcional de src/, sem banco real ou credenciais. Canal estável não implica homologação fiscal.

## Windows gráfico

Extraia todo o ZIP x86 ou x64 e abra `EscrituracaoContabil.exe`. Mantenha `_internal` ao lado do executável. A interface nativa permite iniciar, interromper e reiniciar o serviço local, abrir o portal, configurar caminho do banco e porta, consultar status e histórico operacional. Não abre console e não depende de comandos para operação normal.

O ícone na área de notificação oferece os mesmos controles. Fechar a janela ou pressionar ESC recolhe a administração, mantendo o serviço ativo. Use **Sair do Escritura** para encerrar serviço e aplicativo. Se a área de notificação não estiver disponível, a janela fica minimizada na barra de tarefas. A instância única por arquivo de dados impede dois administradores locais sobre o mesmo banco.

Dados padrão: `%LOCALAPPDATA%\EscrituracaoContabil\accounting.sqlite3`. A configuração gráfica fica em desktop.json na mesma pasta. Trocar o caminho não copia nem migra o banco. Interrompa o serviço antes de salvar a configuração e faça backup antes de atualizar. O histórico exibido na janela é operacional e temporário; a auditoria fiscal/contábil persistente continua no banco.

Esta versão administra o serviço local de compatibilidade. A conexão administrativa a serviços Docker remotos é parte da próxima etapa de arquitetura e não está habilitada por esta janela. O serviço local continua em 127.0.0.1; não houve exposição de porta em rede.

PyInstaller usa `--windowed`. O build valida o subsystem PE GUI, arquitetura e ícones. O teste nativo abre a janela, cria a infraestrutura do tray, confere ausência de console no EXE, inicia o serviço, grava dados fictícios, encerra e reinicia. A disponibilidade visual do ícone depende da sessão do Windows; execução em runner não substitui homologação em todas as edições do sistema. EXEs ainda não possuem assinatura Authenticode.

## Identidade Escritura e ícones reproduzíveis

`src/web/assets/icon.svg` e `symbol.svg` são os originais fornecidos. O gerador
não redesenha nem altera esses SVGs. Ele produz `icon-{size}.png` nos tamanhos
16, 24, 32, 48, 64, 128, 256 e 512, `symbol-512.png` e `icon.ico` com sete imagens
RGBA de 16 a 256 pixels. O ICO usa PNGs internos, suportados no Windows moderno;
a matriz efetivamente testada continua sendo a dos runners indicados acima.

O rasterizador é `@resvg/resvg-wasm@2.6.2`, com integridade SHA-512 no
`packaging/icon-tools/package-lock.json`, sem dependências transitivas. Node.js
24.22.2 e seu npm 11.19.1 estão fixados. WASM evita depender de Cairo, fontes ou
bibliotecas gráficas do sistema; os originais são geométricos e não usam fontes
nem recursos externos. Essas ferramentas são exclusivas de build.

```bash
npm ci --prefix packaging/icon-tools --ignore-scripts --no-audit --no-fund
node packaging/icon-tools/generate.mjs
node packaging/icon-tools/generate.mjs --check
python packaging/verify_icons.py
```

`--check` renderiza novamente e exige igualdade byte a byte com os arquivos
versionados. `icons-manifest.json` registra hashes dos SVGs, PNGs, ICO, WASM,
gerador e lockfile; arquivos de texto usam LF canônico para não depender de
`autocrlf`. Não contém timestamps. Esse escopo de reprodução se limita aos ícones;
o executável inteiro ainda não tem garantia de identidade bit a bit.

Cada build Windows confere dimensões, CRCs PNG e hashes; usa `--icon icon.ico`
e compara os sete recursos `RT_ICON`/`RT_GROUP_ICON` do EXE com o ICO fornecido.
Os assets HTTP são empacotados por nomes explícitos, assim como no contêiner.
O smoke solicita também SVGs, todos os PNGs de ícone e `/favicon.ico`.
Após os dois uploads, outro job baixa os artefatos no próprio Actions e verifica
novamente os ZIPs completos, manifesto, SHA fonte, PE Machine, ICO e hashes dos
assets. Assim a verificação da distribuição não depende do acesso de download
do executor local. Os logs distinguem essa verificação dos checks durante build.

Fontes: [resvg WASM](https://github.com/yisibl/resvg-js/tree/main/wasm),
[Node.js 24.22.2](https://nodejs.org/dist/v24.22.2/),
[PyInstaller — opções de ícone](https://pyinstaller.org/en/stable/usage.html).

## Contêiner

O Dockerfile preserva a base fixada por digest, execução sem privilégios e teste isolado. A imagem atual ainda é uma fundação local, com listener loopback no contêiner: publicar o pacote no GHCR não cria um serviço web compartilhado. Não publicar portas desta imagem como atalho para habilitar uso multiusuário.

O pipeline testa o alvo test, cria final, executa smoke com rede desabilitada, filesystem somente leitura e diretórios temporários privados; salva a imagem exata para publicação posterior. Manifestos e hashes acompanham cada entrega.

## Verificação e atualização

Confira SHA256SUMS.txt e release.json, preserve o diretório inteiro do pacote e faça backup privado do SQLite. Releases imutáveis mantêm SHA fonte, versão SemVer e digest da imagem. Migrações de banco são independentes de rollback do executável.

Veja os comandos de build, manutenção, prerelease contínua, release estável e recuperação em [fluxo-desenvolvimento.md](fluxo-desenvolvimento.md).
