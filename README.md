# Integração fiscal e contábil Prosoft

**Status:** protótipo local persistente com cadastro multiempresa, planos e mapeamentos versionados, documentos e cobrança NF-e 4.00 e conciliação parcial XML × SPED. Nenhum dado real foi incluído ou enviado. Prosoft ainda não homologado.

Este projeto prepara o fluxo entre documentos fiscais, arquivo SPED para importação no Prosoft e lançamentos contábeis com proteção contra duplicidade. Ele não transmite obrigações ao Fisco, não executa o PVA e não grava diretamente no banco de dados do Prosoft.

## Parâmetros configuráveis e cenário inicial

- Competência de referência dos parâmetros: agosto de 2026 (2026-08).
- Competência processada: setembro de 2026 (2026-09).
- A referência parametriza as regras deste cenário; ela não altera a competência dos documentos processados.
- O arquivo fiscal é preparado para importação no Prosoft. A instalação, o leiaute do importador e a seleção de registros ainda precisam ser confirmados.
- A saída planejada inclui C100 e um perfil específico de integração Prosoft para C140/C141 relacionados a modelo 55. O perfil depende do layout e dos exemplos do importador; ainda não há gerador implementado nem compatibilidade validada. Esse requisito não representa uma EFD oficial para modelo 55.
- A etapa contábil deve impedir reaplicação do mesmo lote e dos mesmos lançamentos. Importação com resultado incerto exige reconciliação antes de qualquer repetição.

## Segurança de dados

Este repositório contém apenas código, decisões e testes com identificadores fictícios. Nunca adicione XML de NF-e, SPED real, planilhas, dados cadastrais, plano de contas, logs de produção, credenciais, certificados ou arquivos do Prosoft. Os diretórios de entrada, saída e estado devem ficar fora do repositório, em armazenamento local controlado. O .gitignore cobre formatos usuais, mas não substitui revisão antes de cada commit.

## Começar

Execute com Python 3.10 ou superior, sem dependências externas, a partir da raiz deste projeto:

    python -m src.local_app --database /caminho/privado/escrituracao.sqlite3 --port 8765

Abra http://127.0.0.1:8765. Em Windows, informe por exemplo um caminho privado no seu perfil de usuário. O servidor aceita somente conexões loopback. Use um banco fora do repositório; ele contém dados originais em texto claro e deve ficar em diretório privado, com proteção e backup do sistema operacional. CNPJ é opcional no cadastro, mas importações sem ele permanecem pendentes de conferência de identidade.

Cadastre uma empresa, defina os períodos de parâmetros e movimentos e importe seu plano pelo formulário JSON. As contas requerem code, description, parent_code (ou null), kind (sintetica/analitica), nature (devedora/credora) e attributes (opcional). Cada nova importação com o mesmo nome cria uma versão, sem alterar a anterior. Mapeamentos exigem destino analítico e preservam versões.

Recebimento XML suporta apenas NF-e 4.00 modelo 55, com cabeçalho e faturas/parcelas. Verifica chave/DV, campos de controle e competência de emissão, mas não assinatura, autorização, esquema XSD ou correção fiscal integral. Competência diferente da emissão exige revisão e não é atribuída automaticamente.

SPED pode ser apenas preservado (padrão) ou analisado com o perfil explícito EFD-ICMS/IPI 020, parcial para 2026: cabeçalho 0000 e C100 regular modelo 55. A tela Conciliação compara os campos disponíveis, vincula ambas as fontes ao mesmo documento e mostra diferenças e localizações, sem escolher valores vencedores. Chave ausente, período/empresa divergente e casos fora do recorte ficam em observações pendentes. Coincidência não representa escrituração validada ou liberação de exportação. C140/C141 são somente preservados como registros; não geram faturas modelo 55 sem especificação Prosoft.

Faturas e parcelas extraídas do XML possuem IDs próprios, ligados ao documento e às observações de arquivo/caminho. Referências iguais agregam fontes; valores conflitantes não sobrescrevem os primeiros. Identificadores de cobrança divergentes ficam pendentes de associação, sem criar títulos/parcelas adicionais por suposição. Em Documentos, “Analisar arquivo já salvo” reutiliza os bytes armazenados e registra a tentativa sem duplicar entidades.

O programa não calcula CBS/IBS, não gera partidas ou arquivos de importação Prosoft e não transmite dados. Não existe autenticação multiusuário nem pronto uso em rede/produção. Em Documentos, a remoção lógica apresenta o arquivo, documentos dependentes e consequências; exige motivo e confirmação, preserva o original e a auditoria e deixa os documentos vinculados pendentes. Uma prévia desatualizada é recusada. Purga definitiva e restauração permanecem indisponíveis.

Fatura com valores aritmeticamente divergentes, parcelas sem fatura ou soma das parcelas diferente do líquido ficam pendentes, preservando os valores recebidos. Essas conferências não calculam tributos nem presumem valores ausentes. O normalizador v3 registra também entidades e observações nas novas importações. O esquema 2 adiciona tabelas em transação, sem reescrever originais ou documentos antigos. A indexação de arquivos antigos exige a ação explícita de análise; dados antigos não são liberados automaticamente. Guarde backup privado do SQLite antes de atualizar o programa.

Fluxos A–E, navegação, entidades, permissões e dependências: [mapa funcional completo](docs/mapa-produto.md). Modelo e limites do primeiro incremento: [incremento persistente](docs/incremento-persistente.md).

Escopo de leitura, origem dos perfis, migração e aceite da conciliação: [conciliação documental](docs/conciliacao-documental.md).

Execute a suíte sintética:

    python -m unittest discover -s tests -v

Leia primeiro docs/escopo-e-aceite.md, docs/fluxo-operacional.md e docs/contabil-sem-duplicidade.md. As pendências que bloqueiam operação real estão em docs/decisoes-e-pendencias.md.

## Fontes de leiaute consultadas

- [Guia Prático EFD-ICMS/IPI, versão 3.1.6](https://sped.rfb.gov.br/estatico/38/22C37BE2CE82F67C1A161538F27551C2D8E7E9/Guia%20Pr%C3%A1tico%20EFD%20-%20Vers%C3%A3o%203.1.6.pdf), referência oficial de registros e hierarquia. A versão aplicável em produção deve ser reconfirmada antes do uso.
- [Alterdata/Prosoft: F677 — geração do registro C100 e filhos](https://novoajuda.alterdata.com.br/prosoft/f677-sped-fiscal-geracao-registro-c100-e-filhos-prosoft-fiscal), referência do próprio fornecedor. A documentação informa C140/C141 para faturas do modelo 01 e alerta para evitar duplicidade nas notas desdobradas. A versão instalada e o contrato efetivo do importador precisam ser testados.

