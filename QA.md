# Verificação do primeiro incremento persistente

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
