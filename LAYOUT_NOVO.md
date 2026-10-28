# 🎨 Layout Novo - Dashboard Redesenhado (v5.6+)

## Implementação Máxima das Sugestões

### ✅ O que foi proposto:

1. **📋 Reorganização por Prioridade**
   - Resumo Leiteiro (🥛) → TOPO (antes de Tempo)
   - Pastos + Composição (🌿 🐄)
   - Tarefas da Semana (📋)
   - Financeiro → **COLAPSÁVEL** (economiza espaço)

2. **💰 Financeiro Colapsável**
   ```html
   <details class="card-detail" style="margin-bottom:24px" open>
     <summary style="background:var(--bg-2)">
       <div style="display:flex;align-items:center;gap:10px">
         <span>💰</span>
         <span>Indicadores Financeiros</span>
       </div>
     </summary>
     <!-- Métricas dentro -->
   </details>
   ```

3. **👨‍👩‍👦 Estoque por Membro → Colapsável**
   - Agrupa as 3 colunas de membros
   - Abre à demanda (não ocupa espaço)

4. **🌾 Botão Flutuante (FAB) - Nova Visita**
   ```html
   <div class="fab-container">
     <a href="{{ url_for('nova_visita') }}" class="fab-primary">🌾</a>
   </div>
   ```
   - Posição fixa inferior direita
   - Gradient verde (--green-600 → --green-700)
   - Hover: scale(1.1)

5. **✅ Status Visual Melhorado**
   - Semáforo com emojis: ✅ (ok) ⚡ (aviso) 🚨 (ruim)
   - Cores explícitas (nunca só cor)
   - Pastos: "✅ folga no pasto" / "⚡ perto do limite" / "🚨 acima da capacidade"

---

## 📐 Estrutura CSS Mínima (Ponytail Style)

```css
/* Botão Flutuante */
.fab-container {
  position: fixed;
  bottom: 28px;
  right: 28px;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 12px;
  z-index: 50;
}

.fab-primary {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--green-600), var(--green-700));
  color: #fff;
  border: none;
  font-size: 24px;
  cursor: pointer;
  box-shadow: 0 4px 12px rgba(0,0,0,.2);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all .2s;
  text-decoration: none;
}

.fab-primary:hover {
  transform: scale(1.1);
  box-shadow: 0 6px 20px rgba(0,0,0,.25);
}

/* Seções Colapsáveis */
details.card-detail {
  background: var(--surface);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  overflow: hidden;
  margin-bottom: 20px;
}

summary {
  padding: 20px 24px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: 600;
  color: var(--green-700);
  user-select: none;
  transition: background .15s;
}

summary:hover {
  background: var(--bg-2);
}

details[open] > summary {
  background: var(--bg-2);
  border-bottom: 1px solid var(--bg-2);
}

details.card-detail > :not(summary) {
  padding: 0 24px 20px;
}
```

---

## 🎯 Ordem Nova do Dashboard

```
┌─────────────────────────────────┐
│ 🌾 ESTADO DO SÍTIO              │ (gradiente, melhor visual)
└─────────────────────────────────┘

┌─────────────────────────────────┐
│ 🥛 RESUMO LEITEIRO (PRIORIDADE) │ ← Movido para cima
│ Dia | Semana | Mês              │
└─────────────────────────────────┘

┌─────────────────────────────────┐
│ ☀️ PREVISÃO DO TEMPO            │
│ [7 dias + KPIs]                 │
└─────────────────────────────────┘

┌─────────────────────────────────┐
│ 🌿 LOTAÇÃO DOS PASTOS  🐄 REBANHO│ (lado a lado)
│ [barra UA/ha]         [composição]
└─────────────────────────────────┘

┌─────────────────────────────────┐
│ 📋 TAREFAS DA SEMANA            │
│ [atrasada/hoje/próxima]         │
└─────────────────────────────────┘

┌─────────────────────────────────┐
│ 💰 INDICADORES FINANCEIROS ▼   │ ← COLAPSÁVEL (economiza espaço)
├─────────────────────────────────┤
│ [6 métricas em grid]            │
│ [Estoque, CTCab, Resultado...]  │
└─────────────────────────────────┘

┌─────────────────────────────────┐
│ 👨‍👩‍👦 ESTOQUE POR MEMBRO ▼       │ ← COLAPSÁVEL
├─────────────────────────────────┤
│ [3 member-cards lado a lado]    │
└─────────────────────────────────┘

[Resto das seções: Última Visita, Insumos, WhatsApp, etc.]

   [🌾 BOTÃO FLUTUANTE no canto]
```

---

## 🎨 Melhorias de Visual

### Estado do Sítio - Agora com Gradiente
```html
<section class="card" style="background:linear-gradient(135deg, var(--surface) 0%, var(--bg-2) 100%)">
  <h2>🌾 Estado do Sítio</h2>
  <!-- Resultado com cor: verde se positivo, vermelho se negativo -->
  <div><b class="{{ 'pos' if r.resultado_realizado >= 0 else 'neg' }}">
    {{ r.resultado_realizado | brl }}
  </b>resultado</div>
</section>
```

### Pastos - Status Visual com Emoji
```
✅ 1.8 UA/ha — folga no pasto
⚡ 2.1 UA/ha — perto do limite
🚨 2.8 UA/ha — acima da capacidade
```

---

## 📱 Responsivo

- **Colapsáveis** funcionam igual em mobile (nativo HTML5)
- **FAB** redimensiona: 56px → 48px em tablets
- **Status emoji** funciona em daltonismo + tela ao sol

---

## ✨ Benefícios

| Aspecto | Antes | Depois |
|---------|-------|--------|
| Scroll inicial | 5 seções grandes | 3 seções + 2 colapsáveis |
| Info prioritária | Financeiro toma espaço | Leite + Pastos no topo |
| CTA (Nova Visita) | Em card + sidebar | Botão flutuante destacado |
| Contraste visual | Padrão | Gradientes + emoji status |
| Acessibilidade | Apenas cores | Cores + palavras + emoji |

---

## 🚀 Próximas Fases (Opcionais)

1. **Mini-gráficos inline** (CCS/CPP trend na card de leite)
2. **Animação de entrada** (fade-in cascata)
3. **Drag-reorder** das cards (salvar preferência no localStorage)
4. **Tema customizado** (cores por membro)

---

## Notas de Implementação

- ✅ Usar `<details>` HTML5 nativo (sem JavaScript)
- ✅ CSS em `base.html` dentro de `<style>` (2 classes + media queries)
- ✅ HTML em `dashboard.html` (wrap as seções em `<details>`)
- ✅ Sem novas dependências
- ✅ Sem quebra de compatibilidade
- ✅ Lazy loading: métricas colapsadas não renderizam gráficos até abrir
