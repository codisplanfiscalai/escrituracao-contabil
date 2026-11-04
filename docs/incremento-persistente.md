# Primeiro incremento persistente

## Fluxos antes da implementação

A documentação original permanece válida. Este incremento transforma cadastro e ingestão em um protótipo local executável, sem envio externo.

Navegação: Empresa → Períodos → Plano de contas → Mapeamentos → Importação → Documentos / Histórico.

1. Operador local cadastra empresa e códigos Prosoft; seleciona explicitamente o contexto da empresa.
2. Registra par de períodos: referência de parâmetros e movimentos. Não se copiam movimentos entre competências.
3. Importa plano JSON completo com contas sintéticas/analíticas; valida hierarquia antes de gravar tudo em uma transação.
4. Registra mapeamentos versionados com vigência e motivo. Revisões anteriores permanecem disponíveis.
5. Recebe XML NF-e 4.00 ou arquivo textual SPED. Preserva os bytes e hash no banco local, sem usar nome de upload como caminho.
6. XML NF-e: extrai identificação documental e fatura/parcelas originais, sem calcular tributos. Chave duplicada agrega proveniências somente se dados de controle concordarem; divergência gera pendência sem alterar documento existente.
7. SPED: preserva arquivo e contabiliza registros, ainda sem normalização documental nem validação integral de leiaute. Não alegar deduplicação XML × SPED implementada neste incremento.
8. Consulta documentos, pendências, origens e histórico. Nenhum lançamento ou arquivo Prosoft é produzido por esta etapa.

## Matriz de dados

Empresa possui períodos, planos versionados, arquivos e auditoria. Plano possui contas e mapeamentos imutáveis por versão. Período separa referência e movimento. Arquivo preserva bytes, hash, espécie e status. Documento canônico possui várias origens, payload fiscal original e status; identidade inclui empresa e chave documental. Fatura/parcelas permanecem dados extraídos, não lançamentos contábeis.

## Estados e permissões

Arquivo: recebido → validado ou pendente ou rejeitado; repetição exata retorna a importação anterior. Erros e conflitos são auditados. Documento: validado ou pendente; conflito não substitui silenciosamente dados. Mapeamento: rascunho, revisado, aprovado, inativo; cada alteração gera nova versão.

Este incremento é monousuário: o ator é operador-local. Não há login, papéis remotos ou compartilhamento. Servidor aceita apenas loopback e protege mutações com token de instância e checagem Host/Origin. Autenticação multiusuário é pendência, não capacidade entregue.

## Exclusão

Somente remoção lógica de arquivos, com prévia de dependências e confirmação explícita. Originais, documentos e auditoria não são purgados; arquivo excluído não pode ser reutilizado automaticamente. Purga definitiva permanece bloqueada até política de retenção aprovada. Não excluir empresas/planos vinculados neste incremento.

## Aceite do incremento

Persistência entre conexões; isolamento entre empresas; hierarquia válida; versionamento de plano/mapeamento; repetição idempotente por empresa/período/hash; XML inválido, DTD, entidade, competência divergente, chave ausente e dados conflitantes não provocam duplicação nem perda de original; remoção lógica preserva trilha. Testes usam somente amostras fictícias.

## Pendências explícitas

Contrato e homologação Prosoft; parsing/normalização SPED; reconciliação XML × SPED; importador dos formatos reais de plano; motor de lançamentos e partidas; exportadores; snapshot de processamentos fechados; controle de acesso por papéis; backup/restauração; política de retenção. CBS/IBS não serão apurados. Não afirmar completude do produto neste primeiro incremento.
