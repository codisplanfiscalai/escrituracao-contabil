# Escritura

Portal corporativo de organização contábil com aplicativo Windows gráfico, autenticação, administração e serviços Docker.

- [Portal, primeiro acesso e instalação](docs/portal-corporativo.md)
- [Fluxo main/develop, builds, releases e limpeza](docs/fluxo-desenvolvimento.md)
- [Arquitetura e preservação funcional](docs/arquitetura-consolidada.md)


**Windows gráfico:** abra o EXE para administrar a aplicação pela janela e pelo ícone na área de notificação, sem terminal. Fechar/ESC recolhe a janela; Sair encerra o serviço.

**Desenvolvimento:** main/develop, SemVer, builds x86/x64 e Docker, pré-release contínua, release estável e manutenção de cache. [Fluxo e scripts completos](docs/fluxo-desenvolvimento.md). [Arquitetura e integração incremental](docs/arquitetura-consolidada.md).


**Status:** produto em desenvolvimento, com aplicação local persistente, cadastro multiempresa, planos e mapeamentos versionados, documentos e cobrança NF-e 4.00, conciliação parcial XML × SPED, revisão persistente e motor de partidas explícitas com editor assistido, associações de cobrança, evidências de fechamento e identidade visual Escritura. Nenhum dado real foi incluído ou enviado. Integração e homologação Prosoft permanecem pendentes.

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

No Windows, extraia o ZIP completo e abra `EscrituracaoContabil.exe`. Inicie o serviço na janela, copie a chave do primeiro acesso e abra o portal para cadastrar o administrador. A operação diária usa interface gráfica e ícone na área de notificação.

Para servidor Docker, use as configurações de `deploy/` e siga [instalação do portal](docs/portal-corporativo.md). O acesso compartilhado usa HTTPS, autenticação e escopo por empresa. Dados e chaves ficam em volume persistente, com backup privado.

Para desenvolvimento com Python 3.10 ou superior:

    python -m pip install --only-binary=:all: --require-hashes -r requirements-server.txt
    python -m src.server.runtime --host 127.0.0.1 --database /caminho/privado/escrituracao.sqlite3

Abra http://127.0.0.1:8765 e configure o administrador com a chave em `identity/setup.token`, junto do banco informado. O módulo local anterior permanece para compatibilidade e testes, mas o aplicativo distribuído e o contêiner iniciam o portal autenticado.
Cadastre uma empresa, defina os períodos de parâmetros e movimentos e importe seu plano pelo formulário JSON. As contas requerem code, description, parent_code (ou null), kind (sintetica/analitica), nature (devedora/credora) e attributes (opcional). Cada nova importação com o mesmo nome cria uma versão, sem alterar a anterior. Mapeamentos exigem destino analítico e preservam versões.

Recebimento XML suporta NF-e/NFC-e 4.00 modelos 55/65, com cabeçalho e faturas/parcelas quando presentes. Verifica chave/DV e campos estruturais, mas não assinatura, autorização, esquema XSD ou correção fiscal integral. A competência escolhida é independente da emissão; emissão anterior e destinatário anônimo da NFC-e geram avisos de conferência.

SPED pode ser apenas preservado (padrão) ou analisado com o perfil explícito EFD-ICMS/IPI 020, parcial para 2026: cabeçalho 0000 e C100 modelos 55/65, situações 00/01/06/07. A tela Conciliação compara os campos disponíveis, vincula ambas as fontes ao mesmo documento e mostra diferenças e localizações, sem escolher valores vencedores. Chave ausente, período/empresa divergente e casos fora do recorte ficam em observações pendentes. Coincidência não representa escrituração validada ou liberação de exportação. C140/C141 são somente preservados como registros; não geram faturas modelo 55 sem especificação Prosoft.

Faturas e parcelas extraídas do XML possuem IDs próprios, ligados ao documento e às observações de arquivo/caminho. Referências iguais agregam fontes; valores conflitantes não sobrescrevem os primeiros. Identificadores de cobrança divergentes ficam pendentes, sem criar títulos/parcelas adicionais por suposição. Em Conciliação, a associação explícita aceita apenas XMLs do mesmo contexto, com identificadores presentes, valores/vencimentos iguais e correspondência completa 1:1; exige prévia, motivo e confirmação. Originais e diferenças ficam preservados; a decisão versionada exige nova revisão documental. Casos incompletos, aritmética ou valores divergentes continuam bloqueados. [Contrato de associação](docs/associacao-cobranca.md). Em Documentos, “Analisar arquivo já salvo” reutiliza os bytes armazenados e registra a tentativa sem duplicar entidades.

A tela [Lançamento fiscal](docs/escrituracao-fiscal-manual.md) reúne entradas, saídas e serviços manuais, com guias persistentes por operador, inclusão/edição versionada, revisão e proteção de períodos fechados/exportados. Terceiros são localizados por CPF/CNPJ, com papéis e divergências de nome preservados. É uma ficha de cabeçalho: não substitui livros completos, apuração municipal de ISS, importação NFS-e ou geração de SPED. [Handoff deste incremento](docs/handoff-fiscal.md).

O programa não calcula CBS/IBS, não gera arquivos de importação Prosoft e não transmite dados. O portal possui autenticação multiusuário e isolamento por empresa; a implantação em rede exige a configuração HTTPS documentada e a homologação operacional do ambiente. Em Documentos, a remoção lógica apresenta o arquivo, documentos dependentes e consequências; exige motivo e confirmação, preserva o original e a auditoria e deixa os documentos vinculados pendentes. Uma prévia desatualizada é recusada. Fontes de documentos vinculados a lotes fechados ou fichas de períodos fiscais protegidos têm remoção bloqueada. Purga definitiva e restauração permanecem indisponíveis.

Na Conciliação, registre a fonte escolhida, o motivo e a conferência explícita. A decisão tem versão e fingerprint das fontes; mudanças tornam a decisão caduca e mantêm as diferenças visíveis. Em Contabilização local, use o editor assistido para escolher documentos revisados e mapeamentos aprovados/vigentes, consultar fontes e informar as partidas. Os totalizadores usam centavos inteiros; contas e contrapartidas não são sugeridas automaticamente. O modo JSON avançado permanece disponível. Rascunhos não enviados ficam somente na página e são limpos ao trocar empresa/período; prévias salvas persistem. [Contrato do editor](docs/editor-partidas.md). O motor exige contas analíticas, valores decimais textuais, datas dos movimentos, equilíbrio por grupo/documento/lote e total correspondente à fonte escolhida. Não escolhe contas ou tratamentos fiscais automaticamente.

Cada prévia reserva um único evento documental por empresa/documento, guarda snapshot imutável e exige revisão antes do fechamento local. Repetições são idempotentes e auditadas; correções criam versões vinculadas. Fechado não é sobrescrito nem recontabilizado: estornos, pagamentos/recebimentos e eventos adicionais ainda não estão implementados. Fechamento local não significa escrituração importada ou homologada no Prosoft. Fluxo e limites: [revisão e motor](docs/revisao-e-motor.md).

Em um lote fechado, use “Preparar evidências do fechamento” e informe o motivo. Os downloads `evidence.json`, `postings.csv` e `manifest.json` preservam o snapshot histórico; a aplicação confere hashes e registra cada disponibilização no histórico. Repetir reutiliza os mesmos arquivos. Esse perfil próprio não é importação Prosoft nem EFD. [Contrato de evidências](docs/evidencias-contabeis.md).

Fatura com valores aritmeticamente divergentes, parcelas sem fatura ou soma das parcelas diferente do líquido ficam pendentes, preservando os valores recebidos. Essas conferências não calculam tributos nem presumem valores ausentes. O normalizador v3 registra também entidades e observações nas novas importações. O esquema 5 adiciona tabelas em transação, sem reescrever originais ou documentos antigos. A indexação de arquivos antigos exige a ação explícita de análise; dados antigos não são liberados automaticamente. Guarde backup privado do SQLite antes de atualizar o programa.

Fluxos A–E, navegação, entidades, permissões e dependências: [mapa funcional completo](docs/mapa-produto.md). Modelo e limites do primeiro incremento: [incremento persistente](docs/incremento-persistente.md).

Escopo de leitura, origem dos perfis, migração e aceite da conciliação: [conciliação documental](docs/conciliacao-documental.md).

Distribuição Windows x86/x64, dependências fixadas, manifestos/checksums, imagem Docker e workflows de release/GHCR/homologação: [instalação e distribuição](docs/distribuicao.md). Os builds precisam de execução e verificação dos artefatos no Actions; definir o workflow não comprova que os binários estão prontos. Push em develop produz pré-release contínua; promoção em main produz release estável. Publicação de artefatos não implanta serviços em produção. [Critérios para conclusão do produto](docs/criterios-produto.md) distinguem funcionalidades, distribuição e homologação real.

Identidade, favicon e ícone Windows: [identidade visual](docs/identidade-visual.md). Os [insumos já localizados na Library](docs/insumos-localizados.md) incluem plano e pacotes Prosoft; sua transferência ainda não permitiu validar novos leiautes. Não é necessário pedir novamente esses arquivos como se não tivessem sido enviados.

Execute a suíte sintética:

    python -m unittest discover -s tests -v

Leia primeiro docs/escopo-e-aceite.md, docs/fluxo-operacional.md e docs/contabil-sem-duplicidade.md. As pendências que bloqueiam operação real estão em docs/decisoes-e-pendencias.md.

## Fontes de leiaute consultadas

- [Guia Prático EFD-ICMS/IPI, versão 3.1.6](https://sped.rfb.gov.br/estatico/38/22C37BE2CE82F67C1A161538F27551C2D8E7E9/Guia%20Pr%C3%A1tico%20EFD%20-%20Vers%C3%A3o%203.1.6.pdf), referência oficial de registros e hierarquia. A versão aplicável em produção deve ser reconfirmada antes do uso.
- [Alterdata/Prosoft: F677 — geração do registro C100 e filhos](https://novoajuda.alterdata.com.br/prosoft/f677-sped-fiscal-geracao-registro-c100-e-filhos-prosoft-fiscal), referência do próprio fornecedor. A documentação informa C140/C141 para faturas do modelo 01 e alerta para evitar duplicidade nas notas desdobradas. A versão instalada e o contrato efetivo do importador precisam ser testados.


## Importação em lote

XML, SPED e pacotes podem ser recebidos em lote com originais preservados, resultados por arquivo e rastreabilidade. Consulte [operação, limites e disponibilidade real de ZIP/7z/RAR](docs/importacao-em-lote.md).
