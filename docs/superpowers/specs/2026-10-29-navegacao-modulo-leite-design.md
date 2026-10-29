# Navegação do módulo leiteiro

- **Data:** 2026-10-29
- **Status:** proposta para revisão

## Objetivo

Tornar a navegação do módulo leiteiro previsível no computador e no celular, com retorno contextual, atalhos entre áreas relacionadas e gesto opcional de deslizar da borda esquerda para a direita. A mudança é exclusivamente de experiência de uso: não altera cálculos, estrutura do Excel ou contratos de gravação.

## Escopo

Abrange as telas `leite*.html` e seus fluxos relacionados:

- painel do leite;
- ordenha e operações;
- lista e ficha individual de animais;
- alimentação, necessidades, nutrição, consumo e calculador;
- tratamentos, conforto, colchão, saúde;
- relatórios, exportação e comparativo;
- edição de registros.

O escopo inclui um fragmento Jinja compartilhado, estilos mínimos e um script JavaScript próprio, sem dependências novas.

## Experiência de navegação

### Cabeçalho contextual

Cada tela leiteira terá um cabeçalho de navegação com:

1. breadcrumb textual curto, identificando o caminho atual;
2. botão de retorno contextual visível e acessível;
3. atalhos compactos para as áreas principais do módulo, com rolagem horizontal no celular quando necessário.

Destinos padrão:

| Tela | Retorno |
|---|---|
| painel | — |
| ordenha e operação | painel |
| lista de animais | painel |
| ficha individual | lista de animais |
| alimentação | painel |
| necessidades, nutrição e consumo | alimentação |
| calculador | alimentação |
| tratamentos, conforto, saúde e colchão | painel |
| relatórios e comparativo | painel |
| edição de produção | ordenha |

Os links serão gerados com `url_for`, e ações de formulário permanecerão separadas da navegação. O retorno não usará `window.history.back()` como destino principal, para evitar sair do módulo ou reabrir uma página de formulário.

### Gesto no celular

O script será carregado somente nas páginas que incluírem o fragmento. Ele observará `pointerdown`, `pointermove` e `pointerup` e só ativará o retorno quando todas estas condições forem satisfeitas:

- viewport considerada móvel, até 768px;
- início nos primeiros 24px da borda esquerda;
- deslocamento horizontal para a direita de pelo menos 72px;
- deslocamento horizontal maior que o vertical;
- o alvo não for `input`, `textarea`, `select`, `button`, `a`, `[contenteditable]`, mapa ou elemento com rolagem horizontal;
- não houver formulário alterado na página.

Durante o movimento, será exibida uma indicação não bloqueante (`← Solte para voltar`). Ao completar, o script navegará para o mesmo destino contextual do botão de retorno. Se a condição não for atendida, o gesto será cancelado sem alterar a tela. O script não implementará ações destrutivas, gravação ou exclusão por gesto.

O script não tentará substituir o gesto nativo de voltar do navegador quando este assumir o controle. Eventos serão tratados com `passive: false` apenas quando necessário, sem bloquear rolagem vertical normal.

### Formulários alterados

Antes de navegar por gesto em uma página com formulário modificado, o script não navegará. O botão visível continuará disponível, e o usuário poderá usar os mecanismos existentes da página. Não será introduzido diálogo global nesta etapa.

## Implementação

- `templates/_leite_nav.html`: fragmento com parâmetros opcionais de título, seção, destino e rótulo; atalhos do módulo.
- `static/leite_nav.js`: gesto mobile, indicação visual, detecção de formulário alterado e navegação contextual.
- `templates/base.html`: estilos pequenos e genéricos apenas se o fragmento precisar de tokens não existentes; o arquivo não receberá lógica leiteira.
- templates leiteiros: inclusão do fragmento com o destino adequado, preservando as ações e conteúdo existentes.
- `tests/test_leite_integracao.py` ou novo teste dedicado: presença dos destinos, carregamento do script, retorno contextual e integridade das rotas GET.

Não haverá nova rota Flask, nova dependência, nova aba na planilha ou alteração de dados.

## Acessibilidade e responsividade

- O botão de retorno terá texto, não apenas ícone.
- O aviso do gesto será `aria-live="polite"` e não dependerá somente de cor.
- Atalhos serão links reais, navegáveis por teclado.
- O gesto será complemento, nunca o único meio de voltar.
- O layout não poderá criar rolagem horizontal da página; apenas a faixa de atalhos poderá rolar no celular.

## Testes e verificação

1. Testar todas as rotas leiteiras GET existentes.
2. Verificar que cada template usa o destino contextual correto.
3. Verificar que o fragmento inclui o script e os atributos necessários.
4. Testar o script com cenários de gesto válido, gesto vertical, início fora da borda, campo de formulário e formulário alterado.
5. Executar a suíte completa `python -m pytest -q`.
6. Fazer inspeção visual em viewport móvel e desktop, se o ambiente permitir.

## Fora do escopo

- substituir a navegação global do sistema;
- criar PWA offline para o gesto;
- gesto de voltar em telas não leiteiras;
- alterar histórico do navegador;
- redesenhar os gráficos ou cálculos do painel;
- alterar colunas, dados ou finanças.
