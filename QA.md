# Verificação dos incrementos persistentes

Data: 2026-11-04. Somente dados e identificadores fictícios.

## Executado localmente

Recorte do primeiro incremento (781a49e). As verificações posteriores constam abaixo.

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

## Conciliação parcial e entidades de cobrança — 2026-11-04

- Base b416a99 revisada; sua CI (run 41862143155) continuava em fila, sem execução/falha disponível durante este incremento. A aprovação de 781a49e não é atribuída a b416a99.
- Fluxo, formatos, migração e aceite registrados em docs/conciliacao-documental.md antes de implementar. Guia oficial 3.2.4 e referência oficial de versão 020 consultados; não houve teste com arquivos reais ou Prosoft.
- 89 testes locais em Python 3.12 passaram: 66 anteriores e 23 adicionais de parser, persistência e HTTP. Cobrem as duas ordens XML/SPED; chave/versão/empresa/período inválidos; valores e datas divergentes; identidade de cobrança ausente, repetida ou alterada; preservação de fontes C140/C141 sem presumir Prosoft; reanálise idempotente; migração 1→2 sem reescrita de originais/documentos; isolamento; persistência; rollback em falha de auditoria; remoção lógica com dependências e prévia desatualizada.
- compileall, node --check e git diff --check passaram.
- Chromium real em 1440×1000 e 390×844: cadastro fictício, períodos agosto/setembro, XML com cobrança, SPED apenas recebido, análise do original salvo, documento coincidente, nova fonte com total divergente, valores e linhas de origem, remoção lógica da fonte divergente com IDs de fatura/parcelas, chave ausente na lista de pendências e persistência após recarregar. Sem erros JavaScript ou overflow horizontal da página. Capturas fictícias inspecionadas internamente.
- Recorte: XML NF-e 4.00/55 e leitura parcial EFD-ICMS/IPI 020/2026 (0000 e C100 regular/55). Sem validação completa dos demais registros, itens, tributos ou arquivo oficial. C140/C141/55 continuam observações pendentes de perfil Prosoft, sem entidades inferidas a partir desses registros.
- Pendentes nesta etapa: resolução humana persistente das divergências e associações de cobrança ambíguas, formatos reais de planos e outras versões SPED, snapshots, motor contábil, perfis/exportadores Prosoft, papéis, restauração/purga e política de retenção. Nenhuma liberação para exportação, homologação Prosoft, PVA, XSD, assinatura ou apuração CBS/IBS.

## Revisão persistente, motor e distribuição — 2026-11-04

- Implementação desta etapa delegada a Astra-6 com esforço alto, conforme solicitado. Fluxos registrados em docs/revisao-e-motor.md antes do código. Objetivo completo e evidências exigidas em docs/criterios-produto.md; o produto ainda não está concluído/homologado.
- 108 testes locais passaram em Python 3.12: 89 anteriores, 17 de revisão/motor/migração e 2 fluxos HTTP adicionais. Incluem caducidade, origem explícita, mapeamentos/vigência/contas, Decimal, equilíbrio e valor da fonte, duas conexões concorrentes, idempotência auditada, versões vinculadas, snapshots imutáveis, correção de fechado bloqueada e remoção de fontes bloqueada. compileall, node --check e git diff --check aprovados.
- Chromium: decisão documental com diferença preservada, rejeição de partidas desequilibradas, prévia de débito/crédito 100.30 com mapeamentos explícitos, revisão e fechamento local, bloqueio de remoção da origem e persistência após recarregar. Captura móvel revelou overflow do snapshot aberto; CSS corrigido e retestado em 390px sem overflow.
- CIs de b416a99 e 4c5b105 confirmadas com todos os jobs Python 3.10/3.12/3.13 aprovados. Infraestrutura publicada em 85cfd3476218cd8330b40fa3f50bad58b00119ae. Contêiner CI run 41868426093 passou 89 testes e smoke; publicação GHCR pulada.
- Primeiro Windows run 41868426157 falhou em x86/x64 antes do build: WinError32 na limpeza de dois testes com conexões SQLite abertas. Correção aplicada aos cinco usos diretos nos testes e ao smoke usando closing, preservando transação e liberação de handles. Necessário conferir o próximo run antes de afirmar artefatos prontos; evidência remota mais recente será registrada no PR.
- Infraestrutura local: actionlint/YAML dos quatro workflows; instalação hash-locked; PyInstaller Linux com smoke do executável congelado; Docker test/final e smoke sem rede, read-only, não root e sem capabilities. Verificador de ZIP rejeitou checksum, SHA fonte e PE incorretos, entradas extras e traversal. Build Windows não é cross-compilado neste Linux; jobs Windows devem verificar cada PE e executar EXE real.
- Nenhum release, pacote GHCR, deployment de produção, credencial ou acesso persistente foi criado. Gates de ambientes GitHub ainda precisam de configuração administrativa; release/GHCR/homologação manual novos dependem da branch padrão. Assinatura Windows, instalador, matriz de SOs, integração real e homologação Prosoft continuam pendentes. A imagem atual é isolada e não oferece UI ao navegador do host.


## Identidade Escritura e evidências de fechamento (04/11/2026)

- Nome provisório Escritura, paleta solicitada, SVGs recebidos na mensagem, favicon e PNG/ICO reproduzíveis. Transferência do ZIP da Library falhou; alternativa SVG explicitamente autorizada.
- Perfil próprio `accounting-evidence-v1`: JSON/CSV/manifesto persistidos, hashes, lote fechado, idempotência, isolamento e auditoria. Esquema 4 transacional; nenhuma saída Prosoft/EFD ou regra fiscal inferida.
- Suíte local de 125 testes da aplicação e 6 testes das ferramentas de distribuição aprovada; inclui 15 novos casos de evidência, 2 HTTP e casos negativos de ícones/visibilidade GHCR. `compileall`, `node --check`, `git diff --check` aprovados.
- Chromium real em 1440 px/390 px: identidade, sete áreas, foco/atalho teclado, MIME de SVG/PNG/ICO, sem overflow de página e sem erro JavaScript. Fluxo fechado fictício gerou/baixou os 3 arquivos, confirmou SHA-256/tamanho, três eventos de disponibilização e persistência após reload. Nenhum dado real usado.
- Ícones verificados por dimensão/CRC e hashes; o teste de recursos PE nos novos EXEs pertence à CI da revisão publicada, ainda a consultar.
- Arquivos contábeis anteriores localizados na Library; bytes ZIP/XLSX não materializados por falha de rede do helper. Ver `docs/insumos-localizados.md`; não declarar leiautes validados.
- Contêiner: alvo de testes executou 125 testes e smoke; imagem final executou smoke sem rede, sem capacidades e com filesystem somente leitura. Node fixado regenerou/verificou os ícones; actionlint aprovou workflows. Nenhuma publicação GHCR, release ou deployment executada.
- Resultados finais de jobs/artefatos são registrados no PR e no handoff da revisão, distinguindo execução local/CI/Prosoft.
