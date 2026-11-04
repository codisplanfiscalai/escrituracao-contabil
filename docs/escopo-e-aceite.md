# Escopo e critérios de aceite

## Objetivo

Preparar uma integração controlada para importar dados fiscais e contábeis no Prosoft, preservando a separação entre competência de referência de regras (2026-08) e competência processada (2026-09). A primeira entrega é um esqueleto documentado e testável, sem dados da empresa.

## Dentro do escopo

1. Normalizar documentos de uma única competência de processamento por execução.
2. Aplicar regras identificadas pela competência de referência informada.
3. Produzir arquivo fiscal no formato SPED aceito pelo importador Prosoft confirmado.
4. Preparar lançamentos contábeis com chave idempotente e manifesto de execução.
5. Comparar contagens e valores entre entrada, arquivo preparado, relatório do Prosoft e manifesto.
6. Bloquear repetição automática quando o estado da importação for confirmado, iniciado ou incerto.

## Fora do escopo

- Transmitir SPED, EFD ou qualquer obrigação à SEFAZ/RFB.
- Rodar ou alegar aprovação no PVA/validador oficial. Os testes aqui são apenas estruturais e de contrato.
- Acessar ou alterar diretamente banco de dados do Prosoft.
- Inventar regras fiscais, classificação de CFOP/CST/contas ou compensar diferenças sem decisão documentada.
- Colocar XML, SPED, dados pessoais, dados contábeis, certificados ou credenciais reais no GitHub.

## Critérios de aceite do esqueleto

- A configuração registra explicitamente reference_competence=2026-08 e processing_competence=2026-09.
- Uma execução não mistura documentos fora de setembro de 2026.
- A geração fiscal representa C100 e deixa a emissão de C140/C141 condicionada ao documento e ao contrato do importador.
- A contabilidade gera uma chave determinística por linha/posting group, impede colisão na mesma execução e não autoriza reimportação de estado incerto.
- A reconciliação documenta divergências e impede marcar lote como concluído se contagens ou totais não fecharem.
- Testes usam dados fictícios e executam localmente sem dependências externas.
- Nenhum teste é descrito como validação fiscal oficial.

## Fronteira operacional

O operador revisa o arquivo e importa manualmente no Prosoft, usando o ambiente e a rotina definidos pela empresa. A integração registra o hash do arquivo, o lote, o estado e a evidência de importação. Se não houver comprovante confiável de sucesso ou falha, o lote fica em reconciliação manual e não é repetido.

