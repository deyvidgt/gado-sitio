# Plano de Implementação: Gráficos + Cards + Tabelas + UI (v5.8)

**Status:** Em Progresso  
**Data Início:** 2026-10-30  
**Meta:** Integrar 62 inspirações em 4 fases

---

## Fase 1: Gráficos Financeiros (A) ✅

### 1.1 Gauge (Taxas %)
- [x] Criar componente `gauge.js` (SVG semicircular)
- [x] Integrar em `/` — Margem de Lucro, Taxa Serviço
- [x] Cores: 🔴 Vermelho < 30%, 🟡 Amarelo 30-70%, 🟢 Verde > 70%
- [x] Template: `templates/components/gauge.html`

### 1.2 Barras Comparativas
- [ ] Estender `chart.js` com padrão "Minha Fazenda vs Média Mercado"
- [ ] Integrar em `/lotes` — Ganho @/ha, Lucro/ha
- [ ] Cores: Verde claro (Minha), Verde escuro (Mercado)
- [ ] Rota: `/api/comparativo-lotes`

### 1.3 Barras Empilhadas (Custo/Receita/Lucro)
- [ ] Chart.js com stacked bars
- [ ] Integrar em `/lotes` — Destaque do Lote
- [ ] Cores: Verde (receita), Laranja (custo), Azul (lucro)
- [ ] Template: `templates/lotes/destaque.html`

### 1.4 Linhas com Preenchimento (Produção Leite)
- [ ] Chart.js com area fill
- [ ] Integrar em `/leite/comparativo` — Produção acumulada
- [ ] Eixo Y: Litros, Eixo X: Período (dia/semana/mês)
- [ ] Rota: `/api/leite-producao-timeline`

---

## Fase 2: Sistema de Cards KPI (B) ⏳

### 2.1 Componente Card Métrica Reutilizável
- [ ] `templates/components/card-metric.html` (Jinja2)
- [ ] Props: ícone, número, label, cor, trend, ação
- [ ] Exemplo: `425 | Animais Ativos | +2.1% ↑`
- [ ] CSS: `.card-metric`, `.card-metric--verde`, `.card-metric--azul`

### 2.2 KPI Grid Responsivo
- [ ] `static/css/components/kpi-grid.css`
- [ ] 4 colunas desktop, 2 tablet, 1 mobile
- [ ] Integrar em `/` — Painel Principal
- [ ] Métricas: Animais Ativos, Lactação, Dias, Intervalo

### 2.3 Sparkline (Mini-gráficos)
- [ ] Biblioteca leve ou SVG inline
- [ ] Mostrar trend ao lado de KPI ("+1.07% ↑" com gráfico)
- [ ] Rota: `/api/trend-animais`

### 2.4 Cards Compostos (Destaque do Lote)
- [ ] Múltiplas métricas num card
- [ ] Template: `templates/lotes/destaque-composto.html`
- [ ] Exemplo: 4 linhas (Custo Total, Custo Produção, Custo Alimentação, Lucro/Arroba)

---

## Fase 3: Tabelas Responsivas (C) ⏳

### 3.1 Componente Table Responsivo
- [ ] `templates/components/table-responsive.html`
- [ ] Desktop: tabela HTML padrão
- [ ] Mobile: cards-linha (row = card, colunas = linhas)
- [ ] CSS: `.table-responsive`, `.table-row-mobile`

### 3.2 Aplicar em Principais Páginas
- [ ] `/animais` — Tabela de animais
- [ ] `/lotes/dados` — Dados por cabeça (Qtd, Dias, Rendimento, Ganho, GMD, Peso, Preço)
- [ ] `/leite/animais` — Produção por vaca

### 3.3 Filtro/Busca Sticky
- [ ] Busca sempre visível (sticky no mobile)
- [ ] Dropdown de categoria ao lado
- [ ] Filtros avançados colapsáveis

---

## Fase 4: UI Refinements (D) ⏳

### 4.1 Badges Semáforo
- [ ] `static/css/components/badge.css`
- [ ] Sempre com texto + ícone (nunca só cor)
- [ ] Estados: Verde (OK), Amarelo (Aviso), Vermelho (Urgente)
- [ ] Aplicar em: Status animal, alertas, prioridade

### 4.2 Header Sticky + Gradiente
- [ ] Já parcialmente pronto em `base.html`
- [ ] Garantir z-index 100, altura 60px desktop/50px mobile
- [ ] Gradiente: #3d7a34 → #2d5a27

### 4.3 Sidebar Colapsável (Mobile)
- [ ] Menu drawer overlay (<768px)
- [ ] Hamburger icon no header
- [ ] Suavidade de transição (0.22s)
- [ ] Fechar ao swipe/clique fora

### 4.4 FAB (Botão Flutuante)
- [ ] Botão verde fixo no canto inferior direito
- [ ] Desktop: opcional (usar button na toolbar)
- [ ] Mobile: sempre visível
- [ ] Exemplo: "+ Novo Animal"

### 4.5 Modal/Diálogo Padrão
- [ ] Já existe em `components/modal.css`
- [ ] Fullscreen mobile, centered desktop
- [ ] Verificar overlay opacidade (~0.5)

### 4.6 Ícones Flat Customizados
- [ ] SVG sprite ou font icons
- [ ] Padrão: 24x24 / 32x32
- [ ] Exemplos: brinco eletrônico, sanitário, inseminação, diagnóstico, pesagem, cocho

---

## Implementação: Ordem de Execução

### Sprint 1 (Esta semana): 
1. Gauge + Barras Comparativas (Fase 1)
2. Card Métrica + KPI Grid (Fase 2)

### Sprint 2:
3. Linhas + Sparkline (Fase 1)
4. Table Responsivo (Fase 3)

### Sprint 3:
5. Badges + Header/Sidebar refinements (Fase 4)
6. FAB + Ícones (Fase 4)

---

## Arquivos a Criar/Modificar

### Novos Arquivos:
- `static/js/charts-gauge.js` — Gauge SVG
- `static/js/charts-extended.js` — Barras, linhas, sparkline
- `templates/components/card-metric.html`
- `templates/components/gauge.html`
- `templates/components/table-responsive.html`
- `static/css/components/badge.css`
- `static/css/components/kpi-grid.css`
- `static/css/components/gauge.css`

### Modificar:
- `base.html` — Links dos novos CSS, scripts
- `routes_dashboard.py` — Novas rotas para dados de gráficos
- `routes_lotes.py` — Integrar gráficos
- `routes_leite.py` — Integrar linhas de produção
- Templates principais: `/`, `/lotes`, `/leite/comparativo`

---

## Métricas de Sucesso

✅ Todos os gráficos carregam e responsivos  
✅ Cards KPI atualizados em tempo real  
✅ Tabelas funcionam desktop/mobile  
✅ Badges com semáforo em status  
✅ WCAG AA em contraste (4.5:1)  
✅ Performance < 2s em FCP  

---

**Próximo Passo:** Começar Fase 1.1 — Criar gauge.js

