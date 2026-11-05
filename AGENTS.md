# Escritura - regras de continuidade

- Responder em português do Brasil. Preservar tecnologias e recursos gerais úteis; por instrução explícita do usuário em 05/11/2026, repensar e substituir os processos fiscais/contábeis anteriores, com migração e preservação dos dados. Não usar a preservação do fluxo antigo como requisito.
- Branches de trabalho partem de develop; PRs de implementação retornam a develop.
- Main recebe promoção de develop com título release(patch|minor|major): descrição. Não fazer merge automático.
- VERSION e pyproject.toml devem coincidir; nunca mover tags publicadas ou substituir artefatos estáveis.
- A aplicação Windows é gráfica, com System Tray. Não criar executável operacional de console. Scripts CLI são ferramentas de desenvolvimento/CI.
- Não transportar identidades, nomes ou regras escolares de materiais externos. Não incorporar anexos de referência ao repositório.
- Não incluir documentos reais, bancos, credenciais, arquivos fiscais ou dados privados em Git/CI/releases.
- Não alterar regras fiscais/contábeis por conveniência de infraestrutura. CBS/IBS permanecem fora do cálculo.
- Rodar python scripts/build.py check e os builds pertinentes. Mudança em empacotamento Windows exige CI x86/x64; contêiner exige smoke da imagem efetivamente publicada.
- Validar workflows com actionlint. Não desabilitar checks para publicar.
- Publicação de artefatos não autoriza implantação permanente em produção.
- Relatar testes reais, limitações e resultados de CI separadamente de planos futuros.
