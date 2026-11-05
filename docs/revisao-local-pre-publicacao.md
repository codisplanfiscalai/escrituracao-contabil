# Revisão local anterior ao envio — 05/11/2026

Revisão da branch `refactor/fiscal-accounting-journey`, comparada com `develop` em `e85c425`. O usuário autorizou expressamente o envio ao repositório público e a abertura de PR após a conferência de dados/credenciais. Merge, release e implantação continuam fora da autorização.

## Correções verificadas

Seis cenários adicionais foram exercitados no domínio, sem reescrever lançamentos históricos:

- abertura declarada como zero exige valor zero explícito; abertura com saldos exige partidas na data de abertura;
- pagamento/recebimento e suas partidas usam a mesma data econômica; divergência impede conferência e efetivação;
- versão de competência rejeita booleanos, preservando o controle de concorrência;
- conferência e escrituração verificam o tamanho e o SHA-256 dos originais ativos vinculados ao documento; corrupção após a conferência impede materializar movimentos/títulos;
- o financeiro por competência verifica os hashes dos snapshots posteriores usados para reconstruir estornos/cancelamentos, sem confiar em conteúdo alterado;
- reimportação de original retirado logicamente continua bloqueada pelo mecanismo existente; o novo teste confirma que não há restauração silenciosa e que o recebimento permanece preservado.

As hipóteses foram reproduzidas antes da correção. A retirada lógica já estava protegida; o teste inicial desse caso precisou apenas reconhecer a mensagem existente. A nova validação não calcula ou altera tributos/contas, não corrige dados por suposição e não regrava snapshots fechados. A interface passa a preencher as datas das partidas ao abrir uma ficha de saldos iniciais.

## Contexto Docker

A lista anterior de inclusão de diretórios permitia arquivos adicionais sob `src/portal`, `src/web`, `src/server`, `config` e `packaging`. Uma sondagem somente com arquivos sintéticos demonstrou a inclusão de dez caminhos que deveriam ser recusados. Nenhum segredo real foi usado ou encontrado nessa sondagem.

O filtro foi restringido e atualizado para os recursos atuais. `scripts/check_container_context.py` usa o próprio Docker: constrói uma imagem `scratch` com contexto temporário, cria um contêiner sem executá-lo, exporta a lista de arquivos e remove os objetos temporários. Passou com **25 recursos necessários presentes e 20 sondas privadas/não aprovadas excluídas**. A verificação agora antecede todo `python scripts/build.py container`. Os padrões de exclusão do Git também foram ampliados para pacotes de referência, chaves, certificados privados e tokens.

## Dados e credenciais

Foram examinados os arquivos rastreados, as alterações e os blobs modificados nos commits locais posteriores a `e85c425`. Não foram encontrados bancos, XML/SPED/planilhas reais, anexos de referência, chaves privadas, tokens operacionais ou credenciais de produção. As atribuições literais de senha encontradas pertencem a testes temporários e exemplos reservados; os demais candidatos eram rótulos/expressões dos templates.

A revisão dos identificadores encontrou uma exceção importante ao rótulo “fictício”: o identificador do emitente no fixture antigo coincidia com o CNPJ público de uma instituição real, confirmado no [site oficial do Banco do Brasil](https://www.bb.com.br/site/pagina-modelo-legal/). Não eram documentos reais nem credenciais bancárias, mas o identificador era inadequado para o conjunto de testes. Ele e os identificadores relacionados foram substituídos por marcadores de dígitos repetidos, sem relaxar nenhuma validação de produção. As buscas desses valores antigos na árvore atual ficaram vazias.

**O histórico anterior da develop já contém esse identificador público e permanece inalterado.** A limpeza da árvore atual não representa eliminação de todo o histórico. Não foi feita reescrita de histórico público, movimentação de tags ou remoção de commits. Não há credencial operacional identificada que exija rotação; eventual política de purga desse identificador histórico exige decisão separada do proprietário.

Os logs e dados temporários dos testes, sondagens e builds permanecem fora do Git. A varredura é uma revisão delimitada, não uma garantia de inexistência de qualquer segredo possível. O contexto real do build é validado adicionalmente pela sondagem descrita acima.

## Evidência e limites

- 21 cenários do novo domínio, incluindo abertura válida com saldos, datas divergentes, corrupção e concorrência.
- Suíte da aplicação com os marcadores substituídos: 245 testes aprovados.
- Checks de distribuição, auxiliares de CI, navegação e builds são registrados separadamente do conteúdo fiscal. Resultado local não substitui o resultado dos jobs nativos Windows.
- As guias e os caminhos de navegação mantêm a [auditoria própria](auditoria-navegacao-guias.md).

Permanecem dependentes de evidência externa: acesso ao gerador SPED pela Library (download autorizado falhou na rede), leiautes Prosoft/SPED reais, conferência de uma cópia privada do banco do usuário e homologação operacional/tributária. Não se presume compatibilidade Prosoft/PVA, apuração tributária completa, geração de obrigação oficial, RAR5/comprimido ou conciliação bancária. A autorização de publicar código não altera esses limites nem autoriza merge/release.
