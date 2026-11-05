# Integração operacional local e servidor

Branch de integração criada sobre `develop` `35a00e0`, sem merge, release ou implantação.
Integra os incrementos contábil `3b904db`, interface `4567072`, distribuição `1e2fcc0` e importação `f814ef2`.

## Fluxo disponível

1. Cadastre empresa, competências de referência e dos movimentos e uma versão do plano.
2. Receba XML/SPED individuais ou em lote, incluindo ZIP; confira os resultados por arquivo, os originais e os produtos/terceiros observados. Depois confira as fontes e registre a decisão documental. A referência de agosto pode ter movimentos em setembro; uma não substitui a outra.
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

O portal exige autenticação, escopo de empresa e CSRF nas mutações. Os atores e motivos ficam na auditoria. O HTTP local é privado, restrito a loopback, com token local. O banco migra versões 1–8 para 9 de forma aditiva. A convergência contempla as duas frentes que usaram versão 7 (contábil ou importação) e a versão 8 com financeiro. Há teste que preserva originais de pacotes e produtos, snapshots fechados, exportações byte a byte e baixas financeiras, além de verificar as chaves estrangeiras.

Títulos são informados explicitamente. Não se inferem pagamento, recebimento, liquidação bancária, direção financeira nem vínculo contábil pela mera presença de duplicata no XML. Baixas financeiras não criam partidas; o operador pode registrar partidas manuais separadas com referência ao título. O relatório financeiro CSV é gerado do estado atual; os livros têm exportações preservadas próprias. Colunas textuais CSV recebem prefixo apóstrofo para preservar códigos e impedir interpretação de fórmulas.

## Limites comprovados

- Diário/razão/balancete são livros locais de **movimentos**, sem saldos iniciais, demonstrações estatutárias completas, registro/autenticação de livros ou transmissão.
- Não há arquivo de importação Prosoft ou SPED contábil homologado. Os layouts reais retornaram HTTP 403 no ambiente de pesquisa anterior; a integração não tentou contornar essa restrição. É necessário fornecer leiautes e exemplos autorizados e validar no sistema de destino/PVA antes de disponibilizar esses formatos.
- CBS/IBS continuam fora do cálculo. Os valores fiscais informados ou recebidos não representam apuração tributária homologada.
- Não há integração bancária, conciliação bancária automática, juros/descontos/câmbio de baixa nem contabilização automática do financeiro.
- Rascunhos manuais/financeiros ainda não salvos dependem da sessão do navegador. Sair limpa a recuperação; salve a prévia ou título para persistência durável.
- 7z/RAR no Windows congelado e RAR5/comprimido permanecem sem validação/homologação da frente de importação.

## Verificações reproduzíveis

Somente dados gerados por código, em diretórios temporários fora do Git:

```sh
python scripts/build.py check
python qa/integrated_flow.py
python scripts/smoke_import_ui.py
python qa/workspace_navigation.py
python qa/browser_context_regression.py
python qa/fiscal_browser.py
actionlint
python scripts/build.py container --proxy-ca /etc/ssl/certs/ca-certificates.crt
```

Os testes de navegador exigem Playwright e Chromium no ambiente de QA. O teste integrado executa portal e HTTP local e verifica cadastro/plano/mapeamentos, lote misto de ZIP com XML e arquivo inválido, produto observado, download do pacote original byte a byte, ficha fiscal/revisão, decisão documental, lote documental, lançamento manual com edição/revisão/fechamento/estorno, livros/exportação/download/hash, títulos/baixas parciais e integrais/estorno/cancelamento/CSV, persistência em SQLite e ausência de erros JavaScript. Também confere larguras de 1440, 768, 390 e 320 px. O teste de navegação cobre recuperação de rascunhos e falha de salvamento; o de contexto cobre atraso e falha de rede sem ação sobre lote antigo.

Build e smoke locais de contêiner não equivalem ao smoke de imagem publicada. Nenhuma imagem foi publicada por esta integração. Mudanças de empacotamento aguardam CI Windows x86/x64 e os gates do commit integrado antes de qualquer promoção. Não foram solicitados merge automático, release ou implantação.

## Resultado da integração com importação

Na suíte combinada, 234 testes da aplicação passaram. A verificação de empacotamento tem 18 testes, com um teste DPAPI condicionado a Windows; as ferramentas CI têm 27 testes. Os fluxos Chromium de importação local/cliente, navegação, fiscal e contexto foram executados separadamente dos testes Python.

A cobertura de linhas abaixo foi medida com `coverage.py 7.10.7`, executando a suíte Python inteira com `--source=src`, sem instrumentar o navegador ou os processos filhos nativos:

| Módulo | Linhas executáveis | Não executadas | Cobertura |
| --- | ---: | ---: | ---: |
| `archive_reader.py` | 187 | 32 | 83% |
| `batch_import.py` | 144 | 8 | 94% |
| `product_catalog.py` | 52 | 3 | 94% |
| `manual_accounting.py` | 180 | 16 | 91% |
| `accounting_books.py` | 126 | 9 | 93% |
| `finance.py` | 143 | 9 | 94% |
| `persistence.py` | 461 | 11 | 98% |
| `local_app.py` | 319 | 47 | 85% |
| `server/app.py` | 254 | 35 | 86% |
| **Subtotal destes nove módulos** | **1866** | **170** | **91%** |

Esse subtotal não é cobertura global do produto nem cobertura JavaScript. O corpo de inicialização do filho libarchive não entra nessa medição; o teste funcional Linux de 7z e RAR4 armazenado passou. Isso não comprova RAR5, RAR comprimido ou suporte no Windows congelado. A interface foi verificada funcionalmente em Chromium, sem medição percentual de linhas JavaScript.
