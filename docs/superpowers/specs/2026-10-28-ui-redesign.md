# 🎨 UI/UX Redesign — Mobile-First, Sem Sidebar

**Data:** 28/10/2026  
**Contexto:** Refactor completo do layout para mobile-first, inspirado em apps Android  
**Escopo:** Remover sidebar, reorganizar dashboard, adicionar 6 widgets novos

---

## 📱 Novo Layout (Mobile-First)

```
┌─────────────────────────────┐
│ 🌾 Sítio Santo Antonio      │  ← Header fixo, simples
├─────────────────────────────┤
│ [DASHBOARD PRINCIPAL]       │
│                             │
│ ┌───────────────────────┐   │
│ │ ☀️ PREVISÃO DO TEMPO  │   │ Card 1
│ │ 28°C, sol            │
│ │ Próx 7 dias          │
│ └───────────────────────┘   │
│                             │
│ ┌───────────────────────┐   │
│ │ 🚨 AVISOS E ALERTAS  │   │ Card 2
│ │ • Quarentena leite   │
│ │ • CCS alto vaca 05   │
│ │ • Pasto lotado       │
│ └───────────────────────┘   │
│                             │
│ ┌───────────────────────┐   │
│ │ 📋 AGENDA DE MANEJO  │   │ Card 3
│ │ ⏳ Hoje:             │
│ │  - Pesagem geral     │
│ │  - Vacina lote B     │
│ │ 📅 Próximos:         │
│ │  - Troca colchão     │
│ └───────────────────────┘   │
│                             │
│ ┌───────────────────────┐   │
│ │ 🧂 ESTOQUE ALIMENTO │   │ Card 4
│ │ Sal: 8 sacos (OK)   │
│ │ Prot: 3 sacos ⚠️     │
│ │ Ração: 12 sacos OK  │
│ └───────────────────────┘   │
│                             │
│ ┌───────────────────────┐   │
│ │ 🌧️ CHUVAS (Mês)      │   │ Card 5
│ │ [Gráfico barras]     │
│ │ Mês: 120 mm          │
│ │ Média: 90 mm         │
│ └───────────────────────┘   │
│                             │
│ ┌───────────────────────┐   │
│ │ 💰 COTAÇÃO MERCADO   │   │ Card 6
│ │ Boi: R$30/kg ↑ 2%   │
│ │ Leite: R$1.80/L ↓ 3%│
│ │ Atualizado hoje      │
│ └───────────────────────┘   │
│                             │
│ ┌───────────────────────┐   │
│ │ 🐄 ESTADO DO SÍTIO   │   │ Card 7 (resumo)
│ │ 247 cabeças          │
│ │ R$ +45.000 resultado │
│ │ 1.8 UA/ha            │
│ └───────────────────────┘   │
│                             │
│              [🌾]           │ ← FAB: Nova Visita
│                             │
└─────────────────────────────┘

[Menu inferior ou drawer slide?]
```

---

## 🎯 6 Widgets Principais

### 1. ☀️ Previsão do Tempo
- Já existe (`routes_dashboard.tempo()`)
- Mostrar: Hoje + próx 3 dias
- Integrar chuva com alerta de lotação

### 2. 🚨 Avisos e Alertas  
- Consolidar: Quarentena leite, CCS alto, CPP alto, Mastite
- Cor: 🟢 OK, 🟡 Aviso, 🔴 Urgente
- Máx 5 alertas no resumo, link para "Ver tudo"

### 3. 📋 Agenda de Manejo
- Tarefas do dia + próximos 7 dias (já existe `tarefas.py`)
- Mostrar ícone por tipo: 💉 Vacina, 🔨 Manejo, 🐄 Reprodução, etc.
- Status: Pendente / Atrasada / Hoje

### 4. 🧂 Estoque de Alimentação
- Já existe (`insumos.py`)
- Mostrar: Sal + Proteinado + Ração
- Barras de progresso: verde/amarelo/vermelho
- "Acaba em X dias"

### 5. 🌧️ Chuvas por Mês
- Novo gráfico (barras ou linha)
- Dados: Visitas → coluna "Chuva mm"
- Comparar mês atual vs média histórica

### 6. 💰 Cotação de Mercado
- Novo: integrar API ou entrada manual
- Mostrar: Boi (R$/kg), Leite (R$/L)
- Seta ↑↓ de variação (hoje vs ontem)
- Atualizado: data/hora

### 7. 🐄 Estado do Sítio (Resumo)
- Já existe, manter no fundo
- 3 métricas: Cabeças + Resultado + UA/ha

---

## 🎨 Componentes CSS Novos

```css
/* Card padrão */
.card-mobile {
  background: white;
  border-radius: 12px;
  padding: 16px;
  margin: 12px 0;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

/* Header fixo */
.header-fixo {
  position: sticky;
  top: 0;
  background: linear-gradient(135deg, #3d7a34, #2d5a27);
  color: white;
  padding: 12px 16px;
  z-index: 40;
}

/* Status semáforo */
.status-badge {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 11px;
  font-weight: 600;
}
.status-ok { background: #d4edda; color: #155724; }
.status-aviso { background: #fff3cd; color: #856404; }
.status-urgente { background: #f8d7da; color: #721c24; }

/* Gráfico simples */
.grafico-barras {
  display: flex;
  gap: 8px;
  align-items: flex-end;
  height: 100px;
}
.barra {
  flex: 1;
  background: linear-gradient(135deg, #3d7a34, #2d5a27);
  border-radius: 4px 4px 0 0;
}

/* Menu inferior (if needed) */
.menu-inferior {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  background: white;
  border-top: 1px solid #eee;
  display: flex;
  height: 60px;
  z-index: 40;
}
```

---

## 📁 Estrutura de Arquivos

```
templates/
  base.html              ← Nova versão: header + container + sem sidebar
  dashboard.html         ← Reorganizado: 7 cards principais
  dashboard/
    card_tempo.html
    card_alertas.html
    card_agenda.html
    card_estoque.html
    card_chuvas.html     ← NOVO
    card_cotacao.html    ← NOVO
    card_estado.html
  
static/
  css/
    cards-mobile.css     ← Novo CSS para cards
```

---

## 🔧 Backend Novo

### Funções a Criar/Estender

```python
# dashboard.py (novo)
def alertas_consolidados() → dict
  # Retorna: quarentena, CCS, mastite, CPP, pastagens

def chuvas_mes(ano: int, mes: int) → dict
  # Lê Visitas → coluna "Chuva mm"
  # Retorna: dados para gráfico + média

def cotacao_mercado() → dict
  # Boiada: integrar API ou entrada manual
  # Leite: integrar API ou entrada manual
  # Retorna: preço + % variação
```

---

## ✅ Checklist de Implementação

### Fase 1: Estrutura (4h)
- [ ] Nova base.html (header fixo, sem sidebar, container central)
- [ ] CSS cards-mobile.css
- [ ] Remover menu lateral de TODAS as páginas

### Fase 2: Dashboard Principal (8h)
- [ ] Reorganizar dashboard.html com 7 cards
- [ ] Card Tempo (já existe, reformatar)
- [ ] Card Alertas (consolidar avisos)
- [ ] Card Agenda (tarefas, já existe)
- [ ] Card Estoque (já existe, reformatar)
- [ ] Card Chuvas (NOVO — gráfico simples)
- [ ] Card Cotação (NOVO — manual ou API)
- [ ] Card Estado (já existe, move para final)

### Fase 3: Integrações (4h)
- [ ] dashboard.py → alertas_consolidados()
- [ ] dashboard.py → chuvas_mes()
- [ ] dashboard.py → cotacao_mercado()
- [ ] Routes → endpoints para dados dos cards

### Fase 4: Mobile Responsiveness (2h)
- [ ] Testar em celular (W3C responsive)
- [ ] FAB fixo no canto
- [ ] Ajustar fontes/padding para mobile
- [ ] Teste scroll vertical

### Fase 5: Polimento (2h)
- [ ] Animações suaves
- [ ] Icons/emojis consistentes
- [ ] Cores e contraste
- [ ] Testes em diferentes telas

**Total: 20 horas = 1 sprint**

---

## 🎯 Resultado Esperado

- ✅ Zero sidebar (tudo em cards mobile-first)
- ✅ Dashboard inicial com 6 widgets informativos
- ✅ Responsivo em celular (matcheia exemplos Android)
- ✅ FAB destacado para nova visita
- ✅ Alertas visuais consolidados
- ✅ Sem sacrificar funcionalidade (tudo continua acessível)

---

## 📱 Quebra de Layout (Antes/Depois)

**ANTES:**
```
┌─────────────────────────────────┐
│ Menu Lateral (100px) │ Conteúdo │
│ - Home              │ (desktop) │
│ - Registros         │           │
│ - Relatórios        │ Sidebar   │
│ - Animais           │ ocupa 15% │
│ - Configurações     │           │
└─────────────────────────────────┘
```

**DEPOIS:**
```
┌──────────────────────────────┐
│ 🌾 Sítio Santo Antonio      │ ← Header fixo
├──────────────────────────────┤
│ [Cards Empilhados]           │
│ 100% largura, mobile-first   │
│                              │
│ [Menu inferior slide: ≡ ☰]   │ ← Opcional
└──────────────────────────────┘
       [🌾 FAB]
```

---

## 🚀 Próximos Passos (Depois)

1. Refinar menus secundários (Registros, Relatórios, etc)
2. Aplicar layout card em outras páginas
3. Dark mode (opcional)
4. Animações de transição
