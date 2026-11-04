# Insumos localizados e limites de leitura

Consulta à Library em 04/11/2026 antes de pedir novamente arquivos ao usuário. A pasta `Contabil` contém:

| Arquivo | Resultado da inspeção |
|---|---|
| `PLANOCONTAS0050.PDF` | PDF de 649 páginas; primeiras 24 páginas lidas como texto extraído pela Library. Há colunas Acesso, Classificador, Nome da Conta e outros atributos. Classificador se repete entre contas com acessos distintos; não pode ser usado como chave única. Não houve importação completa nem validação dos bytes do PDF. |
| `CLI INTEGRACAO.XLSX` | Localizado; leitura textual não disponível. Não foi possível conferir células, abas, fórmulas ou leiaute. |
| `Prosoft.zip` | Localizado; conteúdo não legível pelo leitor textual. Leiautes internos e versões ainda não confirmados. |
| `DIX ESTILO.zip` | Localizado; conteúdo não legível pelo leitor textual. Competências e tipos internos ainda não confirmados. |
| `DIX_092026_Pacote_Integracao_Prosoft.zip` | Localizado; item gerado anteriormente. Nome não demonstra homologação nem especificação oficial. Conteúdo interno não conferido. |
| `RAZAO ANALITICO.PDF` | Localizado por metadados; conteúdo não inspecionado nesta etapa. |

A materialização pelo fluxo atual da Library falhou antes de obter os arquivos: o helper de download não conseguiu acessar a listagem de ferramentas do serviço (`hosted apps tools/list request failed: network`). Não houve transferência alternativa nem publicação de originais, dados reais ou conteúdo contábil no repositório. A leitura textual disponível do plano é referência de estrutura, não amostra de teste autorizada.

Consequência: os arquivos existem e não precisam ser solicitados novamente como se nunca tivessem sido enviados. É necessário tornar a transferência autorizada funcional para verificar os ZIPs/XLSX e documentar seus contratos. Até isso ocorrer, permanecem indisponíveis novos perfis Prosoft fiscal/contábil, especialmente C140/C141 para modelo 55. Dados de teste continuam fictícios; não se deduz natureza contábil, conta, vigência ou hierarquia a partir de nomes.

Perfis implementados seguem seus limites documentados: NF-e 4.00 cabeçalho/cobrança parcial; EFD-ICMS/IPI 020 C100 parcial; plano JSON próprio; evidências contábeis próprias. Evidência JSON/CSV não substitui arquivo Prosoft, EFD oficial ou validação em ferramenta oficial.
