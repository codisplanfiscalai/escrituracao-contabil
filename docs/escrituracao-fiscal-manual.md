# Escrituração fiscal manual e documentos de outra competência

Contrato do incremento iniciado em 04/11/2026 sobre develop a1e8932.

## Fluxo e preservação

1. Selecionar empresa e competência de escrituração. Período-base continua separado.
2. Receber XML 4.00 55/65 ou SPED parcial, ou cadastrar lançamento fiscal manual.
3. Preparar uma ficha a partir de um documento importado sem modificar original, chave canônica ou observações. Informar emissão, entrada/saída (quando conhecida), data de escrituração, operação, identificação, valor e observações.
4. Salvar rascunho com motivo e controle de versão. A interface mostra avisos e histórico. Emissão fora do mês é aviso de conferência, não proibição de escrituração. Não inferir situação fiscal de extemporaneidade somente pela emissão anterior.
5. Revisar versão exata e fontes atuais com motivo. Edição posterior gera outra versão e exige nova revisão. Concorrência recusa versão desatualizada.
6. Fechar período fiscal somente com versões revisadas e fontes atuais. Registrar exportação externa exige referência e confirmação, sem afirmar que o aplicativo gerou ou homologou arquivo. Reabertura de fechado exige confirmação/motivo; exportado exige proposta de retificação. Lote contábil fechado/evidência permanece imutável.
7. Em período protegido, a inclusão/edição só pode registrar proposta explícita de retificação, sem trocar a versão vigente. Aprovação/aplicação de retificação externa não faz parte deste incremento.

## Modelo incremental

Esquema 6 adiciona fichas fiscais, versões de ficha e estado/histórico de período. Originais, observações, títulos, parcelas, revisões documentais e snapshots contábeis permanecem. Competência vem do período escolhido; emissão e entrada/saída são fatos independentes. Data de escrituração pertence à competência escolhida. Nova origem é deduplicada pela chave documental; ficha manual sem chave mantém identidade própria e aviso de possível coincidência. Nunca inventar chave.

Modelos 55/65 são suportados neste recorte de cabeçalho. NFC-e sem destinatário identificado pode ser recebida com aviso, sem fabricar CPF/CNPJ. Validade/autorização fiscal completa não é inferida. Perfis de leitura novos preservam análises antigas; reanálise é explícita, inclusive de rejeições anteriores, mantendo bytes e auditoria.

A ficha fiscal não é lançamento de débito/crédito. O motor contábil existente continua explícito: ficha não revisada ou divergente da origem contábil exige tratamento, sem ignorar silenciosamente uma edição fiscal. Livros completos, itens/tributos detalhados, geração SPED, seis adaptadores posicionais Prosoft e CTBLCTOS LC1/LC2 continuam incrementos independentes. CBS/IBS não são calculados.

## Aceite

- Entrada de setembro emitida em agosto pode ser recebida, preparada, revisada e mantida em setembro; original e datas intactos.
- XML 55/65 e C100 parcial 55/65 preservam identificação, origem e datas; validação de formato/chave/empresa continua.
- Inclusão/edição manual, revisão, concorrência, idempotência, isolamento, histórico e persistência testados com fixtures fictícias.
- Fechamento/exportação informada não permite alteração silenciosa; proposta preserva vigente, fechado e evidências.
- Mesma API de domínio no Windows offline e servidor, sem infraestrutura adicional no desktop.
- UI cobre preparar, editar, salvar, revisar e consultar histórico. Sem alegação Prosoft/PVA/XSD.

Quantidades 62 entradas (34 agosto/28 setembro), 363 NFC-e e 4 NF-e são relatos do usuário, ainda não reconferidos nos arquivos reais.

## Tela unificada, guias e terceiros

A tela reúne entradas, saídas, serviços tomados e prestados. Campos de serviço aparecem conforme a operação; valores de ISS são informados, nunca calculados. Sem promessa de importação NFS-e, código municipal validado ou livro de serviços oficial. Campos de serviço já preenchidos permanecem visíveis ao trocar a operação, para correção explícita.

Cada guia guarda título, formulário incompleto, contexto, versão e operador em SQLite. A troca de área aguarda o salvamento; falha de persistência mantém a área e informa o erro. Uma guia encerrada fica preservada no banco/auditoria. As guias não são uma fila de processamento em segundo plano. Formulários fiscais abertos são privados ao operador, enquanto as fichas salvas respeitam as permissões de escrita/revisão e empresa do portal.

Terceiros usam empresa + tipo + CPF/CNPJ normalizado como identidade. XML novo registra emitente/destinatário disponíveis, nome, papel e arquivo de origem. No SPED parcial somente o CNPJ do emitente comprovado pela chave é registrado quando externo à empresa, sem nome inventado; registro 0150 completo ainda é pendente. Consumidor anônimo não vira cadastro fictício. Nomes divergentes aguardam decisão de revisão com motivo, versão e observação escolhida; nomes de origem continuam preservados. Importações antigas podem ser reanalisadas explicitamente para alimentar a base, sem alteração de bytes.

Ficha manual com chave que depois recebe XML pode ser associada explicitamente por “Preparar documento”: a mesma chave, fontes atuais e versão vigente são exigidas. A associação gera revisão e auditoria, sem outra ficha. Não associa automaticamente casos sem chave ou divergentes; períodos protegidos exigem o futuro fluxo de retificação.

## Próximos incrementos e aceite

1. Escrituração contábil manual e edição: criar identidade de lançamento independente de documento, linhas D/C em centavos exatos, conta analítica/vigência, histórico padrão e complemento, justificativa, data e competência. Rascunhos editáveis por versão; revisão exige equilíbrio, contas válidas e origem declarada. Fechados recebem estorno/ajuste vinculado, nunca sobrescrita. Testar edição simultânea, estorno, reabertura autorizada, mudança de plano e repetição da tentativa. Ainda não implementado: o motor atual trabalha sobre documentos revisados.
2. Itens, tributos e livros fiscais: separar fatos importados de decisões de escrituração e regras por leiaute/período; prévias e totalizadores antes da revisão. ISS atual é apenas informação de ficha. CBS/IBS fora do cálculo.
3. Plano de escrituração aprovado, exceções justificadas e agregação contábil por dia: cada partida deve manter o conjunto de documentos/decisões e controles de total, impedindo reaplicação entre integração fiscal, folha e CTBLCTOS.
4. Prosoft: seis formatos posicionais e CTBLCTOS LC1/LC2 como adaptadores distintos com amostras autorizadas, campos/tamanhos/encoding/totais verificáveis e teste real no importador. Sem contratos acessíveis, não gerar suposta compatibilidade.
5. SPED completo: implementar perfis fechados de escrituração, versão e período, hierarquia/contagens/totalizadores; validar contra documentação e ferramenta oficial aplicáveis. C140/C141 modelo 55 somente em perfil Prosoft comprovado, separado da EFD oficial.
6. Guias e tarefas: expandir a persistência para fila local transacional recuperável após interrupção, com os mesmos contratos no servidor; sem exigir serviços externos no Windows. ZIP existe em módulos de auditoria, mas integração geral ZIP/7z/RAR com limites e travessia segura deve ser comprovada por fluxo antes de afirmar suporte.

Retificações propostas não são aplicadas automaticamente. Cadastro de terceiros ainda não inclui endereço/inscrição/identidades estrangeiras nem reconciliação integral 0150. Os limites são visíveis; essas lacunas não foram preenchidas por suposição.
