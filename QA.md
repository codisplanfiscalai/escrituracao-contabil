# Verificação dos incrementos persistentes

Data: 2026-11-04. Somente dados e identificadores fictícios.

## Executado localmente

- Python 3.12: `python -m unittest discover -s tests -v` — 60 testes passaram (8 contratos existentes, 46 persistência/parser, 6 HTTP).
- `python -m compileall -q src tests` — passou.
- `node --check src/web/app.js` — passou.
- Cobertura: persistência entre conexões/servidores, isolamento por empresa, hierarquia e atomicidade de planos, versões/vigência de mapeamento, valores Decimal, identidade/chave/DV NF-e, datas com fuso, fatura/parcelas, DTD/entidades, arquivos repetidos e conflitantes, preservação de originais, SPED pendente, remoção lógica auditada, versão desconhecida de banco, Host/Origin/token, limites HTTP, allowlist e cabeçalhos de segurança.

## Não executado ou não comprovado

- Chromium não iniciou por restrição de socket do ambiente (`Operation not permitted`). Nenhuma página foi carregada pelo teste visual; não houve contorno dessa restrição.
- Python 3.10/3.13 ainda não executados localmente. Workflow CI contempla essas versões e 3.12; o resultado remoto deve ser consultado no commit publicado.
- Sem importação no Prosoft, sem homologação de layout, sem PVA, sem documentos reais, sem validação fiscal completa ou de assinatura/autorização NF-e.
- Não há motor de lançamentos, exportador fiscal/contábil Prosoft ou reconciliação documental XML × SPED neste incremento.

Nenhum resultado local equivale a validação fiscal oficial ou pronto uso em produção. Consulte docs/incremento-persistente.md para limites e próximos passos.

## Revisão independente e segundo incremento — 2026-11-04

- Prompt integral recebido por mensagem de contexto depois da falha de download do anexo; a cópia original da Library não foi materializada. Fluxos completos e dependências registrados em docs/mapa-produto.md antes de alterar o núcleo nesta etapa.
- Commit-base revisado: 781a49ee988db0ca4ae1f07d61b579510b476fd7, PR #1 em rascunho. Reproduzidos os 60 testes, compileall e node --check. Confirmados os jobs remotos aprovados Python 3.10, 3.12 e 3.13 no run 41860945413.
- Após as alterações: 66 testes locais passaram em Python 3.12; compileall, node --check e git diff --check passaram. Seis regressões adicionais cobrem IDs textuais HTTP, duas fontes NF-e equivalentes, aritmética de faturas, parcelas sem fatura, prévia de remoção desatualizada, confirmação/motivo/isolamento e repetição da remoção.
- Chromium headless funcionou neste ambiente. Exercitado fluxo real de tela em 1440×1000 e 390×844: cadastro fictício, referência agosto/2026 e movimentos setembro/2026, plano hierárquico, mapeamento aprovado fictício, duas representações XML da mesma NF-e sem duplicar documento, prévia e remoção lógica confirmada, e persistência após recarregar. Sem erros JavaScript e sem overflow horizontal da página móvel; tabelas possuem rolagem própria. Capturas inspecionadas apenas como evidência interna, sem dados reais.
- O bloqueio Chromium relatado na etapa anterior pertence ao ambiente anterior; não bloqueou este teste.
- Não houve migração de esquema, reescrita retroativa de documentos nem purga. O normalizador v2 registra alertas de cobrança nas novas importações. Resultado antigo é preservado; diferença de conteúdo/normalização continua exigindo conferência.
- Mantidos os limites: SPED apenas recebido, sem conciliação XML × SPED; títulos/parcelas ainda no payload, sem entidades próprias; sem snapshots/motor de lançamentos/exportadores; sem autenticação por função; sem teste Prosoft, PVA, XSD ou validação fiscal oficial.
