# Entrada assistida de partidas — contrato

O operador seleciona documento já revisado, consulta a fonte escolhida e seu total, informa grupo/data/lado/valor/histórico e escolhe explicitamente um mapeamento aprovado vigente do plano. Nenhuma conta, contrapartida, valor ou tratamento fiscal é sugerido automaticamente. O editor visual comporta até 200 linhas; JSON avançado preserva o limite de 10000 do servidor. Duas linhas vazias iniciam o editor; adicionar/remover linhas só altera o rascunho em memória.

Totalizadores locais usam centavos inteiros com BigInt, inclusive valores acima da precisão segura de Number. Mostram débitos, créditos, diferença e grupos por documento. Não substituem as validações transacionais do servidor, a reserva do evento, revisão e fechamento. Valores monetários continuam strings no JSON enviado.

A entrada JSON anterior permanece em modo avançado explícito. Trocar de modo não importa nem grava dados; copiar linhas visuais para JSON ou carregar JSON nas linhas exige ação explícita. Erro ao carregar deve preservar o rascunho anterior. Fonte/mapeamento desatualizados aparecem como indisponíveis, sem substituir a escolha silenciosamente. Mudança de empresa/período limpa o rascunho para evitar envio sob contexto diferente; essa consequência é mostrada no formulário. Troca de plano preserva demais campos e torna mapeamentos incompatíveis indisponíveis.

O identificador de tentativa é gerado localmente, pode ser informado pelo operador e é preservado em repetições. Uma ação explícita pode gerar nova tentativa; ela não libera reservas existentes. Recarregar a página perde o rascunho não enviado, enquanto prévias salvas continuam no banco.

Aceite: fluxo completo de partidas sem digitar IDs/JSON; linhas equilibradas por documento/grupo, fontes e contas visíveis, valores exatos, origem caduca recusada, erro preserva campos, troca de contexto não carrega dados da empresa anterior e interface utilizável em tela estreita. JSON anterior, API e snapshots mantêm o contrato existente.
