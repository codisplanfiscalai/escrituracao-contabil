# PR em rascunho preparado — sem publicação

Destino: `develop`. Origem: `feat/cadastro-clientes-busca-fontes`.

Título sugerido: `feat: separar cadastros e controlar busca e encerramento por módulo`

## Descrição proposta

O cadastro tratava todas as empresas no mesmo registro e não oferecia dados complementares versionados. O encerramento era global, sem permitir bloquear fiscal e contábil separadamente. Este incremento separa a empresa usuária dos clientes, acrescenta cinco seções cadastrais com histórico e permite buscar fontes recebidas sem abrir competência.

O encerramento passa a ter estado independente por empresa, mês e módulo. Receber arquivos continua permitido; organizar, alterar ou efetivar operações respeita os bloqueios. Operações com efeitos fiscais e contábeis exigem ambos abertos. Fechar/reabrir exige conferência, prévia atual, motivo e auditoria. A apuração é conferida externamente, sem cálculo automático. As migrações aditivas 10→11→12 preservam originais, cadastros e movimentos.

Windows passa a iniciar no tray, com `--show-window` para abrir a administração. O produto continua integrado, sem um EXE por tela ou relatório. Inclui ferramenta de triagem estática PE testada apenas com bytes sintéticos. A transferência dos 13 executáveis e 35 prints falhou; não há tecnologia ou telas do sistema original confirmadas.

Validação local: `python scripts/build.py check` aprovado — 264 testes da aplicação, 18 de distribuição e 27 de auxiliares de CI; um teste DPAPI exige Windows. Também passaram os cenários de navegador cadastral, de encerramento, fiscal, portal e fluxo integrado local/portal. Não foram incluídos anexos ou dados reais.

Antes do merge: reconciliar o esquema 12 e as guardas de `src/work_store.py` com a frente contábil; executar CI Windows x86/x64 e smoke dos executáveis finais pela alteração de inicialização. CI remota, publicação de artefatos, homologação fiscal/Prosoft e implantação não foram executadas. Sem mudanças em workflows, Dockerfile ou dependências.

## Prontidão

A branch está baseada na `develop` `22ebdb14d812980dac532cd7c0403c2f811f559e`, conferida novamente após a retomada. As alterações estão isoladas para revisão em rascunho, com commits locais e sem publicação. Os bloqueios de anexos impedem alegar engenharia reversa concluída, mas estão explícitos e não foram usados para inventar comportamento.

Este arquivo prepara título e descrição. Não constitui autorização para push, abertura do PR, merge, release ou deploy.
