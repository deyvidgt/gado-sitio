# Navegação do módulo leiteiro Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tornar a navegação do módulo leiteiro consistente no computador e no celular, com retornos contextuais, atalhos e gesto seguro de deslizar da borda esquerda.

**Architecture:** Um fragmento Jinja compartilhado renderizará breadcrumb, botão de retorno e atalhos; cada template fornecerá seu destino contextual por `url_for`. Um script JavaScript isolado, carregado pelo fragmento, cuidará apenas do gesto mobile e da indicação visual, sem criar rotas ou alterar dados.

**Tech Stack:** Flask/Jinja2, HTML/CSS existente em `base.html`, JavaScript vanilla, pytest e cliente de testes Flask.

**Spec:** `docs/superpowers/specs/2026-10-29-navegacao-modulo-leite-design.md`

## Global Constraints

- Não alterar cálculos, estrutura do Excel, colunas, dados ou contratos de gravação.
- Não adicionar dependências externas ou novas rotas Flask.
- O retorno contextual será feito por links reais gerados com `url_for`, não por `window.history.back()`.
- O gesto só vale em viewport até 768px, iniciado nos primeiros 24px, com deslocamento horizontal mínimo de 72px e maior que o vertical.
- O gesto não pode atuar sobre campos, controles, mapas, elementos com rolagem horizontal ou formulários alterados.
- O botão visível de retorno permanece disponível e o gesto é complementar.
- A página não terá rolagem horizontal; somente a faixa de atalhos poderá rolar no celular.
- Toda alteração será verificada com a suíte completa `python -m pytest -q`.

## Review Focus

- Tela com formulário parcialmente preenchido: o gesto deve cancelar sem perder os dados; coberto por `test_gesture_does_not_navigate_when_form_dirty` em `tests/test_leite_nav.js`.
- Deslize vertical começando na borda: deve preservar a rolagem e não navegar; coberto por `test_vertical_gesture_is_ignored`.
- Toque/deslize iniciado em input, select, botão, link ou editor: deve ser ignorado; coberto por `test_interactive_targets_are_ignored`.
- Início longe da borda ou deslocamento menor que 72px: deve ser ignorado; coberto por `test_gesture_requires_edge_and_threshold`.
- Ficha individual, edição e subáreas: devem apontar para suas páginas-pai corretas; coberto por `test_contextual_back_links` em `tests/test_leite_integracao.py`.

---

### Task 1: Criar o fragmento de navegação leiteira

**Files:**
- Create: `templates/_leite_nav.html`
- Modify: `templates/base.html` somente se forem necessários estilos genéricos pequenos para o fragmento
- Test: `tests/test_leite_integracao.py`

**Interfaces:**
- Consumes: `url_for` e variáveis Jinja fornecidas por cada página: `leite_secao`, `leite_breadcrumb`, `leite_voltar_url`, `leite_voltar_label`.
- Produces: bloco HTML com classe `leite-nav`, link `[data-leite-back]`, atributo `data-leite-back-url`, breadcrumb e atalhos reais do módulo.

- [ ] **Step 1: Escrever testes de integração falhando**

Adicionar verificações para painel, alimentação, consumo, ficha animal e edição: presença de `.leite-nav`, link de retorno contextual e destinos esperados; verificar que a resposta inclui `static/leite_nav.js`.

- [ ] **Step 2: Rodar os testes novos para confirmar a falha**

Run: `python -m pytest tests/test_leite_integracao.py -q`
Expected: FAIL porque os templates ainda não renderizam o fragmento nem os atributos.

- [ ] **Step 3: Implementar `templates/_leite_nav.html` e incluir o fragmento nos templates leiteiros**

Usar um único fragmento com atalhos para painel, ordenha, vacas, alimentação, saúde, tratamentos, conforto, colchões, relatórios e comparativo. Usar `url_for` nos links. Para necessidades, nutrição, consumo e calculador, o retorno será alimentação; para ficha individual, lista de animais; para edição, ordenha; para demais páginas, painel. Preservar os botões e formulários atuais.

- [ ] **Step 4: Rodar os testes de integração**

Run: `python -m pytest tests/test_leite_integracao.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add templates tests/test_leite_integracao.py
git commit -m "feat(leite): add contextual module navigation"
```

### Task 2: Implementar o gesto mobile sem dependências

**Files:**
- Create: `static/leite_nav.js`
- Modify: `templates/_leite_nav.html`
- Test: `tests/test_leite_nav.js` ou teste equivalente executável pelo ambiente já disponível

**Interfaces:**
- Consumes: `[data-leite-back]`, `[data-leite-back-url]`, formulário da página e eventos Pointer Events.
- Produces: navegação para o destino do atributo, indicador `aria-live="polite"` e nenhum efeito quando as condições não forem atendidas.

- [ ] **Step 1: Escrever testes falhando para as condições do gesto**

Testar: gesto válido na borda navega; início fora da borda ignora; deslocamento menor que 72px ignora; movimento vertical ignora; alvo interativo ignora; formulário alterado cancela; viewport acima de 768px ignora.

- [ ] **Step 2: Rodar os testes para confirmar a falha**

Run: comando do executor JavaScript disponível no projeto para `tests/test_leite_nav.js`; se não houver executor configurado, validar a parte estática com pytest e manter os cenários no teste de integração.
Expected: FAIL antes do script existir ou antes dos listeners serem registrados.

- [ ] **Step 3: Implementar o comportamento em `static/leite_nav.js`**

Registrar listeners apenas quando o fragmento existir. Guardar a posição inicial, cancelar quando o movimento vertical dominar, ignorar alvos interativos/mapas/rolagem horizontal, mostrar a indicação durante um gesto elegível e redirecionar apenas no `pointerup` válido. Detectar formulário alterado comparando valores atuais com valores iniciais e não bloquear rolagem vertical normal.

- [ ] **Step 4: Rodar os testes do gesto e revisar o JavaScript**

Run: teste JavaScript ou `python -m pytest -q` com os cenários integrados.
Expected: todos os cenários passam; nenhum erro de sintaxe.

- [ ] **Step 5: Commit**

```bash
git add static/leite_nav.js templates/_leite_nav.html tests
git commit -m "feat(leite): add safe edge swipe navigation"
```

### Task 3: Cobrir todas as telas e consistência visual

**Files:**
- Modify: todos os `templates/leite*.html` que ainda não incluírem o fragmento
- Modify: `templates/base.html` apenas para CSS reutilizável necessário
- Test: `tests/test_leite_integracao.py`

**Interfaces:**
- Consumes: fragmento e convenções das Tasks 1–2.
- Produces: todas as telas leiteiras com navegação consistente e retorno contextual correto.

- [ ] **Step 1: Ampliar a matriz de testes das telas leiteiras**

Incluir ordenha, operação, animais, ficha, alimentação, necessidades, calculador, tratamentos, conforto, colchão, relatórios, comparativo, saúde, consumo, nutrição e edição. Verificar retorno esperado por tela e que todas incluem a navegação.

- [ ] **Step 2: Rodar a matriz para identificar telas restantes**

Run: `python -m pytest tests/test_leite_integracao.py -q`
Expected: falhas apenas nas telas ainda sem fragmento.

- [ ] **Step 3: Inserir o fragmento nas telas restantes e ajustar classes responsivas**

Manter o CSS existente, usar a faixa de atalhos com rolagem horizontal própria no celular e não alterar conteúdo operacional. Garantir texto visível no botão e `aria-label`/`aria-live` no indicador.

- [ ] **Step 4: Rodar a matriz completa**

Run: `python -m pytest tests/test_leite_integracao.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add templates tests/test_leite_integracao.py
git commit -m "feat(leite): standardize navigation across dairy screens"
```

### Task 4: Verificação final e revisão do diff

**Files:**
- Test: suíte completa do projeto

- [ ] **Step 1: Revisar o diff e confirmar que não há alterações de dados ou dependências**

Run: `git diff --stat` e `git diff --check`.
Expected: somente templates, JavaScript, testes e documentação especificados; sem whitespace errors.

- [ ] **Step 2: Executar a suíte completa**

Run: `python -m pytest -q`
Expected: exit code 0 e todos os testes passando; warnings externos devem ser reportados sem mascarar falhas.

- [ ] **Step 3: Fazer inspeção visual em desktop e celular**

Abrir as telas leiteiras em viewport desktop e até 768px. Confirmar que o cabeçalho não cria overflow, os atalhos podem rolar horizontalmente e o gesto não impede rolagem vertical.

- [ ] **Step 4: Atualizar o changelog**

Adicionar uma entrada em `CHANGELOG.md` na seção `[Não lançado]`, descrevendo a navegação contextual e o gesto mobile, sem mencionar detalhes internos desnecessários.

- [ ] **Step 5: Commit final de documentação e verificação**

```bash
git add CHANGELOG.md docs/superpowers/specs/2026-10-29-navegacao-modulo-leite-design.md docs/superpowers/plans/2026-10-29-navegacao-modulo-leite.md
git commit -m "docs(leite): document navigation improvements"
```
