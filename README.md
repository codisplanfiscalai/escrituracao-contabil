# Integração fiscal e contábil Prosoft

**Status:** primeiro incremento executável local: persistência SQLite, cadastro multiempresa, planos e mapeamentos versionados, recebimento de arquivos e normalização parcial de NF-e 4.00. Nenhum dado real foi incluído ou enviado. Prosoft ainda não homologado.

Este projeto prepara o fluxo entre documentos fiscais, arquivo SPED para importação no Prosoft e lançamentos contábeis com proteção contra duplicidade. Ele não transmite obrigações ao Fisco, não executa o PVA e não grava diretamente no banco de dados do Prosoft.

## Parâmetros configuráveis e cenário inicial

- Competência de referência dos parâmetros: agosto de 2026 (2026-08).
- Competência processada: setembro de 2026 (2026-09).
- A referência parametriza as regras deste cenário; ela não altera a competência dos documentos processados.
- O arquivo fiscal é preparado para importação no Prosoft. A instalação, o leiaute do importador e a seleção de registros ainda precisam ser confirmados.
- O bloco C usa C100. C140/C141 entram somente conforme aplicabilidade do documento e contrato do importador, com no máximo um C140 por documento e C141 por parcela quando o C140 for informado.
- A etapa contábil deve impedir reaplicação do mesmo lote e dos mesmos lançamentos. Importação com resultado incerto exige reconciliação antes de qualquer repetição.

## Segurança de dados

Este repositório contém apenas código, decisões e testes com identificadores fictícios. Nunca adicione XML de NF-e, SPED real, planilhas, dados cadastrais, plano de contas, logs de produção, credenciais, certificados ou arquivos do Prosoft. Os diretórios de entrada, saída e estado devem ficar fora do repositório, em armazenamento local controlado. O .gitignore cobre formatos usuais, mas não substitui revisão antes de cada commit.

## Começar

Execute com Python 3.10 ou superior, sem dependências externas, a partir da raiz deste projeto:

    python -m src.local_app --database /caminho/privado/escrituracao.sqlite3 --port 8765

Abra http://127.0.0.1:8765. Em Windows, informe por exemplo um caminho privado no seu perfil de usuário. O servidor aceita somente conexões loopback. Use um banco fora do repositório; ele contém dados originais em texto claro e deve ficar em diretório privado, com proteção e backup do sistema operacional. CNPJ é opcional no cadastro, mas importações sem ele permanecem pendentes de conferência de identidade.

Cadastre uma empresa, defina os períodos de parâmetros e movimentos e importe seu plano pelo formulário JSON. As contas requerem code, description, parent_code (ou null), kind (sintetica/analitica), nature (devedora/credora) e attributes (opcional). Cada nova importação com o mesmo nome cria uma versão, sem alterar a anterior. Mapeamentos exigem destino analítico e preservam versões.

Recebimento XML suporta apenas NF-e 4.00 modelo 55, com cabeçalho e faturas/parcelas. Verifica chave/DV, campos de controle e competência de emissão, mas não assinatura, autorização, esquema XSD ou correção fiscal integral. Competência diferente da emissão exige revisão e não é atribuída automaticamente. SPED é armazenado com contagem de registros e estado pendente: ainda não há normalização/reconciliação XML × SPED.

O programa não calcula CBS/IBS, não gera partidas ou arquivos de importação Prosoft e não transmite dados. Não existe autenticação multiusuário nem pronto uso em rede/produção. A remoção lógica de arquivo tem prévia e confirmação na API do núcleo; purga definitiva e restauração ainda não estão disponíveis na interface.

Fluxo, modelo, estados, aceite e limitações: [primeiro incremento](docs/incremento-persistente.md).

Execute a suíte sintética:

    python -m unittest discover -s tests -v

Leia primeiro docs/escopo-e-aceite.md, docs/fluxo-operacional.md e docs/contabil-sem-duplicidade.md. As pendências que bloqueiam operação real estão em docs/decisoes-e-pendencias.md.

## Fontes de leiaute consultadas

- [Guia Prático EFD-ICMS/IPI, versão 3.1.6](https://sped.rfb.gov.br/estatico/38/22C37BE2CE82F67C1A161538F27551C2D8E7E9/Guia%20Pr%C3%A1tico%20EFD%20-%20Vers%C3%A3o%203.1.6.pdf), referência oficial de registros e hierarquia. A versão aplicável em produção deve ser reconfirmada antes do uso.
- [Alterdata/Prosoft: F677 — geração do registro C100 e filhos](https://novoajuda.alterdata.com.br/prosoft/f677-sped-fiscal-geracao-registro-c100-e-filhos-prosoft-fiscal), referência do próprio fornecedor. A documentação informa C140/C141 para faturas do modelo 01 e alerta para evitar duplicidade nas notas desdobradas. A versão instalada e o contrato efetivo do importador precisam ser testados.

