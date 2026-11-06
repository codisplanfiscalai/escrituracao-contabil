# Decisões e pendências

Registro histórico do escopo inicial de integração. Para o estado atual da aplicação integrada, cobertura dos PRs e plano restante, consulte [Estado da estrutura fiscal](estado-estrutura-fiscal.md).

## Decisões registradas

- **D-001 — Repositório isolado:** projeto separado dos demais no repositório privado escolhido pelo usuário; publicar somente estrutura sintética.
- **D-002 — Sem dados reais no Git:** apenas contratos, código e testes sintéticos podem entrar no controle de versão.
- **D-003 — Datas do cenário:** parâmetros de referência 2026-08; competência processada 2026-09.
- **D-004 — Fiscal:** arquivo SPED preparado para importar no Prosoft, com C100 e C140/C141 conforme tipo de documento e requisitos confirmados do importador; sem transmissão ou validação oficial.
- **D-005 — Contábil:** barreira de idempotência, manifesto, reconciliação e pausa obrigatória se resultado for incerto.

## Pendências que bloqueiam operação real

1. Versões exatas do Prosoft Fiscal e Contábil, rotinas de importação, leiautes e relatórios de confirmação.
2. Origem/formato dos dados de entrada, convenção de pastas locais e retenção segura.
3. Regras fiscais e contábeis aprovadas, parâmetros de referência efetivos de agosto de 2026 e mapeamentos para SP.
4. Campos reais disponíveis para deduplicação e consulta pós-importação no Prosoft.
5. Versão oficial do Guia Prático aplicável ao ambiente/período e validações locais exigidas pelo responsável.

