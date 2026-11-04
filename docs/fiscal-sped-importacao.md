# Fiscal: SPED para importação no Prosoft

## Limite funcional

O objetivo desta etapa é preparar um arquivo SPED para **importação no Prosoft**. Não transmitir ao SPED/SEFAZ, não executar o PVA e não declarar o arquivo validado. O nome do produto, módulo, versão, rotina e leiaute de importação precisam ser registrados antes do teste de integração.

## Registros do cenário

- **C100:** registro de documento fiscal dentro da abrangência confirmada do importador.
- **C140:** dados da fatura comercial quando aplicável e aceito pelo importador.
- **C141:** uma ocorrência para cada parcela vinculada a C140, se o registro e os dados forem aplicáveis.

O Guia Prático EFD-ICMS/IPI descreve C140 como fatura para documentos modelo 01/1A e exige C141 quando C140 for informado. A orientação do Prosoft consultada também alerta para apresentar apenas um C140 por nota fiscal desdobrada e um C141 por parcela, para evitar duplicidade. Isso é uma base documental, não substitui confirmação do importador instalado. Referências e links estão no README.

## Regras de geração e barreiras

1. Criar um C100 por documento fiscal elegível, segundo o contrato do importador.
2. Para C140/C141, verificar cumulativamente: o modelo/tipo é aceito, existe fatura/parcelamento aplicável, os campos obrigatórios estão disponíveis e o importador espera esse registro.
3. Não gerar C141 sem C140; não repetir C140 por desdobramento; garantir identificador de parcela único no documento.
4. Se registros do importador diferirem do padrão oficial, manter o adaptador e sua versão separados, documentados e aprovados. Nunca alterar silenciosamente sem registro de decisão.
5. Rejeitar documento cuja chave de identidade colida com outro documento. Guardar exceção para revisão em armazenamento controlado.
6. Comparar quantidade de documentos, soma de valores e contagens por situação antes/depois da conversão. Diferenças interrompem a importação.

## O que os testes cobrem

Os testes verificam contratos do projeto com entradas sintéticas: competência, presença/condicionalidade dos registros, ausência de duplicatas e totais de controle. Não reproduzem todas as regras da escrituração nem validam arquivo oficial. O primeiro teste com Prosoft deve ocorrer em ambiente autorizado e com dados exclusivamente sintéticos, após confirmação do módulo e do importador.

