# Design: Dashboard com Cards Clicáveis, Calendário e Gráficos (v5.6+)

**Data:** 2026-10-27  
**Status:** Proposta (inspiraçao das imagens de apps similares)  
**Prioridade:** Alta

## 1. Dashboard com Cards Clicáveis (Versão v5.6)

### Problema
O painel atual mostra números grandes (vacas, resultado, insumos…), mas precisa fazer a ponte entre visão geral e detalhes. Ao clicar em "45 vacas leiteiras", abre a lista filtrada.

### Solução
**Cards interativos no painel principal:**

```
┌────────────────────────────────────────┐
│ 🥛 LEITE                               │
├────────────────────────────────────────┤
│ ┌──────────────────────────────────┐   │
│ │      45 vacas leiteiras          │   │
│ │     (clica → /animais?leite=1)   │   │
│ │  ├─ 32 em lactação               │   │
│ │  └─ 13 secas                     │   │
│ └──────────────────────────────────┘   │
│                                        │
│ ┌──────────────────────────────────┐   │
│ │      1.245 L / dia (média)       │   │
│ │   (clica → /leite/relatorios)    │   │
│ │  vs 1.189 L na semana passada    │   │
│ └──────────────────────────────────┘   │
│                                        │
│ ┌──────────────────────────────────┐   │
│ │  ⚠️ Alertas (4)                  │   │
│ │   (clica → /leite/alertas)       │   │
│ │  • 1 vaca com CCS > 400k         │   │
│ │  • 1 colchão urgente (5 dias)    │   │
│ │  • 2 sem consumo registrado      │   │
│ └──────────────────────────────────┘   │
└────────────────────────────────────────┘
```

**Comportamento:**
- Clique no card inteiro abre a página relacionada
- Badge "4 alertas" leva a `/leite/alertas`
- Expandível (opcional): clica a seta para mais detalhes inline

---

## 2. Calendário Visual de Eventos (v5.6+)

### Problema
Eventos importantes (partos próximos, vacinação, secagem) não têm visão mensal. Pecuarista precisa saber "qual vaca pare em qual dia este mês?"

### Solução
**Página `/calendario` com Leaflet-Calendar (ou simple grid HTML):**

```
┌─────────────────────────────────────────────┐
│ 🗓️ Calendário de Eventos — Outubro 2026   │
├─────────────────────────────────────────────┤
│ Seg Ter Qua Qui Sex Sab Dom                 │
│                         1   2   3   4       │
│  5   6   7   8   9  10  11   🐮             │
│ 12  13  14  15  16  17  18   ← Vaca X pare │
│ 19  20  21  22  23  24  25                  │
│ 26  27  28  29  30  31   1                  │
│        ↑                                     │
│     Vacinação: Brucela (5 vacas)            │
│                                             │
│ ┌──────────────────────────────┐            │
│ │ 📋 Eventos do dia 27         │            │
│ │ • Vaca Brinco Amarelo 08    │            │
│ │   Parto previsto (280 dias)  │            │
│ │   Toque: amanhã              │            │
│ │                              │            │
│ │ • Colchão Baia 01            │            │
│ │   Próxima troca: 5 dias      │            │
│ └──────────────────────────────┘            │
└─────────────────────────────────────────────┘
```

**Dados:**
- 🐮 **Partos:** Data de parto prevista + dias restantes (via `dias_em_lactacao()` reverso)
- 🩺 **Toque:** 35 dias após cobertura
- 💉 **Vacinação:** Calendário sanitário (via `saude.py`)
- 🛏️ **Colchão:** Próxima troca
- 📋 **Tarefas:** Pendentes e de hoje

**Cores:**
- 🔴 Urgente (≤3 dias)
- 🟡 Aviso (≤7 dias)
- 🟢 Normal (>7 dias)

---

## 3. Gráficos de Crescimento (GMD) — (v5.6+)

### Problema
Peso do animal só aparece como número isolado. Pecuarista quer ver **tendência visual**: "esse animal está ganho peso normal?"

### Solução
**Página `/animais/crescimento?id=A0001` com Recharts:**

```
Crescimento — Amarelo 08 (A0001)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

       600 kg
         │      ╱╲     ╱╲
       550 kg ╱  ╲   ╱  ╲╱╲
         │  ╱      ╲╱      ╲
       500 kg                ╲╱━━← Desacelera
         │
         └────────────────────────────
         08/2024      01/2025      10/2026

Pesagens:
• 20/08/2024: 480 kg
• 15/09/2024: 510 kg
• 10/10/2024: 545 kg (pico)
• 05/11/2024: 500 kg (queda — febre?)
• 20/10/2026: 520 kg (atual)

GMD (Ganho por dia):
• Período todo: +150g/dia (bom)
• Últimos 30 dias: +50g/dia (lento — verificar nutrição)
• Desde a 1ª pesagem: +140g/dia

Status: 🟡 Aviso — ganho desacelerou no mês (verificar saúde/alimentação)
```

**Recursos:**
- Eixo X: Data (zoom últimos 30 dias / 6 meses / tudo)
- Eixo Y: Peso em kg
- Linha de tendência (trend)
- Anotações inline: "Febre 5/11", "Seleção de ração 15/12"
- Comparativo: linha de referência (média da categoria)
- CSV export

---

## 4. Notificações Push (PWA) — v5.6+

### Problema
WhatsApp avisa de urgentes, mas web PWA não tem notificações. Pecuarista na web não vê alertas em tempo real.

### Solução
**Service Worker notificações desktop/mobile:**

```javascript
// Ao marcar tarefa atrasada como feito:
self.registration.showNotification("✅ Tarefa concluída", {
  body: "Cerca do fundo — feito em 2h",
  tag: "tarefa-concluida",
  requireInteraction: false,
});

// Ao receber alerta via WebSocket (long-polling futuro):
self.registration.showNotification("🔴 Urgente!", {
  body: "Vaca Azul 15: CCS > 400k — mastite em curso",
  tag: "leite-urgente",
  requireInteraction: true,
  actions: [
    { action: "abrir", title: "Abrir ficha" },
    { action: "fechar", title: "Descartar" }
  ],
});
```

**Permissões:**
- Pede ao abrir página: "Permitir notificações?"
- Armazena em localStorage: `notificacoes_habilitadas=true`

---

## 5. Ficha Condensada (Mobile First) — v5.6

### Problema
Animal details (`/animais/A0001`) é completo mas longo. Mobile: precisa rolar muito. 

### Solução
**Ficha mobile:** mostra essencial, esconde detalhes em abas.

```
┌─────────────────────────────┐
│  🔙 Amarelo 08 #A0001      │ ← brinco + ID
├─────────────────────────────┤
│ 🐮 Vaca (F, 6 anos)         │
│ 520 kg · GMD +50g/dia       │
│ 📅 Parida 15/08/2024        │
│ 🥛 Lactação: 14 dias        │
│ 📊 Produção: 18 L/dia       │
│                             │
│ 🚨 CCS: 250k (aviso)        │
│ 📋 Status: Vivo, estoque    │
└─────────────────────────────┘

┌─ Ações ──────────────────────┐
│ [Pesar] [Examinar] [Vender]  │
└──────────────────────────────┘

Abas:
│ Últimas ações │ Histórico │ Fotos │
├──────────────┼──────────┼────────┤
│ 20/10 Pesagem│           │        │
│ 18/10 Ordenha│           │        │
│ 15/10 Cobertu│           │        │
```

---

## 6. Comparativo de Vacas — v5.6+

### Problema
Qual vaca é mais produtiva? Lado-a-lado é visual: "Vaca A vs B vs C".

### Solução
**Página `/leite/comparativo` (POST) com seletor de vacas:**

```
Comparativo de Produção
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

┌─ Selecione até 3 vacas ──────────────┐
│ [Amarelo 08] [Azul 15] [Verde 23]    │
│ [Limpar]                             │
└──────────────────────────────────────┘

Litros/dia (últimos 30 dias):
  Amarelo 08 ████████░░ 18 L (excelente)
  Azul 15    ██████░░░░ 15 L (bom)
  Verde 23   ███░░░░░░░  8 L (baixo)

Custos vs receita:
                  Amarelo 08    Azul 15    Verde 23
  Produção       18 L/dia      15 L/dia    8 L/dia
  Custo/dia      R$ 25         R$ 24       R$ 22
  Receita/dia    R$ 54         R$ 45       R$ 24
  Margem/dia     R$ 29         R$ 21       R$ 2

Decisão: Verde 23 está deficitária — verificar saúde/nutrição
```

---

## Cronograma

| Feature | v5.6 | v5.7 | Post |
|---------|------|------|------|
| Dashboard cards clicáveis | ✅ | | |
| Calendário visual | ✅ | | |
| GMD gráfico | ✅ | | |
| Push notifications | ✅ | | |
| Ficha mobile condensada | | ✅ | |
| Comparativo vacas | | ✅ | |

---

## Notas

- Todos usam dados **já no sistema** (sem nova coluna)
- Gráficos com **Recharts** (react-like em Jinja2 com Chart.js como fallback)
- Mobile-first: Calendário é grid CSS, GMD é área/linha do Chart.js
- Notificações: PWA nativo, sem biblioteca extra
