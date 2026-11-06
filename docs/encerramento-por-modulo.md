# Encerramento por empresa, competência e módulo

## Resultado implementado

Fiscal e contábil possuem controles independentes de abertura/encerramento por cliente e mês. A tabela `module_period_versions` mantém versões, snapshot da conferência, hash, marcações de revisão, referência da evidência, responsável, motivo e instante. A migração aditiva **11 → 12** preserva os cadastros e movimentos existentes. Bancos anteriores passam pelas migrações aditivas já estabelecidas.

O controle global anterior permanece para compatibilidade e preservação de fechamentos existentes. Um módulo aberto não sobrepõe um fechamento global anterior. Reabrir o controle global também não remove um bloqueio independente de módulo.

## Fechamento e reabertura

- A consulta apresenta a prévia atual e seus bloqueios. Encerramento exige a mesma versão/hash; concorrência ou novas operações exigem atualizar a conferência.
- Operações ainda em rascunho/revisadas e guias incompletas do módulo impedem seu fechamento. O fiscal também verifica documentos organizados ainda sem escrituração. O contábil exige abertura/saldos declarados.
- O operador confirma lançamentos, livros, correções e apuração no fiscal; no contábil, confirma lançamentos, livros, correções e saldos.
- É obrigatório registrar motivo e referência da conferência. **A apuração fiscal é conferida externamente por declaração do operador. A aplicação não calcula nem valida essa apuração.** A marcação não comprova homologação tributária.
- Reabertura exige motivo, autorização de revisão e prévia atualizada; cria outra versão, preservando o fechamento anterior. Não altera snapshots de operações já escrituradas.

## Barreiras de escrita

`assert_module_period_open` e `assert_operation_modules_open` são aplicados dentro da transação de gravação, com `BEGIN IMMEDIATE`, antes de produzir efeitos. Cobrem configuração de parâmetros compartilhados, versões de operações, conferência, efetivação e alteração de payloads das guias. A união dos módulos do payload anterior e do novo impede disfarçar uma operação fiscal como ajuste contábil para evitar o bloqueio.

A organização/reanálise de fontes em competência fiscal fechada é recusada. A retirada de fonte já organizada respeita ambos os módulos afetados e as proteções anteriores de dependências. **Receber arquivos sem competência continua permitido**, preservando originais para análise posterior; a caixa de entrada não permite efetivar movimentos no período bloqueado.

As operações que já foram efetivadas continuam imutáveis. Repetir um POST idempotente de uma operação escriturada apenas recupera seu resultado, sem gerar movimento adicional, mesmo após o fechamento.

## Independência e operações integradas

É possível encerrar fiscal e manter contábil aberto, ou o contrário, sem alterar outra empresa ou mês. Uma abertura ou ajuste exclusivamente contábil pode continuar com fiscal fechado. Uma operação que produz efeitos fiscais e contábeis precisa dos dois módulos abertos, porque sua efetivação atual é transacional e conjunta. O programa não efetiva metade da operação nem perde os vínculos para contornar um módulo fechado.

Para integração com a frente contábil, novas rotinas devem identificar todos os módulos que afetam e chamar a barreira dentro da mesma transação das escritas. Estornos fiscais são identificados também pela operação original, mesmo quando o payload de destino usa a natureza ajuste. As datas econômicas e a competência de destino continuam sujeitas às validações existentes.

## API e interface

- `GET /api/work-module-state?company_id=…&cycle_id=…`: retorna fiscal e contábil, estado, snapshot/hash, bloqueios e conferências exigidas.
- `POST /api/work-module-state`: recebe `company_id`, `cycle_id`, `module` (`fiscal`/`contabil`), `target` (`aberta`/`encerrada`), `snapshot_hash`, `reason`, `checks` e `evidence_reference`.
- Escrita exige `workspace.review`; contexto de empresa e proteção CSRF permanecem validados pelo servidor.
- Em Encerramento, os dois módulos aparecem na mesma aplicação, com ações independentes. O controle global anterior fica em seção recolhível. Não foi criado outro executável.

## Coordenação de arquivos

Além do incremento cadastral no commit `d046d7e`, esta atualização acrescenta `src/module_closure.py` e guardas compartilhadas em `src/work_store.py`. Também altera `src/persistence.py`, `src/work_api.py`, `src/source_evidence.py`, o template/render e o controlador do workbench. Os testes históricos esperam agora esquema **12**, não 11. A frente contábil precisa partir desse contrato ou reconciliar a migração antes do merge; não deve criar outra migração 11/12 com conteúdo diferente.

Não foram alterados os cálculos do motor contábil, `src/work_books.py`, `src/work_domain.py`, `src/accounting_store.py` ou `src/finance.py`. O Analisador Fiscal IOB foi registrado somente como referência futura: não há anexos, formatos, conversores ou integrações confirmados. O print encaminhado por engano à tarefa fiscal não foi tratado como referência funcional ou como acesso recuperado aos anexos.

## Validação e limites

Passaram os testes de independência entre módulos/clientes/meses, persistência após reinício, recebimento após fechamento, impedimento de organização/escrituração, rascunhos, parâmetros compartilhados, prévia desatualizada, conferências obrigatórias, histórico/auditoria e migração 11→12 preservando cadastro. A corrida entre fechar o fiscal e gravar uma nova operação permite somente uma das duas transações: a outra é bloqueada.

O contrato HTTP foi verificado com autenticação/CSRF. O teste de navegador passou para fechar/reabrir fiscal, manter contábil aberto e recuperar o estado após recarga. A verificação completa executada inclui **264 testes da aplicação, 18 de distribuição e 27 de CI**, com uma omissão de DPAPI por exigir Windows, além de templates, sintaxe, matemática, ícones e smoke autenticado.

Os anexos continuam sem bytes/pixels acessíveis; não foram reexecutadas tentativas já falhas sem nova evidência. Apuração calculada, importadores bancários, homologação Prosoft e a validação nativa Windows continuam pendentes. Não houve publicação, PR, merge ou implantação.
