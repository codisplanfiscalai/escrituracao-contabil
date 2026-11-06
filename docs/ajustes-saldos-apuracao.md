# Ajustes de apuração e saldos entre competências

## Entrega e dependência

Incremento fiscal da branch `feat/ajustes-saldos-apuracao`, baseado no commit `3e3535bfbe015fe493fdbcb76c83a60af2da5fe6` do PR #13. Cadeia de dependências: este incremento → #13 → #11 → #10 → #8. Destino de publicação: PR em rascunho para develop. Não há merge, release ou implantação nesta entrega.

A aplicação recebe ajustes exclusivos da apuração e transporte explícito de saldos aritméticos. Não há transporte automático de saldo negativo, reconhecimento de direito a crédito, compensação entre tributos, guia ou contabilização/baixa automática. CBS/IBS continuam fora do cálculo.

## Ajustes manuais

Cada ajuste exige componente, receita quando aplicável, data na competência de destino, efeito débito/crédito, valor positivo em texto decimal, descrição e referência que autoriza o registro. Antes de efetivar, o operador gera uma prévia, informa motivo e referência de conferência e confirma expressamente origem, valor, natureza, autorização e efeitos.

O componente pode ser ICMS, ISS, PIS, COFINS, ICMS_ST, ICMS_DIFAL, FCP:IDENTIFICADOR ou RETENCAO:IDENTIFICADOR. Modalidades e tributos diferentes permanecem separados. Receita preenchida exige cadastro ativo e vigente na data declarada; sua versão integra a evidência. O cadastro de um código não comprova enquadramento ou autorização legal.

A prévia não grava reserva nem altera a apuração. A aprovação cria registro imutável com responsável, motivo, referência, parâmetros, hash da prévia e estado dos fatos do destino na conferência. Não é possível editar o registro aprovado: correções exigem cancelamento em nova versão e novo ajuste conferido.

## Origem e transporte

O transporte exige uma competência anterior da mesma empresa, a última apuração validada correspondente aos fatos atuais e o módulo fiscal da origem encerrado. O destino deve estar aberto tanto globalmente quanto no fiscal.

O operador seleciona a origem e declara valor e data; o valor não é preenchido automaticamente. Componente, receita e natureza do saldo são preservados exatamente. Saldo negativo só pode ser transportado como crédito declarado; positivo, como débito declarado. O nome dessa natureza representa o sinal aritmético e não constitui crédito legal, obrigação de pagamento ou autorização de compensação.

```text
reservado = soma dos transportes aprovados ainda não cancelados
disponível = valor absoluto do saldo da origem − reservado
valor declarado do novo transporte ≤ disponível
```

A capacidade é controlada por empresa, apuração de origem, componente e receita, considerando todos os destinos. A aprovação reserva o valor, mesmo antes da validação da apuração do destino. Reservas não expiram automaticamente; transportes não utilizados devem ser cancelados expressamente.

A gravação usa transação SQLite com `BEGIN IMMEDIATE`, nova conferência da disponibilidade e comparação do hash da prévia. Duas competências não podem consumir a mesma capacidade além do saldo. Alterações nos fatos ou nas reservas depois da prévia exigem nova conferência. Tentativas repetidas com a mesma chave e conteúdo retornam o registro existente; a chave não aceita outro conteúdo.

A memória guarda identificador/hash da apuração de origem, competência, versão do encerramento fiscal, saldo, componente, receita, natureza, capacidade e reservas vistas na aprovação. O transporte não reescreve a memória histórica da origem. A consulta de saldos mostra separadamente saldo histórico, reserva e disponibilidade.

## Cancelamento e períodos fechados

Cancelamento exige confirmação, motivo, referência de conferência e comparação da versão/hash atual. Uma nova versão referencia o registro cancelado; o histórico anterior permanece preservado. Cancelar um transporte libera sua reserva e torna a apuração anterior do destino desatualizada para novos fechamentos.

Criar ou cancelar ajustes é bloqueado em destino fiscal ou globalmente encerrado. Reabrir o fiscal da origem é bloqueado enquanto existirem transportes ativos. Para corrigir a origem, é necessário reabrir os destinos pertinentes, cancelar os transportes, reabrir a origem, corrigir e validar sua nova apuração, encerrar o fiscal e preparar novos transportes conferidos.

O fechamento contábil permanece independente. Reabrir o recorte global não remove o bloqueio fiscal; registros contábeis continuam sujeitos aos controles próprios. A recepção de arquivos continua independente da abertura de período e não efetiva ajustes ou movimentos em competências fechadas.

## Apuração e memória

Períodos com histórico de ajustes usam `apuracao-parametrizada-v2`, incluindo os registros e hashes no snapshot e na exportação JSON. Períodos sem ajustes conservam o formato v1 anterior. Linhas de ajuste identificam origem manual/transporte e mantêm suas referências.

Os totais continuam agrupados por componente e receita. Não existe saldo líquido global compensando tributos diferentes. O relatório distingue saldo anterior aos ajustes, ajustes a débito, ajustes a crédito e saldo final:

```text
saldo_final = saldo_antes_ajustes + ajustes_debito − ajustes_credito
```

Os campos `debito` e `credito` incluem fatos e ajustes; os subtotais `ajustes_debito` e `ajustes_credito` permitem distingui-los. Efeito informativo dos movimentos não entra no saldo. Alterar ajustes, cancelar transportes ou alterar um cadastro aplicável invalida a prontidão da apuração para fechamento. Mudanças na origem ou reservas inconsistentes bloqueiam a apuração do destino.

Os ajustes não criam operações de escrituração, partidas contábeis, títulos financeiros, pagamento ou compensação. Não substituem o ajuste fiscal vinculado a um movimento original nem satisfazem automaticamente a cobertura tributária exigida para estornos de operações.

## Migração e integração contábil

O esquema SQL passa de 14 para **15**, com a tabela `tax_assessment_adjustment_versions` e índice de consulta por empresa/competência. A migração é aditiva, transacional e não regrava documentos, movimentos, apurações ou fechamentos anteriores. Bancos no esquema 15 não devem ser abertos com executáveis antigos.

Pontos de integração: `src/persistence.py` registra a migração e o mixin; `src/module_closure.py` protege a reabertura da origem; `src/tax_assessment.py` incorpora linhas e evidências; `src/tax_api.py` expõe consulta/prévia/aprovação/cancelamento com permissão de revisão; `src/web/workbench.js`, template e render implementam a interface integrada. O núcleo novo fica em `src/tax_balances.py`.

O motor contábil e financeiro não foi alterado. Consumidores contábeis devem distinguir linhas de ajuste de movimentos e só gerar integrações por políticas próprias aprovadas. O PR contábil #12 é compatível com esquema 14; suas expectativas de teste precisam ser atualizadas para 15 ao compor este incremento. Testes combinados com adaptações locais serão relatados separadamente de compatibilidade já publicada.

A aplicação permanece única, com Windows gráfico/tray e execução Docker. Não é criado serviço obrigatório ou executável por rotina.

## Validação e pendências

Fixtures inteiramente sintéticas. Os testes incluem apuração documental com subtotais de ajustes, transporte parcial, concorrência entre conexões, idempotência, prévia desatualizada, cancelamento imutável, segregação de empresa/componente/receita, conferência obrigatória, cadastro/vigência, origem inválida, destino fechado, bloqueio de reabertura da origem, independência contábil e migração 14→15 preservando bytes/hashes e bloqueios.

O navegador percorre ajuste manual, transporte de origem encerrada, tentativa acima do disponível, conferência, exportação JSON, cancelamento, invalidação da apuração e troca de competência/empresa nos modos local e portal. Resultados reais de suíte, regressões, builds, integração e CI constam da descrição do PR e da conversa do projeto.

Ainda exigem definição e homologação: hipóteses legais e códigos oficiais de ajuste, autorização de créditos, limitações por tributo/jurisdição, prazos, prescrição, pagamentos, restituições e compensações permitidas. O mecanismo não certifica saldo legal disponível, entrega de obrigação acessória ou todos os requisitos de apuração fiscal.

Os anexos legados permanecem sem bytes/pixels locais por falha de transferência. Nenhum executável desconhecido foi executado, não há recuperação comprovada de código-fonte e nenhum dado real foi incluído em Git/CI.
