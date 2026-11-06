# Importação versionada dos cadastros fiscais

## Resultado e dependências

Incremento separado sobre o HEAD `a5ac6898c87d3d43357fca1a1c2c429cecf7b9d5` do PR #10. Preserva a dependência #10 → #8 e não modifica as branches desses PRs ou da frente contábil #9. O destino final é develop; enquanto a base não for integrada, o diff contra develop inclui os incrementos anteriores.

Implementa recepção e ativação revisada de cadastros CFOP, NCM, receitas e serviços, por empresa, com arquivo recebido, hashes, edição, sistema, jurisdição, vigências, comparação com versões anteriores e manifesto de aplicação. Não faz download automático, não transforma HTML/PDF/XLSX e não presume o leiaute nativo de qualquer portal. Não carrega códigos ou alíquotas oficiais no banco ou no Git.

## Referências oficiais verificadas em 06/11/2026

| Cadastro | Referência | Evidência e limite |
| --- | --- | --- |
| NCM | [Receita Federal: download da NCM](https://www.gov.br/receitafederal/pt-br/assuntos/aduana-e-comercio-exterior/classificacao-fiscal-de-mercadorias/download-ncm-nomenclatura-comum-do-mercosul) | Documenta JSON/XLSX e que o download cobre a tabela vigente, sem histórico/códigos futuros. O download direto do Siscomex foi bloqueado neste ambiente com `URLError: <urlopen error Tunnel connection failed: 403 Forbidden>`. Nenhum arquivo foi materializado; o leiaute nativo não foi validado. |
| CFOP | [CONFAZ: referência de CFOP](https://www.confaz.fazenda.gov.br/legislacao/ajustes/sinief/copy_of_cfop_cvsn_70_nova) | A página não pôde ser transferida na consulta, por timeout. Resultados alternativos do CONFAZ apresentam anotações de revogação/sem efeitos; não foram usados como tabela vigente nem aprovados para carga automática. Edição, atos e vigências exigem conferência. |
| Receitas | [Receita Federal: Sicalc](https://sicalc.receita.fazenda.gov.br/sicalc/principal) | O portal oferece Consulta de Códigos de Receita. Não foi validado arquivo completo para importação. DARF não representa automaticamente receitas estaduais ou municipais. |
| Serviços | [Portal NFS-e: códigos publicados](https://www.gov.br/nfse/pt-br/mei-e-demais-empresas/codigos-de-tributacao-nacional-nbs) | A página contém códigos desdobrados de seis dígitos. Não estabelece equivalência automática com subitens LC116, códigos municipais ou NBS, nem fornece vigência individual para todos os registros. |

Esses links são referências documentais, não certificação dos arquivos enviados. A lista registra a data e o estado da verificação; não significa monitoramento contínuo. A URL fornecida pelo operador é armazenada e não é acessada pelo servidor. Não há tentativa de contornar bloqueios, CAPTCHA, autenticação ou limites dos provedores.

## Arquivo aceito e limites

CSV ou JSON UTF-8, até 8 MiB e 15000 registros por snapshot. Cada registro contém exatamente código textual, descrição, início e fim de vigência. Zeros iniciais são preservados. Datas usam AAAA-MM-DD; fim em branco significa apenas fim não informado no arquivo, não uma garantia legal de vigência indefinida.

CSV usa separador ponto e vírgula e este cabeçalho:

```csv
code;description;valid_from;valid_to
```

JSON usa o perfil documentado:

```json
{"profile":"cadastro-fiscal-v1","records":[]}
```

Os exemplos mostram a estrutura vazia, sem códigos ou datas normativas presumidas. Antes da recepção é necessário preenchê-los com registros conferidos. Código duplicado, campos desconhecidos, chave JSON repetida, código numérico, data ausente/inválida ou formato nativo não identificado são recusados. Cada arquivo representa um snapshot com um registro por código; outras vigências são recebidas como novas edições.

Conversões precisam ser registradas em `transformation_reference`. O arquivo preservado é exatamente o recebido, inclusive quando for uma conversão. Seu hash não comprova que o conteúdo reproduza fielmente um documento oficial que não foi fornecido.

## Origem, sistema e jurisdição

Metadados exigidos: tipo, sistema de códigos, jurisdição, publicador declarado, URL HTTPS, edição/versão, data de consulta, recorte e referência da conversão/conferência. Recortes disponíveis: parcial ou snapshot informado. O sistema não certifica completude nem preenche datas legais automaticamente.

Sistemas aceitos: NCM, CFOP, DARF, receita estadual, receita municipal, LC116, NFS-e nacional e serviço municipal, conforme o tipo. Jurisdição é BR, UF:XX ou MUN:código IBGE de sete dígitos. A verificação municipal é estrutural; não confirma existência ou abrangência do município em uma tabela oficial.

O vínculo de sistema/jurisdição é por empresa, tipo e código. Códigos distintos de sistemas diferentes podem coexistir. Reutilizar o mesmo código em outro sistema ou município é bloqueado, sem conversão silenciosa. Referências qualificadas para permitir duas definições simultâneas do mesmo código ainda não foram implementadas.

Códigos legados selecionados, ainda sem vínculo de escopo, exigem reconhecimento explícito e referência de revisão. As versões anteriores não são reescritas ou certificadas retroativamente. O vínculo também não transforma uma alteração manual posterior em conteúdo oficial: a edição manual produz outra versão sem o marcador de importação daquela versão anterior.

## Recepção, comparação e ativação

A recepção não exige competência e não altera códigos ativos. Preserva bytes, nome declarado, SHA-256 do arquivo, snapshot normalizado e seu hash, metadados, responsável, motivo e instante. Pode ocorrer com períodos encerrados.

A ativação exige selecionar de 1 a 500 códigos, informar uma data local de aplicação, gerar a prévia e confirmar revisão de conteúdo, origem, seleção, vigências e jurisdição. A prévia mostra versões, descrições e estados anteriores e propostos. A ativação deste perfil cria versões ativas; inativação continua disponível na manutenção manual versionada.

O início local é o maior entre o início registrado no arquivo e a data de aplicação declarada. O início e o fim originais permanecem em `data.import_origin`, juntamente com sistema, jurisdição, edição, URL, hash do arquivo, recibo e referência da revisão. Código já expirado nessa data não pode ser ativado.

A ativação é transacional. Mudanças nos códigos selecionados ou no vínculo de escopo invalidam a prévia. Duas aplicações concorrentes da mesma prévia permitem somente uma gravação. Falha em qualquer registro desfaz códigos, vínculos, manifesto e auditoria da tentativa. Recepção e ativação têm chaves idempotentes; uma repetição recupera o resultado sem duplicar versões.

Ausências no arquivo ou na seleção não excluem nem inativam códigos existentes. O mecanismo não declara sincronização integral com a fonte. Corrigir uma edição exige receber outro arquivo e revisar a aplicação; arquivos e manifestos anteriores permanecem preservados.

Fechamentos fiscais são conferidos dentro da transação. Parametrização que alcance período fechado é recusada. Uma data local posterior pode restringir a aplicação a um período aberto, sem alterar a vigência original documentada ou reabrir períodos silenciosamente.

## Consulta, memória e exportação

Arquivo recebido e registros normalizados são consultáveis por empresa; a busca no arquivo cobre código/descrição, em páginas de 100 registros. O catálogo ativo também é paginado, com busca por código/tipo e histórico separado de cada código. Isso evita renderizar todos os códigos de uma NCM de uma vez.

O GET tax-config passa a retornar até 100 códigos atuais em `catalog`, com total, offset e limite em `catalog_page`. `tax-catalog-codes` e `tax-code-history` fornecem as páginas seguintes e versões anteriores. Os serviços internos de regra continuam resolvendo código e vigência, agora com consulta direta ao código no banco.

O download do arquivo devolve os bytes recebidos com nome seguro fixo. O manifesto JSON inclui arquivo/parser, hash bruto e normalizado, metadados, data local, revisão e dados exatos das versões criadas. A lista de aplicações usa resumos; o manifesto completo é carregado sob demanda.

Regras calculadas a partir desses códigos preservam a origem importada na memória tributária. Alteração posterior de catálogo ainda não escriturado exige recálculo. Uma URL, hash ou confirmação de revisão não representa assinatura digital, autenticidade oficial ou homologação fiscal.

## Migração, integração e permissões

Migração aditiva **13 → 14**: novas tabelas `tax_catalog_imports`, `tax_catalog_import_applications` e `tax_catalog_scopes`. Não reescreve códigos, documentos, cálculos, movimentos ou fechamentos anteriores. Binários anteriores que não suportam esquema 14 não devem operar esse banco; a evolução precisa ser integrada e distribuída como conjunto.

A manutenção manual e o cálculo por item do #10 permanecem. Os motores contábil e financeiro não foram alterados. Pontos compartilhados: `src/persistence.py`, rotas local/portal, serviços tributários, controlador/template/render do workbench e workflow de navegador. A frente contábil #9 possui duas expectativas fixas de esquema 13 em `tests/test_accounting_schema13.py` (linhas 69 e 160 na revisão c4a7a31); devem ser reconciliadas para a versão final 14 durante a integração.

Leitura, arquivo e manifestos exigem workspace.read e escopo da empresa. Recepção, prévia de aplicação e ativação exigem workspace.review; POSTs preservam CSRF. O portal externo do cliente não recebe essas rotas. Não há fetch de URLs fornecidas pelo operador, execução de arquivos ou novas dependências.

## Validação e pendências

Fixtures são sintéticas. Cobrem bytes/hashes, UTF-8/BOM, zeros iniciais, limites e paginação, arquivos inválidos, vigências, seleção, histórico, código ausente, jurisdições, legado, idempotência, corrida entre aplicações, rollback, bloqueio fiscal, permissões/CSRF, origem na memória de cálculo e migração 13→14.

O navegador cobre recepção sem competência, arquivo sem ativação, comparação/ativação, duas edições, histórico de vigência, preservação de código ausente, download exato, manifesto, mobile e troca de empresa, nos modos local e portal. Resultados executados, SHA e CI são registrados na descrição do PR e na conversa.

Pendências: arquivos oficiais acessíveis para validar adaptadores nativos; edição/vigência de CFOP; tabelas de receitas por órgão/documento/jurisdição; códigos municipais e eventuais correspondências; datas legais por registro; validação operacional e homologação. Não há carga nativa NCM concluída, base oficial completa, atualização automática, classificação tributária ou novas alíquotas. CBS/IBS continuam fora do cálculo. Os anexos legados permanecem sem bytes/pixels acessíveis; não foram executados binários desconhecidos. Não há dados reais nos testes/Git nem merge, release ou implantação neste incremento.
