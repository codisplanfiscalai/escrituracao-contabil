# Eventos de NF-e/NFC-e: recepção e conferência rastreáveis

## Escopo e dependências — 06/11/2026

Incremento fiscal posterior ao PR #18, base `2a68f7452e739438cc2922dc2a3b5702a96291ea`, para PR em rascunho destinado à develop. A cadeia anterior permanece necessária: #18 → #16 → #14 → #13 → #11 → #10 → #8. Não representa merge, release, homologação ou implantação.

Implementa observação de eventos processados de cancelamento e Carta de Correção, preservação dos originais, fila de conferência por empresa, decisões versionadas e vínculo histórico com a escrituração explícita. Não emite ou transmite eventos e não consulta a SEFAZ.

## Fontes verificadas e limite da consulta

Foram consultados os conteúdos oficiais indexados do MOC on-line da Fazenda do Paraná:

- [Registro de eventos — parte geral](https://moc.sped.fazenda.pr.gov.br/NFe_NFCe/RecepcaoEventoGeral.html): separação entre pedido, retorno e armazenamento procEventoNFe; campos de identificação/correlação e códigos 135/136.
- [Cancelamento](https://moc.sped.fazenda.pr.gov.br/NFe_NFCe/RecepcaoEventoCancelamento.html): evento 110111, protocolo da NF-e e justificativa; 110112 identificado como evento diferente, fora deste perfil.
- [Carta de Correção](https://moc.sped.fazenda.pr.gov.br/NFe_NFCe/RecepcaoEventoCartaCorrecao.html): evento 110110, texto e condições de uso, sequências e restrição ao modelo 65.

A abertura direta dessas páginas não funcionou no navegador de pesquisa. Uma tentativa limitada de leitura direta recebeu `Tunnel connection failed: 403 Forbidden`. Não houve contorno desse bloqueio, download de pacote XSD ou leitura integral alegada. O perfil delimita os caminhos efetivamente observados no conteúdo oficial indexado. O MOC on-line é referência de apoio; não substitui a edição oficial aplicável à operação.

## Perfil de leitura

O perfil `nfe-evento-processado-1.00-v1` aceita somente `procEventoNFe` 1.00, com um `evento` e um `retEvento`, ambos 1.00. Tipos cobertos: cancelamento 110111 e CC-e 110110; modelos identificados na chave: 55/65. CC-e para modelo 65 e sequência acima de 20 são preservadas com pendência impeditiva.

São observados chave, tipo, sequência, ambiente, órgão, autor numérico CNPJ/CPF, data/hora com fuso, versão, descrição e detalhes específicos. O cancelamento conserva separadamente o protocolo da NF-e do pedido e o protocolo do evento informado no retorno. A CC-e conserva texto e condições de uso sem interpretar ou substituir campos documentais.

O retorno conserva cStat, motivo, aplicação, identificação/correlação e protocolo/data quando presentes. Pedido e retorno divergentes são recusados pelo perfil e ficam como fonte pendente, com original preservado. Correlação incompleta fica observada e bloqueada para manter o fluxo.

O código 135 é apresentado como registro/vínculo **informado pelo arquivo**; 136, como registro sem vínculo informado. Outros códigos permanecem observados sem conversão em sucesso. Não há presunção de autorização, inclusive em duplicidade 573, rejeição ou cancelamento extemporâneo.

Cada campo conserva caminho, texto decodificado e texto normalizado. O arquivo original e seu SHA-256 preservam a representação de bytes/entidades. São recusados DTD/entidades, encoding com NUL, estrutura ambígua, escalar duplicado, versão fora do perfil e arquivo acima de 10 MiB. A prévia é limitada a 8 MiB. Esses controles não são validação XSD completa, assinatura, autenticidade, dígitos verificadores ou análise da legalidade do texto.

## Recepção e associação

O recebimento usa a caixa de entrada existente, sem exigir competência ou plano. Também funciona dentro dos pacotes já suportados. Os eventos ficam em índice separado; não são importados como notas ou movimentos.

A identidade operacional combina chave, ambiente, tipo e sequência dentro da empresa. Cópias com os mesmos bytes permanecem preservadas e são agrupadas sem duplicar a identidade. Origens diferentes para a mesma identidade geram pendência; nenhuma é escolhida automaticamente. Nova sequência de CC-e permanece separada, sem substituir ou aplicar o texto anterior.

O documento é localizado pela chave na mesma empresa. Enquanto não estiver organizado, o evento permanece aguardando correlação. Para manter o fluxo, exige-se XML documental ativo com ambiente único compatível. Ambiente ausente, divergente ou não confirmado impede essa decisão. Não se infere ambiente de um registro SPED.

Fontes recebidas por versões anteriores não são reinterpretadas durante a migração. Um evento antigo não identificado precisa ser recebido novamente neste perfil; ambos os recebimentos e suas evidências permanecem preservados.

Retirada lógica de uma fonte de evento não apaga a observação nem elimina a pendência do documento. A integridade dos originais é novamente verificada ao consultar/conferir o evento.

## Decisões e efeitos

Na Recepção, a fila paginada permite buscar por chave, consultar origens/campos/retorno e registrar uma decisão com confirmação, motivo e referência da conferência externa:

1. **Pendente:** mantém a análise em aberto e bloqueia nova escrituração do documento.
2. **Suspender:** registra decisão explícita de suspender nova escrituração.
3. **Manter fluxo:** registra conferência operacional para continuar sem alterar dados; exige correlação, integridade e cobertura sem pendências impeditivas.

Nenhuma decisão muda dados da nota, alíquotas, regras, memórias tributárias, partidas, títulos ou liquidações. A decisão não certifica autorização SEFAZ. Correção textual não é convertida em alteração de campo. Cancelamento não dispara estorno, cancelamento financeiro ou retificação.

Prévia e decisão são protegidas por hash e transação. Alteração do contexto exige nova conferência; repetição da mesma tentativa/conteúdo retorna o resultado já preservado. Conteúdo diferente com a mesma tentativa é recusado. Origens conflitantes invalidam a decisão corrente; nova cópia idêntica não a invalida.

Recepção e anotação podem ocorrer em período fechado porque não alteram movimentos. Livros e operações já escrituradas mantêm seus snapshots. A fila sinaliza pendência posterior; não há reabertura automática. Correções efetivas precisam de procedimento específico autorizado e módulos/períodos apropriados.

Uma pendência de evento impede nova escrituração do documento e encerramento fiscal/global do recorte. O módulo contábil mantém seu controle independente. Essas pendências são de conferência operacional, sem declarar automaticamente que a nota está legalmente cancelada.

## Rastreabilidade na escrituração

Ao escriturar explicitamente uma operação cujos eventos foram conferidos, a mesma transação grava uma evidência separada: versão/hash da operação, documento, contexto e hashes das decisões consideradas. Falha posterior desfaz essa evidência junto dos movimentos. Não se altera o payload histórico para acrescentar eventos recebidos depois.

A evidência e as decisões são consultáveis pela API e pela interface, com download JSON operacional e download exato dos originais. Decisões futuras não reescrevem a evidência de uma escrituração anterior. JSON operacional não é obrigação fiscal nem prova de transmissão.

## Esquema e integração

O esquema **18** acrescenta `nfe_event_observations`, `nfe_event_reviews` e `nfe_event_posting_proofs`. A migração é aditiva, sem reinterpretar originais ou regravar movimentos. Banco atualizado exige executável compatível; antes de uso operacional, conferir migração/restauração numa cópia privada autorizada.

Arquivos centrais: `src/nfe_events.py` (leitor), `src/nfe_event_store.py` (índice/decisões/provas), `src/source_evidence.py` (recepção), `src/work_api.py` (rotas), `src/work_store.py` e `src/module_closure.py` (controles), `src/persistence.py` (migração), frontend compartilhado e testes.

Consultas exigem workspace.read e escopo da empresa; decisões exigem workspace.review e CSRF no portal. Uma permissão de escrita comum não concede revisão de eventos. A composição contábil deve reconciliar as expectativas de esquema para 18 e executar testes/builds da versão combinada. Não duplicar as composições contábeis antigas.

Windows gráfico/tray, servidor Docker e arquitetura integrada permanecem preservados. Não há novo executável, serviço obrigatório, dependência de OCR ou envio de dados a terceiros.

## Validação e pendências

Testes sintéticos cobrem os dois tipos de evento, protocolos separados, textos/caminhos, status informados, estruturas inválidas, correlação, ambiente, recepção anterior à nota, escopo, CSRF/permissões, cópias/conflitos/sequências, retirada lógica, integridade, confirmação, concorrência, idempotência, rollback, bloqueios, preservação de livros e migração real 17→18. O navegador exercita local/portal, resposta perdida, download, reload, evidência de escrituração, mobile e troca de empresa.

Resultados efetivos, SHA, PR, composição contábil e builds/CI são registrados na descrição do PR e na conversa. Não são atribuídos ao incremento resultados de versões anteriores.

Permanecem fora do perfil: envEvento/retEnvEvento ou pedido/retorno isolados, cancelamento por substituição 110112, cancelamento legado, outros eventos/documentos, autor alfanumérico, assinatura/XSD/consulta SEFAZ, validação legal da CC-e, seleção entre origens conflitantes, estorno/retificação automática e transmissão de obrigações. São necessários leiautes aplicáveis, amostras autorizadas e homologação dos procedimentos de correção.

Os anexos legados permanecem sem acesso, pela falha anterior `library file transfer failed: download failed`. Nenhum binário desconhecido foi executado ou código-fonte recuperado. Este incremento se apoia no código existente, requisitos autorizados e conteúdo oficial verificável disponível.
