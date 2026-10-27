# v5.7 Roadmap — Progresso de Sprints

**Status:** Sprint 1 ✅ Completo | Sprint 2-4 📋 Planejado

---

## ✅ Sprint 1: Mobile Refinements (Completo)

**Commit:** `53c192f` — 2026-10-27

### Arquivos Criados
- ✅ `static/css/mobile.css` (235 linhas)
  - Drawer menu toggle com slide-out animation
  - Bottom action bar fixo com scroll hide/show
  - Sticky tabs com border indicator
  - Touch targets ≥44x44px para acessibilidade
  - Long-press context menu
  - Media queries para ≤768px, ≤480px

- ✅ `static/js/gestures.js` (195 linhas)
  - `Gestures` class com métodos:
    - `initDrawer()`: Toggle + swipe-to-close
    - `initSwipe()`: Navegação por swipe left/right
    - `initLongPress()`: Menu de contexto em 500ms hold
    - `initScrollBehavior()`: Scroll-triggered show/hide
  - Auto-init ao carregar página

- ✅ `static/css/dark-mode.css` (207 linhas)
  - CSS custom properties: `--bg-primary`, `--text-primary`, `--accent-green`, etc.
  - `prefers-color-scheme: dark` suportado
  - `data-theme="dark"` override manual
  - Todos os componentes adaptados (.card, .badge, .input, etc.)
  - Chart.js brightness filter

- ✅ `static/js/dark-mode.js` (85 linhas)
  - Detecta preferência de sistema
  - localStorage persistence com chave `gado-theme`
  - `applyTheme(theme)` e `toggle()` métodos
  - Toggle button criado automaticamente

- ✅ `templates/base.html` — Integração
  - Links CSS: `mobile.css`, `dark-mode.css` antes de `</head>`
  - Script `gestures.js` antes de `</body>`
  - Dark mode toggle logic inline

- ✅ `tests/test_v57_mobile.py` (9 testes)
  - Verifica carregamento de CSS/JS
  - Testa existência de arquivos
  - Valida comentários v5.7 em base.html
  - **Status:** 9/9 ✅ Passando

### Testes
```bash
pytest tests/test_v57_mobile.py -v
# 9 passed in 2.15s
```

### Checklist Sprint 1
- [x] CSS drawer com animações suaves
- [x] JavaScript para swipe/gestos
- [x] Dark mode com localStorage
- [x] Integração em base.html
- [x] Testes unitários
- [x] Commit com mensagem detalhada

---

## 📋 Sprint 2: Performance & Offline (Planejado)

**Estimativa:** 3-4 dias | **Meta:** 2026-10-30

### Tarefas
1. **Lazy Loading de Imagens**
   - Implementar `loading="lazy"` em `<img>` tags
   - Intersection Observer para placeholders
   - Arquivo: `static/js/lazy-images.js` (~80 linhas)

2. **Virtual Scroll para Listas**
   - Para tabelas com 100+ linhas
   - Renderizar apenas viewport + buffer
   - Arquivo: `static/js/virtual-scroll.js` (~120 linhas)

3. **Service Worker Melhorado (v2)**
   - Cache strategy: network-first para API, cache-first para assets
   - Offline fallback page com `_offline.html`
   - Pré-cache de críticos (CSS, JS, fonts)

4. **Skeleton Screens**
   - Placeholder enquanto carrega
   - CSS: `.skeleton` com shimmer animation
   - Usar em cards, tabelas, listas

### Arquivos Sprint 2
- `static/js/lazy-images.js` — Lazy load com observer
- `static/js/virtual-scroll.js` — Virtual scroll para listas grandes
- `templates/_offline.html` — Fallback offline
- `static/css/skeleton.css` — Skeleton screens com shimmer
- `static/sw.js` v2 — Service worker melhorado
- `tests/test_v57_performance.py` — Testes de performance

---

## 📋 Sprint 3: Design System Components (Planejado)

**Estimativa:** 2-3 dias | **Meta:** 2026-10-31

### Tarefas
1. **Modal Component**
   - Template macro: `templates/macros/modal.html`
   - Focus trap + ESC para fechar
   - Backdrop click handling

2. **Toast Notifications**
   - `static/js/toast.js` — Fila de notificações
   - Auto-dismiss após 4s
   - Animação de slide-in/out

3. **Accordion Component**
   - Expand/collapse com animação
   - Só 1 item aberto por vez (opcional)
   - Acessível com aria-expanded

4. **Accessible Color + Text**
   - Converter _todos_ os semáforos (aviso/ruim/ok)
   - Adicionar ícones + texto (não só cor)
   - WCAG 2.1 AA de contraste em tudo

### Arquivos Sprint 3
- `templates/macros/modal.html` — Modal component
- `static/js/modal.js` — Modal logic
- `static/js/toast.js` — Notificações
- `static/css/accordion.css` — Accordion styles
- `templates/macros/badge.html` — Badge com ícone + texto
- `tests/test_v57_a11y.py` — Accessibility tests

---

## 📋 Sprint 4: UX Improvements (Planejado)

**Estimativa:** 2-3 dias | **Meta:** 2026-11-02

### Tarefas
1. **Confirmação de Ação Destrutiva**
   - Modal para delete/reset/logout
   - Botão de confirmação com delay (3s)
   - Atalho teclado: Enter para confirmar

2. **Loading States**
   - Botões com spinner durante POST/PATCH
   - Desabilitar após click
   - Aria-busy + aria-label dinâmico

3. **Paginação Inteligente**
   - Lazy load mais itens ao chegar no final
   - Sem carregamento infinito (máx 500 itens)
   - Estado "Carregando..." visível

4. **Search + Filter UX**
   - Debounce 200ms
   - Clear button quando houver texto
   - Placeholder dinâmico por contexto

5. **Mobile Navigation Bottom Tabs**
   - Tab bar fixo no bottom em mobile
   - Ativo com highlight
   - Máx 5 abas (overflow em drawer)

### Arquivos Sprint 4
- `static/js/confirm-modal.js` — Confirmação
- `static/js/loading-state.js` — Loading spinners
- `templates/pagination.html` — Pagination inteligente
- `templates/filter-bar.html` — Filter/search component
- `static/css/bottom-tabs.css` — Mobile bottom tabs
- `tests/test_v57_ux.py` — UX tests

---

## 🎯 Métricas de Sucesso

| Métrica | Meta | Status |
|---------|------|--------|
| Lighthouse Performance | ≥85 | 📊 A medir (Sprint 2) |
| Lighthouse Accessibility | ≥90 | 📊 A medir (Sprint 3) |
| Offline Funcionalidade | ✅ Ler cache | 📋 Sprint 2 |
| Touch Targets | ≥44x44px | ✅ Sprint 1 |
| Dark Mode | Completo | ✅ Sprint 1 |
| Testes | ≥95% cobertura | 📊 Em andamento |

---

## 📅 Timeline

```
Sprint 1: ✅ 2026-10-27 (Mobile Refinements)
Sprint 2: 📋 2026-10-28 — 2026-10-30 (Performance & Offline)
Sprint 3: 📋 2026-10-31 (Design System)
Sprint 4: 📋 2026-11-01 — 2026-11-02 (UX)

Release v5.7.0: 2026-11-03
```

---

## 🔗 Referências

- **Documentação:** `docs/superpowers/plans/2026-10-27-v57-roadmap.md`
- **V5.6 Features:** `docs/FEATURES_V56.md`
- **Commits:** Branch `develop` com tags por sprint
- **CI/CD:** `.github/workflows/tests.yml` (Lighthouse em `/tempo`, `/calendario`)

