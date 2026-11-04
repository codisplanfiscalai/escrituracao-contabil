# Contábil sem duplicidade

## Identidade e chave idempotente

Cada linha contábil preparada recebe uma chave determinística calculada sobre um contrato canônico, sem incluir valores mutáveis de apresentação:

escopo_empresa_pseudonimo + competencia_processada + chave_documento_origem + versao_mapeamento + grupo_de_lancamento + identificador_de_linha.

A chave é calculada como hash e fica no manifesto de execução local. Ela serve à reconciliação; só deve ser inserida no arquivo de importação se houver campo oficialmente aceito pelo leiaute do Prosoft. A chave não pode depender da ordem de leitura dos arquivos.

O mesmo documento pode gerar várias linhas válidas; por isso, o identificador determinístico da linha/grupo deve distinguir débitos, créditos, rateios ou agrupamentos aprovados sem permitir que uma repetição da mesma linha pareça nova.

## Barreira de repetição

- Antes de importar, verificar se o run_id, hash do manifesto ou chave idempotente já consta como concluído no controle local e, quando disponível, no relatório/consulta do Prosoft.
- A primeira importação exige estado REVISADO, arquivo/hash fixos e operador identificado no controle de execução.
- Só registrar sucesso após evidência do Prosoft e conciliação. Guardar número de linhas e somas de débito/crédito do lote.
- Não repetir automaticamente se houve timeout, fechamento do Prosoft, queda de rede ou ausência de relatório. Primeiro pesquisar no Prosoft se houve lançamento parcial ou integral.
- Se rejeitado comprovadamente, corrigir e criar novo lote ligado à tentativa rejeitada. Não apagar histórico nem reaproveitar o mesmo identificador com conteúdo diferente.
- Correção de lançamento já contabilizado exige fluxo contábil de estorno/ajuste aprovado; não reimportar para sobrescrever.

## Requisitos de conciliação

1. Soma dos débitos igual à soma dos créditos por lote.
2. Totais e contagens do arquivo iguais ao manifesto.
3. Lançamentos do relatório de importação correspondem 1:1 às chaves preparadas, sem extras e sem ausências.
4. Os saldos/contas de contrapartida fecham conforme regra aprovada.
5. Divergência ou chave já existente interrompe o fechamento e exige análise.

O formato de importação contábil, campos de histórico, contas, centros de custo e forma de consultar lançamentos já contabilizados ainda precisam ser definidos com a versão do Prosoft e com o responsável contábil.

