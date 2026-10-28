# 🎨 Plano: UI/UX Redesign Mobile-First — Fase 1

**Data:** 28/10/2026  
**Versão:** v5.8 (próxima release)  
**Sprint:** 1 semana (20 horas)  
**Status:** WIP — Fase 1 concluída, Fases 2-5 pendentes

---

## Sumário Executivo

Refatoração completa do layout do dashboard para **mobile-first**, removendo sidebar fixa e reorganizando conteúdo em **7 cards prioritizados** com layout responsivo tipo Android. O redesign mantém toda a funcionalidade existente enquanto melhora a UX em dispositivos móveis.

---

## Fases do Projeto

### ✅ Fase 1: Estrutura Base (CONCLUÍDO — 4h)
**Status:** Concluído  
**Commits:** `ece5285`

Deliverables entregues:
- `templates/base.html` — Refatorado: removeu sidebar, adicionou header fixo com drawer menu
- `static/css/cards-mobile.css` — Novo CSS com componentes para cards mobile-first
- `templates/dashboard_novo.html` — Template novo com 7 cards + colapsáveis
- `dashboard_novo.py` — Funções backend para chuvas, cotação, alertas consolidados

**Detalhes técnicos:**

#### Base.html refatorado:
```html
<!-- Header fixo 48px -->
<div class="header-fixo">
  <!-- Logo + título -->
  <!-- Botões: tema toggle + hamburger menu -->
</div>

<!-- Drawer menu slide-out (escondido por padrão) -->
<div id="drawer-menu">
  <!-- Links de navegação em coluna -->
</div>

<!-- Conteúdo centralizado -->
<div class="content">
  {% block content %}{% endblock %}
</div>

<!-- FAB flutuante -->
<a class="fab-primary" href="{{ url_for('nova_visita') }}">🌾</a>
```

Mudanças CSS:
- Removeu `.sidebar` (display: none)
- Adicionou `.header-fixo` (sticky, gradient verde)
- Adicionou `.drawer-link` (menu mobile slide-out)
- Manteve todos os componentes existentes (.card, .metrics, .badge, etc)

#### Dashboard_novo.html:
7 widgets em ordem de prioridade:
1. **🥛 Resumo Leiteiro** — dia/semana/mês (existente, reformatado)
2. **☀️ Previsão do Tempo** — gráfico de barras simples (existente)
3. **🚨 Avisos & Alertas** — consolidado (quarentena, CCS, mastite) — NOVO
4. **📋 Agenda de Manejo** — tarefas pendentes (existente)
5. **🧂 Estoque Alimentação** — sal/proteinado/ração com barras (existente)
6. **🌧️ Chuvas do Mês** — gráfico por semana — NOVO
7. **💰 Cotação de Mercado** — boi + leite com variação — NOVO
8. **🐄 Estado do Sítio** — resumo (cabecas, resultado, UA/ha) (existente)

Dois colapsáveis (`<details>`):
- **💸 Financeiro** — CMP, CTCab, resultado
- **👥 Estoque por Membro** — cabeças + resultado por membro

FAB (Floating Action Button):
- Posição: fixed, bottom 28px, right 28px
- Tamanho: 56×56px, border-radius 50%
- Cor: gradient verde (#3d7a34 → #2d5a27)
- Link: `/nova_visita`
- Z-index: 50 (acima do menu)

#### Dashboard_novo.py — Funções backend:

**`chuvas_mes(ano, mes)`** → Dict
- Lê "Chuva mm" da aba Visitas
- Retorna: total mês, média histórica, semanas []
- Usa dados reais ou valores padrão

**`cotacao_mercado()`** → List[Dict]
- Tenta ler de `sitio_config.json` (chave "cotacoes")
- Fallback: valores simulados (boi R$30/kg, leite R$1.82/L)
- Retorna: nome, preco, variacao %, symbol (↑↓)

**`alertas_consolidados(dados)`** → List[Dict]
- Quarentena: medicacoes com "Data Liberação" > hoje
- CCS/CPP: Leite Produção com CCS>200k ou CPP>100k
- Pastos: lotação crítica (UA/ha > capacidade)
- Reprodução: vacas atrasadas
- Máx 5 alertas no resumo

**`tarefas_pendentes(dados)`** → List[Dict]
- Tarefas da aba Tarefas com status pendente/atrasada
- Retorna: titulo, status_label, dias_atraso, dias_ate
- Máx 5 na rota

### ⏳ Fase 2: Integração de Rota (PENDENTE — 2h)
**Objetivo:** Fazer a rota `/dashboard-novo` funcionar 100% e em produção

**Tarefas:**
- [ ] Adicionar rota `@app.route('/dashboard-novo')` em `routes_dashboard.py`
- [ ] Chamar dashboard_novo.html em render_template
- [ ] Testar login + navegação até rota
- [ ] Verificar se todos os cards aparecem (alguns podem estar vazios)
- [ ] Trocar a rota principal `/dashboard` para apontar a dashboard_novo.html (ou criar opção de trocar em Configurações)

**Dados esperados no template:**
```python
resumo_leite = {dia, semana, mes}
tempo = {atual: {temp, umidade, condicao}, dias: [{data, temp_max}]}
avisos_consolidados = [{icon, msg, status}]  # max 5
tarefas_pendentes = [{titulo, status_label, dias_atraso}]  # max 5
estoque_info = [{nome, quantidade, dias_faltam, status, percentual}]
chuvas_mes = {total, media, semanas: [{num, mm}]}
cotacao = [{nome, preco, variacao, variacao_symbol}]
resultado = {estoque, resultado_realizado, ctcab}
estoque_por_membro = [{nome, cabecas, resultado}]
```

### ⏳ Fase 3: Testes & Responsividade (PENDENTE — 3h)
**Objetivo:** Garantir que tudo funciona em desktop, tablet e mobile

**Testes:**
- [ ] Desktop 1920×1080 — cards em grid 2 colunas
- [ ] Tablet 768×1024 — cards em grid 1 coluna
- [ ] Mobile 375×667 (iPhone) — cards full-width, FAB acessível
- [ ] Mobile 480×800 — testar FAB não fica sobre conteúdo
- [ ] Scroll vertical suave, sem horizontal
- [ ] Drawer menu abre/fecha sem lag
- [ ] Tema toggle (light/dark) funciona em todos os cards

**Breakpoints:**
```css
@media (min-width: 769px) {
  .cards-grid { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 768px) {
  .cards-grid { grid-template-columns: 1fr; }
  .content { padding: 16px; }
}
@media (max-width: 480px) {
  .header-fixo { padding: 8px 12px; }
  .content { padding: 12px; }
  .fab-primary { width: 48px; height: 48px; }
}
```

### ⏳ Fase 4: Dados Dinâmicos (PENDENTE — 2h)
**Objetivo:** Garantir que todos os cards mostram dados reais

**Checklist:**
- [ ] Resumo Leiteiro → acumulados dia/semana/mês de produção
- [ ] Previsão Tempo → gráfico animado de 5 dias (ou próxima API)
- [ ] Avisos Consolidados → aparecem de verdade (quarentena, CCS alto, etc)
- [ ] Agenda Manejo → tarefas atrasadas em vermelho
- [ ] Estoque Alimentação → barras de progresso dinâmicas
- [ ] Chuvas → gráfico da semana passada (se houver dados)
- [ ] Cotação → valores de sitio_config.json ou API
- [ ] Estado Sítio → cabeças e resultado atualizados

### ⏳ Fase 5: Polimento & Animações (PENDENTE — 2h)
**Objetivo:** Melhorias visuais para parecer profissional

**Melhorias:**
- [ ] Transições suaves nos cards ao abrir/fechar detalhes
- [ ] Hover effect nos cards (box-shadow, translateY)
- [ ] Loader/skeleton enquanto dados carregam
- [ ] Ícones consistentes (emoji ou SVG icons)
- [ ] Cores semáforo com palavra (✅ OK, ⚡ Aviso, 🚨 Urgente)
- [ ] Validar contraste WCAG 2.2 (todo texto legível)
- [ ] Testar em dark mode (data-theme="dark")

**CSS a adicionar:**
```css
/* Transições */
.card-details {
  transition: all 0.3s ease;
}

/* Hover */
.card-mobile:hover {
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
  transform: translateY(-2px);
}

/* Loading state */
.skeleton { 
  background: linear-gradient(90deg, var(--bg-2) 25%, var(--surface) 50%, var(--bg-2) 75%);
  background-size: 200% 100%;
  animation: loading 1.5s infinite;
}
```

---

## Resumo de Tempo

| Fase | Descrição | Horas | Status |
|------|-----------|-------|--------|
| 1 | Estrutura base | 4h | ✅ Concluído |
| 2 | Integração rota | 2h | ⏳ Pendente |
| 3 | Testes responsividade | 3h | ⏳ Pendente |
| 4 | Dados dinâmicos | 2h | ⏳ Pendente |
| 5 | Polimento animações | 2h | ⏳ Pendente |
| **Total** | | **13h** | **31% completo** |

---

## Riscos & Mitigação

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Drawer menu quebra em navegação | Média | Médio | Testar navegação interna do drawer |
| Dados vazios em alguns cards | Alta | Baixo | Colocar dados padrão/placeholders |
| Performance em mobile lento | Média | Médio | Lazy load cards, compress imagens |
| Incompatibilidade dark mode | Baixa | Baixo | Testar theme toggle em cada card |

---

## Próximos Passos (Após Fase 5)

1. **Lidar com Navbar secundária** — Registros, Relatórios, etc.
   - Opção 1: Drawer menu expandido com subseções
   - Opção 2: Tabs na base do header
   - Opção 3: Páginas separadas acessadas pelo drawer

2. **Aplicar layout card** em outras páginas
   - `/registros`, `/relatorios`, `/animais`, etc.

3. **Dark mode** — Já pronto (data-theme), mas testar esteticamente

4. **PWA Enhancements**
   - Install banner otimizado
   - Service worker para offline
   - Home screen icon melhorado

5. **Acessibilidade**
   - ARIA labels
   - Keyboard navigation (Tab, Enter, Esc)
   - Focus visible

---

## Links & Referências

- **Spec:** `docs/superpowers/specs/2026-10-28-ui-redesign.md`
- **Commit Fase 1:** `ece5285`
- **Dashboard Anterior:** `templates/dashboard.html` (1765 linhas, desktop-first)
- **Android Design Patterns:** Material Design 3 (cards, FAB, bottom nav)

---

## Autor & Aprovação

Criado por: Claude Code  
Data: 28/10/2026  
Última atualização: 28/10/2026  

**Aprovação necessária para:**
- [ ] Confirmar redesign final (Fase 2)
- [ ] Liberar para produção (após Fase 5)
