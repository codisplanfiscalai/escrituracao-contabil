# Identidade visual Escritura

Nome provisório solicitado pelo responsável do produto. Símbolo e ícone SVG recebidos diretamente na mensagem de execução; preservados em `src/web/assets/symbol.svg` e `icon.svg`. O pacote de referência foi localizado na Library, mas sua transferência para este ambiente falhou. A alternativa de usar esses SVGs foi expressamente autorizada. A identidade visual é própria da aplicação.

Paleta: azul-petróleo `#064D5D`, verde `#08A45B`, cinza `#86A1A6`, branco. O petróleo orienta texto, botões e foco; verde marca detalhes e seleção; cinza serve como apoio visual. Textos auxiliares usam tom escuro derivado para legibilidade. O verde não recebe texto branco pequeno: esse par teria contraste insuficiente.

A marca aparece no cabeçalho, título do navegador, favicon SVG/ICO, PNG para atalhos e recurso de ícone Windows. O símbolo junto ao nome tem alternativa vazia para evitar leitura duplicada. Interface mantém controles nativos, navegação por teclado, foco visível e atalho para o conteúdo.

Verificação local executada em Chromium: desktop 1440 px e tela 390 px; logo carregado, sete áreas navegáveis, sem erro JavaScript e sem overflow horizontal da página. Tabelas e navegação conservam rolagem interna. SVG, PNG e ICO responderam com MIME correto; tentativa de caminho fora da lista de arquivos permitidos continua bloqueada. Contrastes calculados: petróleo/branco 9,43:1; texto auxiliar/branco 5,97:1; texto principal/fundo 11,20:1. Esta conferência não equivale a auditoria completa de acessibilidade ou teste com leitor de tela.

Geração dos tamanhos PNG/ICO, dependências fixadas, verificação e integração de empacotamento estão descritas em [distribuicao.md](distribuicao.md). O resultado efetivo dos novos executáveis deve ser conferido na CI da revisão publicada; testes de uma revisão anterior não validam o novo ícone.
