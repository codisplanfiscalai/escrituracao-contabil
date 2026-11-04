# Importação em lote e cadastros de origem

Esta frente recebe e organiza fontes para conferência. Não calcula tributos, não valida escrituração integral, não transmite arquivos e não homologa integração Prosoft. As funções anteriores de importação individual continuam disponíveis.

## Operação

Em **Documentos**, selecione empresa e período, escolha vários arquivos XML, TXT/SPED, ZIP, 7z ou RAR e envie o lote. A extensão identifica o tipo. O portal do cliente usa o mesmo serviço, limitado às empresas autorizadas. O SPED permanece em modo de recebimento por padrão; a leitura EFD-ICMS/IPI 020 parcial de 2026 precisa ser selecionada explicitamente pelo operador.

Cada lote registra operador, empresa, período, horário, identificador de tentativa e hash do manifesto. Cada entrada registra nome, posição, tipo, hash SHA-256, tamanho, situação, diagnóstico e vínculo ao arquivo normalizado. Arquivos internos registram também a entrada do pacote de origem. Documentos repetidos continuam submetidos às regras existentes de identidade e divergência; o lote não cria documentos fiscais independentes para cada repetição.

Os bytes recebidos são mantidos em SQLite, inclusive pacotes rejeitados, arquivos vazios e fontes sem normalização. Para arquivos internos aceitos, o original fica no armazenamento de arquivos existente; entradas não extraídas permanecem recuperáveis no pacote original. O botão de download recupera os bytes sem gerar novamente o documento. O servidor usa um nome de download seguro e nunca aceita um caminho para acessar o disco.

Repetir o mesmo identificador de tentativa com os mesmos arquivos, ordem, nomes, período e perfil devolve o resultado existente. Reutilizá-lo com outro conteúdo é recusado. Uma falha de banco desfaz a transação do lote; não deixa importações parcialmente confirmadas. Diagnósticos de conteúdo são resultados individuais e não interrompem os demais arquivos. Ao atingir um limite do pacote, ele pode ser recusado integralmente antes da importação dos membros. Outros arquivos avulsos/pacotes do lote continuam sendo tratados.

## Limites aplicados

| Controle | Limite/comportamento |
| --- | --- |
| Requisição HTTP | 15 MiB de JSON com base64; a interface limita a soma dos arquivos enviados a 10 MiB |
| Arquivo ou pacote recebido | 10 MiB por entrada |
| Serviço de lote chamado diretamente | Até 100 MiB de originais, mantendo 10 MiB por entrada |
| Quantidade | Até 500 arquivos/pacotes no lote; até 500 entradas por pacote, incluindo diretórios no controle do leitor |
| Arquivo interno | Até 10 MiB |
| Expansão | Até 100 MiB por lote e pacote; até 100 vezes o tamanho comprimido do pacote; ZIP também confere a razão por membro |
| Tempo | Orçamento de 60 segundos por lote, conferido entre arquivos; até 20 segundos por processo leitor 7z/RAR, limitado pelo tempo restante |
| Processo nativo no POSIX | Limites de CPU, memória virtual de 768 MiB e saída de 150 MiB; encerramento pelo processo pai ao exceder o prazo |
| Caminhos e tipos internos | Recusa caminhos absolutos, unidades Windows, `..`, caracteres de controle, links e entradas especiais |
| Pacotes adicionais | Não há extração recursiva; pacotes aninhados são preservados e rejeitados para importação automática |
| Recursos não contemplados | Criptografia/senhas, volumes múltiplos e diretório ZIP64 não fazem parte deste perfil |

O leitor ZIP confere e percorre o diretório central antes de criar objetos dos membros, e confere tamanhos/CRC durante a leitura. Nenhum nome de membro é usado para criar arquivos no disco. O leitor 7z/RAR envia os dados por memória para libarchive em um processo Python separado; sua saída usa um arquivo temporário privado, sem nomes fornecidos pelo pacote. Quando um pacote nativo é recusado, membros parcialmente lidos não são importados.

## Disponibilidade dos formatos

- **ZIP:** leitor da biblioteca padrão; testado com compressão DEFLATE e modo armazenado.
- **7z:** leitor opcional libarchive, testado neste ambiente Linux com pacote 7z sintético criado por libarchive. Não representa homologação de todos os métodos de compressão, arquivos sólidos ou variantes.
- **RAR:** leitor opcional libarchive, testado neste ambiente Linux com RAR4 sintético em modo armazenado. RAR comprimido e RAR5 não foram homologados nesta entrega.
- **Executável Windows congelado:** 7z/RAR são recusados explicitamente, pois o processo isolado não está empacotado. ZIP e arquivos avulsos permanecem disponíveis. Esta frente não altera a distribuição nem instala leitores no equipamento do usuário.

Ausência de libarchive, corrupção, método incompatível, criptografia ou limite de segurança produzem rejeição explícita com o pacote original preservado. Não se declara suporte apenas pela extensão ou pela presença de uma biblioteca.

## Leitores e cadastros

XML mantém o perfil de cabeçalho/cobrança NF-e/NFC-e 4.00 e a leitura segura que recusa DTD e entidades. O cadastro observa somente `cProd`, `xProd`, `NCM`, `uCom`, `cEAN` e `CEST` presentes em `det/prod`. Não calcula valores, não atribui NCM nem presume enquadramento fiscal. Produtos XML usam a identidade **empresa + CNPJ emitente + código de origem**.

A leitura parcial SPED preserva as linhas e acrescenta observação dos registros **0150 e 0200**, somente com cabeçalho compatível e dentro do bloco 0 aberto. O registro 0150 exige CPF/CNPJ presente para formar cadastro; participantes estrangeiros/sem identificador permanecem como observações, sem documento fictício nem papel comercial inferido. Produtos 0200 usam **empresa + espaço de códigos SPED + código de origem**. Códigos XML e SPED não são unidos automaticamente.

A primeira representação do produto é preservada. Novas descrições, unidades ou classificações divergentes ficam pendentes; o operador pode escolher uma observação de origem, informar motivo e confirmar a revisão pela tela. A revisão exige a versão vigente, registra o antes/depois e mantém as observações. Sem código não há identidade fabricada; a observação e o aviso no arquivo continuam registrados. Sem descrição o cadastro fica pendente. A revisão não verifica a validade tributária dos campos.

Para arquivos antigos já analisados, selecione **Cadastros de origem · terceiros e produtos · v1** em “Analisar arquivo já salvo”. Esse perfil lê o original e registra análise adicional, preservando as análises fiscais anteriores. A migração aditiva do banco para versão 7 cria as novas tabelas sem reinterpretar automaticamente os documentos históricos.

## Contrato das APIs

- `POST /api/import-batches`: `company_id`, `period_id`, `request_key`, `inputs: [{filename, content_base64, kind?}]`, `sped_profile?`.
- `GET /api/import-batches?company_id=...&period_id=...`: lotes e resultados individuais, sem bytes dos originais.
- `GET /api/import-original?company_id=...&item_id=...`: bytes da origem, com escopo de empresa.
- `GET /api/products?company_id=...`: produtos e observações.
- `POST /api/product-review`: empresa, produto, versão, observação e motivo; exige permissão de revisão.
- O portal do cliente permite `import-batches` e `import-original` sob `/api/v1/client/`, com sessão, CSRF nas gravações e escopo da empresa. Não concede acesso à revisão dos produtos.

Falhas de envelope (JSON/base64 inválido, empresa/período incompatível, nomes externos com caminho ou limites de envio) são recusadas antes da criação do lote. Somente conteúdo efetivamente recebido e admitido no envelope é armazenado. Nenhum dado real foi incluído nos testes ou no repositório.

## Evidências

As suítes novas usam arquivos gerados em memória e cobrem lotes mistos, originais byte a byte, rastreabilidade, duplicidade, retomada por chave, isolamento, transações, entradas inseguras, ZIP bomb/CRC/diretório forjado, links, criptografia, tempo, indisponibilidade do leitor, 7z e RAR4 armazenado. Testes de HTTP verificam autorização, CSRF e downloads; os cadastros têm testes de conflitos, revisão, ausência de código, análise separada de originais e migração de banco.

A verificação em Chromium confirmou lote misto, erro individual, revisão de produto divergente, download idêntico ao pacote recebido e persistência após recarga, sem erro JavaScript. Os resultados finais dos comandos de teste e cobertura são informados junto ao commit; execução de CI, Windows x86/x64 e imagem publicada não foi realizada nesta frente.

Para repetir a verificação visual em ambiente de desenvolvimento com Playwright e Chromium instalados: `python scripts/smoke_import_ui.py`. O script cria somente bancos e documentos sintéticos temporários, abre servidores em loopback e os encerra ao terminar.

Verificação local desta implementação:

- `python scripts/build.py check`: 205 testes da aplicação; 18 de empacotamento (um pulado por exigir DPAPI/Windows); 18 de ferramentas de entrega; compilação Python, sintaxe JavaScript, template Vue, matemática decimal, ícones e smoke do portal aprovados.
- `python scripts/smoke_import_ui.py`: fluxos local e do cliente aprovados em Chromium, com documentos sintéticos e bancos temporários.
- `actionlint` 1.7.7: workflows aprovados na verificação local. Não houve execução remota de CI.
- Cobertura de linhas com `coverage`, nas suítes específicas (23 testes): `batch_import.py` 94%, `archive_reader.py` 83%, `product_catalog.py` 94%; total dos três módulos novos 89%. O corpo de inicialização do processo filho não é instrumentado por essa medição, embora sua execução seja exercitada pelos testes funcionais 7z/RAR.
