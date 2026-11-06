# Ciclo de vida da administração Windows

## Escopo e base

Correção isolada na branch `fix/windows-ciclo-vida`, criada da `develop` em `c2713b9e51fe13bbcc1a10af744645d40dd45cd7` e atualizada para `1b6b12834a8cbbb5e6ed80c9dd8df8d7c7ddf19a` após os merges fiscais #18/#20. Depois do merge contábil #21 na develop, a branch foi sincronizada com `63333a4ceb38e458c6095080e2fd0a5fb208dbea` para validar a versão integrada. A sincronização preserva o commit original da correção e o histórico dos merges, sem duplicar ou reescrever as branches anteriores. A correção não altera esquema, dados ou regras de negócio. Destino de revisão: develop, respeitando o fluxo de merges do projeto. Sem merge, release ou implantação automática.

O usuário relatou abertura seguida de desaparecimento da janela, permanência no tray e encerramento ao interagir com links, atalhos ou pop-ups. A imagem `libfile_5d3bbd31d480819194bec90a5974f74e` não pôde ser materializada: o fluxo suportado retornou `library file transfer failed: download failed`; nenhum byte ou pixel foi inspecionado. Não se conclui nada sobre a imagem pelo seu identificador.

## Fatos e hipótese de falha

Foi confirmado no código anterior que a janela era sempre ocultada, a menos que houvesse `--show-window`; `--background` existia, mas não havia preferência gráfica persistente. O botão de fechar e o ESC global recolhiam a administração. Isso explica o desaparecimento inicial e o comportamento do ESC; não prova a causa de um encerramento real do processo.

O tray executava chamadas Tcl (`root.after`) dentro do WndProc e mantinha um segundo despachante nativo com PeekMessage/DispatchMessage, enquanto Tk já controla a fila da mesma thread. A implementação foi ajustada para impedir essa reentrada e separar ações do callback nativo. Sem reprodução do crash no Windows do usuário, essa condição é tratada como risco identificado no código, não como diagnóstico definitivo de toda falha relatada.

## Mudanças

- Janela visível por padrão; preferência `start_minimized` salva em desktop.json, desmarcada por padrão e independente de `auto_start`.
- `--background` força início minimizado; `--show-window` força janela visível. A janela fica oculta durante a montagem da interface para evitar um lampejo antes da minimização escolhida.
- Preferências de início podem ser salvas com serviço ativo. Alterar banco ou porta ainda exige interromper o serviço; o salvamento não copia/migra bancos e conserva outras chaves da configuração.
- Fechar a administração e **Recolher para a bandeja** apenas ocultam/minimizam a janela. ESC deixa de ter uma ação global de recolhimento, preservando o cancelamento de diálogos.
- `DesktopLifecycle` concentra mostrar, recolher, abrir URL e sair. Somente saída explícita encerra serviço e janela; chamadas repetidas de saída são idempotentes.
- WndProc enfileira ações/erros sem chamar Tk. Um timer Tk drena a fila, captura falhas e não tenta continuar após a saída. O despachante nativo redundante foi retirado. Menus são liberados em finally; o ícone carregado do arquivo tem propriedade local para liberação correta.
- Erro/retorno negativo ao abrir o navegador é informado sem encerrar o aplicativo. Exceções de callbacks e início do serviço têm diagnóstico privado em desktop.log, com até 1 MB por arquivo e duas rotações. Filas da interface continuam sendo atendidas após falhas de uma ação.
- Mantidos GUI/tray, instância única por perfil, servidor loopback, conexão Docker e motor fiscal/contábil.

## Validação

Testes portáveis cobrem preferências/precedência, configuração inválida, preservação do arquivo de dados, ocultar/restaurar sem parar serviço, fallback sem tray, falhas de abertura de navegador, saída idempotente, limpeza após falha de parada e isolamento das ações/erros do WndProc. Os testes existentes continuam exercitando backend real, reinício, persistência, porta ocupada e validação de caminho.

No Windows, `NativeDesktopLifecycleTests` usa Tk/tray reais para restauração por mensagem, janela modal e ESC. O smoke do launcher e do EXE usa perfil e banco descartáveis e quatro inicializações: padrão visível, `--background`, preferência salva e `--show-window` sobre a preferência. Controla somente HWNDs pertencentes ao processo de teste; abre uma segunda instância, fecha a janela com WM_CLOSE e restaura pelo tray, verificando HTTP e processo vivo em cada etapa. Depois confere encerramento explícito, persistência e ausência de console no EXE.

O executor local é Linux e não possui Windows, Wine ou Xvfb. Resultados Linux não comprovam Tk/Win32 nem o EXE. O build Windows x86/x64 e os testes nativos do SHA final são obrigatórios para validar esta alteração de empacotamento; deverão ser registrados com os respectivos links e artefatos. Abertura real de todos os navegadores, diálogos do Windows e ambiente específico do usuário ainda depende de homologação; não se declara o crash eliminado somente pelos testes simulados.

Na primeira validação x64 do PR #22, os testes reais Tk/tray/modal/ESC passaram. O smoke seguinte encontrou uma corrida no próprio teste: quando a janela já estava visível, a condição de restauração podia passar antes de a ação da segunda instância sair da fila; o fechamento subsequente era seguido por essa restauração tardia. A sequência foi ajustada para partir de uma janela recolhida antes de cada restauração, preservando as checagens de estado, processo e HTTP. A implementação do aplicativo não foi alterada para suprimir a falha, e os builds do novo HEAD devem ser acompanhados novamente.

Resultados por SHA, CI e bloqueios de publicação devem ficar no relato final e em `artifacts/validacao-ciclo-vida-windows.md`, sem atribuir builds antigos ao código novo.

Referências de implementação: [modelo de eventos do Tkinter](https://docs.python.org/3.13/library/tkinter.html#threading-model) e [fila de mensagens Win32](https://learn.microsoft.com/en-us/windows/win32/winmsg/using-messages-and-message-queues).
