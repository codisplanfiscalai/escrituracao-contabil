# Integração fiscal e contábil Prosoft

**Status:** esqueleto inicial, somente documentação e contratos sintéticos. Nenhum dado real foi incluído ou enviado.

Este projeto prepara o fluxo entre documentos fiscais, arquivo SPED para importação no Prosoft e lançamentos contábeis com proteção contra duplicidade. Ele não transmite obrigações ao Fisco, não executa o PVA e não grava diretamente no banco de dados do Prosoft.

## Parâmetros fixos deste primeiro cenário

- Competência de referência dos parâmetros: agosto de 2026 (2026-08).
- Competência processada: setembro de 2026 (2026-09).
- A referência parametriza as regras deste cenário; ela não altera a competência dos documentos processados.
- O arquivo fiscal é preparado para importação no Prosoft. A instalação, o leiaute do importador e a seleção de registros ainda precisam ser confirmados.
- O bloco C usa C100. C140/C141 entram somente conforme aplicabilidade do documento e contrato do importador, com no máximo um C140 por documento e C141 por parcela quando o C140 for informado.
- A etapa contábil deve impedir reaplicação do mesmo lote e dos mesmos lançamentos. Importação com resultado incerto exige reconciliação antes de qualquer repetição.

## Segurança de dados

Este repositório contém apenas código, decisões e testes com identificadores fictícios. Nunca adicione XML de NF-e, SPED real, planilhas, dados cadastrais, plano de contas, logs de produção, credenciais, certificados ou arquivos do Prosoft. Os diretórios de entrada, saída e estado devem ficar fora do repositório, em armazenamento local controlado. O .gitignore cobre formatos usuais, mas não substitui revisão antes de cada commit.

## Começar

Execute a suíte sintética com Python 3.10 ou superior, sem dependências externas:

    python -m unittest discover -s tests -v

Leia primeiro docs/escopo-e-aceite.md, docs/fluxo-operacional.md e docs/contabil-sem-duplicidade.md. As pendências que bloqueiam operação real estão em docs/decisoes-e-pendencias.md.

## Fontes de leiaute consultadas

- [Guia Prático EFD-ICMS/IPI, versão 3.1.6](https://sped.rfb.gov.br/estatico/38/22C37BE2CE82F67C1A161538F27551C2D8E7E9/Guia%20Pr%C3%A1tico%20EFD%20-%20Vers%C3%A3o%203.1.6.pdf), referência oficial de registros e hierarquia. A versão aplicável em produção deve ser reconfirmada antes do uso.
- [Alterdata/Prosoft: F677 — geração do registro C100 e filhos](https://novoajuda.alterdata.com.br/prosoft/f677-sped-fiscal-geracao-registro-c100-e-filhos-prosoft-fiscal), referência do próprio fornecedor. A documentação informa C140/C141 para faturas do modelo 01 e alerta para evitar duplicidade nas notas desdobradas. A versão instalada e o contrato efetivo do importador precisam ser testados.

