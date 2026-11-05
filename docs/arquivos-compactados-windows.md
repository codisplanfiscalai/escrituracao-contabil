# Leitura 7z/RAR no Windows

Base deste incremento: PR 6, commit `46cee74033564cabcb5bc27ac80f81cbdcc3d2dc`. O pacote Windows passa a incluir o leitor nativo por arquitetura e um modo interno do mesmo EXE gráfico para executá-lo isoladamente. ZIP continua no leitor da biblioteca padrão. Não é necessário instalar 7-Zip, WinRAR, Python ou obter DLLs no computador do operador.

## Dependências e licenças

As fontes são os releases dos projetos oficiais: [libarchive 3.8.11](https://github.com/libarchive/libarchive/releases/tag/v3.8.11) e [XZ Utils 5.8.4](https://github.com/tukaani-project/xz/releases/tag/v5.8.4). `packaging/native-archives.lock.json` fixa URLs, versões, SHA-256 dos tarballs e dos textos de licença. O build recusa fontes/cache ou textos de licença divergentes. Os tarballs foram baixados das origens oficiais e tiveram seus hashes e textos conferidos; não foi realizada validação independente de assinatura GPG.

`packaging/build_native_archives.py` compila liblzma estática e libarchive DLL com MSVC, separadamente para x86/x64. Ferramentas xz, scripts shell e leitores externos não são distribuídos. Recursos opcionais que acrescentariam outras bibliotecas são desabilitados. O build exige liblzma efetivamente ligada, verifica versão e arquitetura PE da DLL e recusa dependências DLL fora da lista de bibliotecas de sistema do Windows. A DLL é carregada por caminho absoluto no pacote; o EXE congelado ignora o override de desenvolvimento e não procura leitores no PATH/CWD.

A licença principal de libarchive permite redistribuição de binários sob BSD-2-Clause com preservação dos avisos. Seu `COPYING` também registra arquivos BSD-3-Clause, domínio público e arquivos com opção CC0/OpenSSL/Apache; os avisos completos dos arquivos C/H acompanham o pacote. A biblioteca liblzma de XZ usa 0BSD; os scripts GPL e o getopt LGPL das ferramentas XZ não entram neste build. Não são usados UnRAR, SDK proprietário RAR ou binários de terceiros não oficiais. O código de leitura RAR de libarchive mantém seus próprios avisos permissivos.

A distribuição inclui `_internal/src/native/archive.dll`, `native-manifest.json` e `licenses/` com os `COPYING`, `COPYING.0BSD` e avisos por arquivo de libarchive. Os manifestos registram fontes, hashes, arquitetura e imports da DLL. O verificador dos ZIPs baixados confere novamente a presença e os hashes das licenças, DLL e metadados, além da arquitetura e GUI do executável. A fixture sintética RAR5 é derivada do corpus oficial de libarchive; sua atribuição está em `archive-fixture-license.txt`.

## Fronteiras de segurança

- A aplicação cria um diretório temporário e nomes fixos `input`/`output`. Nomes de membros do arquivo nunca viram caminhos de extração no disco.
- O EXE inicia a si próprio no modo interno `--archive-worker`, antes de importar a aplicação ou abrir janela/tray. Esse modo não é um segundo aplicativo de console e não exige stdin/stdout no EXE `--windowed`.
- O filho aplica limites antes de carregar libarchive. No Windows, um Job Object limita a memória comprometida do processo a 768 MiB, CPU a 20 segundos e a quantidade de processos a um. A falta de suporte/permissão ao Job causa recusa; não há execução sem limites. No POSIX permanecem os limites de memória virtual, CPU e tamanho do arquivo de saída.
- O pai aplica prazo de parede de até 20 segundos, ou o orçamento restante do lote, e encerra o leitor ao ultrapassá-lo. Nenhuma saída parcial de um filho recusado é importada.
- Mantêm-se os limites de entrada de 10 MiB, 500 entradas, 10 MiB por membro, 100 MiB expandidos e razão total máxima de 100. A saída serializada fica limitada a 150 MiB. O pai valida novamente nomes, estrutura JSON/base64, quantidade e tamanhos antes de aceitar os bytes.
- Permanecem recusados caminhos absolutos/unidades/`..`, links, entradas especiais, criptografia/senhas e pacotes aninhados na importação automática. Não se acrescentam filtros externos, shell ou ferramenta de extração por caminho.

O Job Object controla recursos; não é uma sandbox de segurança nem remove os direitos de acesso do usuário. A biblioteca nativa continua sendo superfície de ataque e precisa de atualizações revisadas. No Windows o teto de saída é aplicado pelo protocolo/escritor e pelo pai; não há equivalente de quota de arquivo do Job. Os limites não garantem proteção contra exploração que obtenha execução arbitrária dentro do filho. Políticas adicionais de isolamento/antivírus da estação pertencem à implantação. Processos Windows com restrições incompatíveis a Jobs aninhados recusam a leitura explicitamente.

## Testes e formatos

O build nativo existente x86/x64 passa a compilar as fontes oficiais, rodar as suítes e empacotar a DLL/licenças. Além do smoke gráfico/tray/HTTP, `packaging/archive_smoke.py` chama o EXE congelado e exige bytes idênticos para 7z LZMA, RAR4 armazenado e RAR5 comprimido, com rejeição de pacote corrompido e caminho inseguro. O teste RAR5 compara uma sequência sintética de 300 inteiros de 32 bits, não documentos ou dados privados.

As suítes locais verificam o leitor real disponível, recusa por tempo, ausência de biblioteca, criptografia/links/caminhos, bombas ZIP, falha de limites do SO, saída inválida/excessiva do filho e preservação da importação em lote. A CI também verifica os ZIPs efetivamente baixados. Executar testes Linux não comprova o EXE; os resultados Windows x86/x64 devem ser relatados separadamente dos checks locais.

O perfil não homologa todos os formatos de 7z/RAR. Não se promete suporte a senhas, volumes múltiplos, todos os filtros BCJ/arquiteturas, arquivos sólidos ou recuperação de arquivos danificados. O build mínimo inclui LZMA/LZMA2 e o leitor RAR nativo; não inclui bibliotecas opcionais para Deflate/BZip2/Zstd em 7z. RAR4 comprimido exige caracterização adicional antes de ser declarado homologado. Uma variante não atendida é recusada, com o pacote original preservado e os demais arquivos do lote mantidos.

## Reconstrução e operação

```powershell
python scripts/build.py windows --arch x64 --install-build-tools
# Em Python x86 nativo:
python scripts/build.py windows --arch x86 --install-build-tools
```

Requer Windows, MSVC/Visual Studio 2022, CMake, Python da arquitetura escolhida, Node/npm e acesso inicial às fontes oficiais e dependências fixadas. O programa pronto funciona offline. O build ainda depende dos runners/toolchain do provedor e não é hermético nem garantido bit a bit. As novas fontes/DLLs não foram publicadas no GHCR; retenção própria/espelhamento depende de autorização e trabalho específico.

O suporte do Windows não instala libarchive no Docker slim. Nesse ambiente a ausência do leitor continua uma recusa explícita, preservando a imagem e as dependências previamente aprovadas. Não há mudança nas regras fiscais/contábeis nem no banco por este incremento.
