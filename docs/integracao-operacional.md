# Integração operacional local e servidor

Branch de integração criada sobre `develop` `35a00e0`, sem merge, release ou implantação.
Integra os incrementos contábil `3b904db`, interface `4567072` e distribuição `1e2fcc0`.

## Fluxo disponível

1. Cadastre empresa, competências de referência e dos movimentos e uma versão do plano.
2. Receba XML/SPED, confira as fontes e registre a decisão documental. A referência de agosto pode ter movimentos em setembro; uma não substitui a outra.
3. Prepare a ficha fiscal a partir de uma origem ou informe uma ficha manual. Salve e revise explicitamente a versão fiscal. Esta decisão não produz partidas contábeis.
4. Use as partidas documentais com mapeamentos aprovados ou o lançamento contábil manual por conta analítica. Informe data, grupo, D/C, valor e histórico. Cada evento deve equilibrar por data e grupo.
5. Confira o snapshot, revise e feche. Edições de lançamentos manuais abertos criam versões; fechados permitem estorno vinculado, também sujeito a revisão e fechamento.
6. Em **Livros e exportações**, selecione período e plano para consultar diário, razão e balancete dos movimentos fechados. Preserve o pacote e baixe JSON, CSV e manifesto com hashes. A leitura verifica os arquivos preservados e o navegador confere SHA-256/tamanho antes do download. Uma mudança posterior nos movimentos não modifica exportações anteriores.
7. Em **Financeiro**, registre títulos a pagar/receber, com referência, contraparte, vencimento e valor. Registre baixas parciais ou integrais por data, referência e motivo. O saldo não pode ficar negativo. Estorne baixas incorretas e cancele títulos sem baixas vigentes, preservando o original e o histórico. Baixe o relatório CSV do recorte selecionado.

As atividades usam o mesmo iframe no portal. Rascunhos contábeis manuais e de títulos ficam separados por usuário, empresa e competência, recuperáveis na sessão do navegador; as versões salvas ficam no SQLite. As guias fiscais têm persistência própria no banco. Trocar empresa/competência recarrega os dados do contexto selecionado. Uma falha ao salvar a guia fiscal impede a navegação e mantém o contexto.

## Financeiro e permissões

O financeiro usa valores decimais textuais, transações SQLite `BEGIN IMMEDIATE`, chaves de tentativa e hashes de estado. Pedidos repetidos com a mesma chave não duplicam registros; conteúdo diferente exige outra chave. Baixa e estorno sobre estado desatualizado são recusados. Operações simultâneas não podem consumir o mesmo saldo.

Rotas compartilhadas pelo HTTP local e portal:

| Rota | Operação | Permissão no portal |
| --- | --- | --- |
| `finance-titles` | GET/POST consultar/criar | `workspace.read` / `workspace.write` |
| `finance-settlements` | POST baixar | `workspace.write` |
| `finance-reversal` | POST estornar baixa | `workspace.review` |
| `finance-cancel` | POST cancelar título | `workspace.review` |
| `finance-file` | GET CSV atual | `workspace.read` |

O portal exige autenticação, escopo de empresa e CSRF nas mutações. Os atores e motivos ficam na auditoria. O HTTP local é privado, restrito a loopback, com token local. O banco migra versões 1–7 para 8 de forma aditiva, preservando cadastros e movimentos existentes.

Títulos são informados explicitamente. Não se inferem pagamento, recebimento, liquidação bancária, direção financeira nem vínculo contábil pela mera presença de duplicata no XML. Baixas financeiras não criam partidas; o operador pode registrar partidas manuais separadas com referência ao título. O relatório financeiro CSV é gerado do estado atual; os livros têm exportações preservadas próprias. Colunas textuais CSV recebem prefixo apóstrofo para preservar códigos e impedir interpretação de fórmulas.

## Limites comprovados

- Diário/razão/balancete são livros locais de **movimentos**, sem saldos iniciais, demonstrações estatutárias completas, registro/autenticação de livros ou transmissão.
- Não há arquivo de importação Prosoft ou SPED contábil homologado. Os layouts reais retornaram HTTP 403 no ambiente de pesquisa anterior; a integração não tentou contornar essa restrição. É necessário fornecer leiautes e exemplos autorizados e validar no sistema de destino/PVA antes de disponibilizar esses formatos.
- CBS/IBS continuam fora do cálculo. Os valores fiscais informados ou recebidos não representam apuração tributária homologada.
- Não há integração bancária, conciliação bancária automática, juros/descontos/câmbio de baixa nem contabilização automática do financeiro.
- Rascunhos manuais/financeiros ainda não salvos dependem da sessão do navegador. Sair limpa a recuperação; salve a prévia ou título para persistência durável.
- O incremento de recepção em lote/organização aguarda commit remoto autorizado da frente responsável. A presente evidência de ponta a ponta usa a recepção XML individual existente.
- 7z/RAR no Windows congelado e RAR5/comprimido permanecem sem validação/homologação da frente de importação.

## Verificações reproduzíveis

Somente dados gerados por código, em diretórios temporários fora do Git:

```sh
python scripts/build.py check
python qa/integrated_flow.py
python qa/workspace_navigation.py
python qa/browser_context_regression.py
python qa/fiscal_browser.py
actionlint
python scripts/build.py container --proxy-ca /etc/ssl/certs/ca-certificates.crt
```

Os testes de navegador exigem Playwright e Chromium no ambiente de QA. O teste integrado executa portal e HTTP local e verifica cadastro/plano/mapeamentos, XML, ficha fiscal/revisão, decisão documental, lote documental, lançamento manual com edição/revisão/fechamento/estorno, livros/exportação/download/hash, títulos/baixas parciais e integrais/estorno/cancelamento/CSV, persistência em SQLite e ausência de erros JavaScript. Também confere larguras de 1440, 768, 390 e 320 px. O teste de navegação cobre recuperação de rascunhos e falha de salvamento; o de contexto cobre atraso e falha de rede sem ação sobre lote antigo.

Build e smoke locais de contêiner não equivalem ao smoke de imagem publicada. Nenhuma imagem foi publicada por esta integração. Mudanças de empacotamento aguardam CI Windows x86/x64 e os gates do commit integrado antes de qualquer promoção. Não foram solicitados merge automático, release ou implantação.
