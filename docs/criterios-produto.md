# Critérios do produto e da distribuição

O objetivo é um produto completo de escrituração fiscal e contábil, com distribuição Windows x86/x64 e fluxos reproduzíveis de build, teste, release, contêiner e implantação. O estado atual deve ser avaliado por evidências; gerar um executável não comprova a conclusão funcional ou a compatibilidade Prosoft.

## Evidências necessárias por entrega

| Área | Evidência exigida para declarar pronta |
|---|---|
| Isolamento e persistência | Testes por empresa/período, reinício, falhas transacionais e migração que preserva originais e histórico |
| Planos e associações | Hierarquia, vigência, versões e origem preservadas; formatos efetivamente fornecidos/testados |
| Conciliação | Fontes e diferenças visíveis, entidades canônicas, casos sem identificadores e decisões versionadas que caducam quando a origem muda |
| Motor contábil | Regras/partidas explicitamente informadas, contas analíticas, mapeamentos aprovados, valores rastreáveis, equilíbrio e bloqueio de duplicidade entre execuções |
| Processamento histórico | Snapshot imutável de fontes, parâmetros e associações; revisão explícita; correção sem sobrescrita de fechado |
| Prosoft | Layouts e versões recebidos, exemplos conferidos e teste real autorizado de ida/retorno com reconciliação. C140/C141/55 exige perfil específico |
| Windows x86/x64 | Builds da mesma revisão e aplicação, dependências fixadas, teste do executável em cada arquitetura, recursos web incluídos, manifesto e checksums dos artefatos reais |
| Contêiner/GHCR | Imagem-base identificada por digest, build e smoke test reais, usuário/permissões/armazenamento definidos, pacote e digest verificados após publicação autorizada |
| Release e implantação | Artefatos originados de revisão identificada, gates e permissões mínimas; instalação/reversão documentadas; teste no destino autorizado |

## Limites de autorização e operação

Este trabalho ocorre no PR em rascunho, sem merge ou deploy de produção. A definição de workflows não autoriza criar credenciais, ampliar acesso persistente ou expor os dados e o servidor local. Publicação de release/pacote e implantação precisam respeitar o alvo e as autorizações efetivas da operação. Não mudar a audiência ou abrir rede para contornar uma limitação de empacotamento.

O servidor atual é monousuário e loopback, com SQLite privado. Binários e contêineres devem preservar esse comportamento. Acesso remoto/multiusuário requer arquitetura e controle de papéis próprios, ainda não comprovados. Segredos não pertencem ao repositório, aos binários, às camadas de imagem ou aos logs de build.

## Insumos que continuam necessários

Layout e exemplos reais Prosoft Fiscal/Contábil; formatos reais de planos; regras contábeis aprovadas; casos de teste autorizados; papéis e revisões de produção; política de retenção; destino de implantação; política de assinatura de executáveis e publicação de pacotes. Não inventar regras fiscais, prazos legais, credenciais, dados de referência ou resultados de homologação.

Cada relatório de etapa deve separar implementação, testes locais, CI, inspeção dos artefatos, validação contra especificação, teste real Prosoft e ferramenta oficial. Falha ou ausência de execução deve ser informada com o alvo e o resultado observado. CBS/IBS permanecem fora da apuração deste produto.
