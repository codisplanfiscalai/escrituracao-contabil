# Validação local da reformulação — 05/11/2026

Branch `refactor/fiscal-accounting-journey`, criada de `develop` em `e85c425`. Sem publicação, merge, release ou implantação. Somente código, documentação e testes sintéticos; originais fiscais, bancos e anexos reais não foram incorporados.

## Diferenças concretas

| Antes | Agora |
| --- | --- |
| Competência necessária para importar | Caixa de entrada recebe sem competência/plano; organização é decisão posterior |
| Revisão documental → ficha fiscal → lote contábil → título avulso | Uma operação versionada reúne fatos fiscais, partidas e cobrança; uma conferência e efetivação transacional |
| Baixa financeira sem partidas no livro principal | Liquidação é evento próprio no mesmo livro; estorno mantém os vínculos |
| Livros de movimentos sem abertura | Abertura declarada ou zero expressamente confirmado, continuidade de saldos e financeiro por competência |
| Tela fiscal e editores contábeis independentes | Uma ficha para origem importada, lançamento manual, folha informada, abertura, liquidação e ajustes |
| Guias limitadas a parte do menu | Os 18 recursos do menu abrem em guias; formulários se mantêm ao alternar |
| Rascunhos dependentes da sessão do navegador | Fichas incompletas persistidas no banco por usuário/empresa/competência, com controle de versão |
| Repetir gravação manual após resposta incerta podia criar outra operação | Tentativa durável consultada antes de repetir; recuperação também após recarga |
| Interface operacional anterior incluída no pacote | Scripts e estilos antigos retirados; novos escritores substituem os anteriores, que retornam 410 |

## Resultados executados

`python scripts/build.py check`: **239 testes da aplicação**, **18 de distribuição/desktop** (um teste específico de DPAPI não se aplica ao Linux) e **27 dos auxiliares de CI**. Também passaram compilação Python/JavaScript, verificação dos templates pré-compilados, contas decimais, ícones e smoke do launcher com autenticação/CSRF, banco externo e reinício.

- `qa/portal_browser.py`: primeiro acesso, login/logout, empresa sem códigos obrigatórios Prosoft, usuários, configurações, mobile, restrição por perfil e recebimento no portal do cliente sem período.
- `qa/workspace_navigation.py`: os 18 recursos em guias, mesmo iframe, usuários preservados ao consultar perfis, rascunhos separados por empresa/mês, contexto de cliente independente, recarga, falha de gravação bloqueando navegação e recuperação de resposta perdida após o servidor confirmar a gravação. Confirma uma única operação após recuperar. Larguras 1440/1024/768/390/320 sem extravasamento horizontal da página.
- `qa/fiscal_browser.py`: plano CSV com atributos/original, competência-base distinta, serviço manual com ISS informado, conferência/escrituração/livro fiscal e estorno vinculado em outra competência, com saldos reconciliados, e retomada de guia fiscal antiga sem alterar seu conteúdo original.
- `scripts/smoke_import_ui.py`: ZIP com XML válido e erro individual, sem plano/período, consulta de decisões/versionamento, download byte a byte do pacote original e recarga.
- `qa/integrated_flow.py`: **local e portal autenticado**, pela interface real: recepção → organização → operação com parcelas → conferência → escrituração → abertura explícita → rascunho recuperado após recarga e reaberto do Histórico → liquidação parcial → JSON baixado → encerramento. Verifica quatro movimentos, um documento fiscal, três operações e nenhum registro nos escritores fiscais/contábeis antigos.
- `tests/test_work_application.py`: 15 cenários novos, incluindo XML/SPED no mesmo documento, fonte escolhida explicitamente, alteração de fonte invalidando conferência, versões, concorrência, rollback dos efeitos, estorno financeiro/contábil, retomada única de lançamento e de guia fiscal antiga pertencente ao operador, exportações preservadas e migração do esquema 9 mantendo original, livro e ficha fiscal fechados. Período anteriormente exportado não reabre silenciosamente.
- `actionlint`: sem erros nos workflows existentes. Nenhum check foi desligado.

Cobertura medida **somente pelos 15 testes do novo domínio**, com branches, nos quatro módulos de fontes/domínio/livros/store: **75%** agregados (`source_evidence` 62%, `work_domain` 70%, `work_store` 79%, `work_books` 86%). Não é cobertura de toda a aplicação: API e JavaScript não foram instrumentados nessa medição; as verificações HTTP e de navegador têm os escopos descritos acima. Os testes históricos dos métodos internos continuam verificando preservação/migração; seus fluxos de gravação HTTP antigos foram substituídos pelos novos cenários e pela checagem explícita de 410.

Guias de operação encerradas permanecem no Histórico do proprietário e podem ser reabertas com o conteúdo preservado. Rascunhos anteriores não retomados aparecem no encerramento e exigem reconhecimento explícito quando pendentes.

## Limites da evidência

Base sintética, sem homologação fiscal/contábil em ambiente real. A migração de uma cópia privada do banco do usuário permanece por conferir. O fechamento implementado é mensal e operacional; não faz apuração, encerramento anual ou transmissão. O livro fiscal contém fatos de cabeçalho e valores informados; não é uma escrituração tributária integral por item nem um arquivo EFD oficial.

Não foi possível materializar `geradorsped-main.zip` pelo helper autorizado da Library (`hosted apps tools/list request failed: network`). Nenhum código desse ZIP foi lido ou reaproveitado nesta reformulação. Leiautes reais tiveram HTTP 403 e não houve contorno. Importador/exportador Prosoft e gerador SPED oficial continuam bloqueados por perfis/evidência insuficientes. Plano PDF, NFS-e, cálculo de folha/tributos, CBS/IBS, conciliação bancária e homologação RAR5/comprimido não são implementações desta entrega.

O pacote Windows foi atualizado para os novos recursos, mas **os builds nativos x86/x64 deste código ainda não foram executados**. Resultados da CI anterior não validam esta branch. A autorização anterior de envio/PR referia-se à integração já incorporada em develop; não foi reutilizada para publicar o redesenho. Nenhum resultado local comprova imagem publicada ou implantação de produção.


## Revisão posterior das guias

A auditoria ampliada encontrou exceções além do menu: editores de usuário/perfil modais e consultas de fonte em um painel único. Essas aberturas foram substituídas por guias, com correções no roteamento e nos contextos. Consulte a [auditoria de navegação](auditoria-navegacao-guias.md) para o inventário, os caminhos e os testes específicos desta revisão. Os resultados de build e contêiner anteriores não devem ser confundidos com validação nativa Windows do código posterior.
