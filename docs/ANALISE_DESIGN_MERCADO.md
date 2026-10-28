# Análise de Design: Softwares de Controle de Gado (Mercado)

**Data:** 2026-10-28  
**Objetivo:** Compilar padrões de interface, layouts e designs de softwares comerciais e open-source de gestão de gado para adaptar no gado-sitio v5.10+

---

## 1. SOFTWARES COMERCIAIS PRINCIPAIS

### iRancho (Líder de mercado)
- **URL:** https://www.irancho.com.br/
- **Tipo:** Web + iOS/Android
- **Apps:** iRancho Campo, iRancho Confinamento, iRancho RePro
- **Características:**
  - ✨ **Mapa interativo** — visualizar e mover lotes no mapa da fazenda
  - Dashboard integrado com painel de controle
  - Acesso a dados de subdivisões direto do mapa
  - Indicadores: Compra média, custos/cab, produtividade, R$/arroba
  - Relatórios customizáveis, análise reprodutiva
  - Herd listing visual

### VSM AGRO
- **URL:** https://www.vsmagro.com.br/
- **Tipo:** Web + App mobile (Android)
- **Especialidade:** Cria, recria, engorda, confinamento
- **Características:**
  - Controle de lotes por faixa etária
  - Localização em pasto com rastreabilidade
  - **Pesagem com balança digital integrada** ← Feature importante
  - Manejo reprodutivo visual

### Leigado (10+ anos no mercado)
- **URL:** https://leigado.com.br/
- **Tipo:** Web + iOS/Android (multiplataforma)
- **Especialidade:** Gado leiteiro + corte (módulo único)
- **Características:**
  - 9 módulos integrados
  - 35+ relatórios especializados
  - **Notificações diárias** de eventos urgentes
  - Múltiplas propriedades em uma conta
  - Offline no app + sincronização
  - Módulos: Produção, Reprodução, Saúde, Financeiro, Manejo

### Aegro
- **URL:** https://aegro.com.br/
- **Tipo:** SaaS web (Gestão rural completa)
- **Características:**
  - Integração financeira (compra/venda entra em fluxo de caixa)
  - **Análise de lucratividade por ciclo** ← Modelo importante
  - Dashboards customizáveis (Power BI)
  - Interface intuitiva e mobile-friendly

---

## 2. SOFTWARES OPEN-SOURCE NO GITHUB

### BoviTrack (2 versões — Brasil + Colombia)
- **Repos:** 
  - https://github.com/CRH535/BoviTrack__Sistema-full-stack-para-gestao-pecuaria
  - https://github.com/Bovi-Track/BoviTrack
- **Stack:** React 18+ Vite + TypeScript + TailwindCSS 4, Express/Django, PostgreSQL
- **Características:**
  - Dashboard com KPIs principais
  - Gestão de propriedades, animais, lotes
  - Vacinação, produção de leite, financeiro
  - Histórico produtivo/sanitário/reprodutivo
  - **Mobile-first design** (ícones grandes, touch targets 48dp+)

### Controle Rebanho
- **Repo:** https://github.com/amanda-gondra/controle-rebanho
- **Stack:** React + Node.js + PostgreSQL
- **Foco:** Gado de corte, pesagens, GMD

### Gestão Agropecuária Completa
- **Repo:** https://github.com/JoseBieco/sistema-de-gestao-agro
- **Características:** Rebanho, manejo sanitário, financeiro, pastagens

---

## 3. PADRÕES DE DESIGN ENCONTRADOS

### 3.1 Paleta de Cores (Padrão Mercado)

```
🟢 VERDE (Produção, saúde, OK)
  → Verde escuro: Principal, CTA, success
  → Verde claro: Background, suave

🟡 AMARELO/ÂMBAR (Atenção, aviso)
  → Requer monitoramento
  → Condição marginal

🔴 VERMELHO (Crítico, urgente)
  → Problema imediato
  → Requer ação agora

⚪ CINZA/AZUL (Informação neutra)
  → Backgrounds, borders
  → Contexto, labels
```

**Regra fundamental:** ⚠️ **Semáforo SEMPRE com a palavra junto da cor** (daltonismo, acessibilidade)

### 3.2 Componentes Visuais Recomendados

#### Cards de KPI (Padrão universal)
```
┌─────────────────────┐
│  [Número Grande]    │
│   (métrica)         │
│  [Rótulo pequeno]   │
│   (unidade)         │
│  [Seta de tren]     │
│   (+5% vs mês)      │
└─────────────────────┘
```
- Número grande em cima
- Rótulo descritivo abaixo
- Opcional: trend indicator (↑↓ com %)
- Cor: verde (OK), amarelo (aviso), vermelho (crítico)

#### Badges de Status
- ✅ Verde: "Ativo", "OK", "Prenha"
- ⚠️ Amarelo: "Aviso", "Pendente", "Vazia"
- ❌ Vermelho: "Crítico", "Urgente", "Morte"

#### Semáforos (3 níveis)
- Saúde do rebanho: verde/amarelo/vermelho
- **Sempre com rótulo:** "Saúde: OK" não "Saúde: 🟢"

#### Gráficos
- **Colunas:** Comparação entre categorias (lotes, membros, períodos)
- **Barras:** Horizontal para nomes longos
- **Linhas:** Evolução temporal (GMD histórico, preço/arroba)
- **Pizza:** Distribuição (estoque por categoria, resultado por membro)
- **Tabelas:** Detalhamento (lista de animais, histórico de vendas)

### 3.3 Responsividade (Mobile-First)

**Desktop:**
- Tabelas com múltiplas colunas
- Gráficos lado a lado
- Sidebar com menu

**Tablet (768px):**
- Tabelas com colunas adaptadas
- Gráficos em coluna única
- Menu colapsável

**Mobile (<480px):**
- **Tabelas → Cards-linha** (1 linha por animal)
  ```
  ┌─────────────────────┐
  │ Animal: A0001       │
  │ Peso: 350 kg        │
  │ GMD: 1.2 kg/dia     │
  │ Status: Ativo ✅    │
  └─────────────────────┘
  ```
- Gráficos em altura reduzida
- Touch targets: 48dp (Android) / 44pt (iOS)
- Ícones grandes, rótulos curtos

### 3.4 Tipografia (Hierarquia)

```
Métrica principal:    36–48px, bold (número grande)
Rótulo de métrica:    12–14px, gray (descrição)
Título de seção:      24–32px, bold
Subtítulo:            16–18px, medium
Corpo de texto:       14–16px, regular
Labels/helpers:       12–13px, gray
```

---

## 4. INDICADORES PRINCIPAIS (KPI) DO MERCADO

### Top 11 indicadores encontrados em softwares de gado:

1. **Total de animais ativos** — Número total vivo no rebanho
2. **Lotes ativos** — Quantos lotes em confinamento/pasto
3. **Peso médio do rebanho (kg)** — Estimativa média
4. **Ganho médio acumulado/cab** — Desde a compra
5. **Volume em arrobas (@ vivo)** — Potencial de venda
6. **Custo total investido (R$)** — Total de compra + gastos
7. **Compra Média (CMP)** — Custo médio por cabeça comprada
8. **Gastos por cabeça (GPCab)** — Alimentação, medicamentos, etc
9. **Custo Total por cabeça (CTCab)** — CMP + GPCab (o mais importante!)
10. **GMD (Ganho Médio Diário)** — Produtividade em kg/dia (CRÍTICO)
11. **Custo da arroba (@) produzida** — Custo real da produção

### Fórmulas principais:
```
GMD = (Peso final − Peso inicial) ÷ Dias
Custo@Produzida = (Custo total ÷ (GMD × Rendimento Carcaça)) × 15
Arrobas ganho = GMD × Rendimento ÷ 15
```

---

## 5. LAYOUT PADRÃO DE DASHBOARD

### Estrutura recomendada:

```
┌─────────────────────────────────────────────────┐
│  [Logo]  [Título]              [Menu/Usuário]  │
├─────────────────────────────────────────────────┤
│                                                 │
│  KPI Row 1:                                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐        │
│  │ Animais  │ │ Lotes    │ │ Peso     │        │
│  │  2.500   │ │    8     │ │ 350 kg   │        │
│  │ Ativos   │ │ Ativos   │ │ Médio    │        │
│  └──────────┘ └──────────┘ └──────────┘        │
│                                                 │
│  KPI Row 2:                                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐        │
│  │ CMP      │ │ CTCab    │ │ GMD      │        │
│  │ R$2.100  │ │ R$2.850  │ │ 1.2 kg   │        │
│  │ /cab     │ │ /cab     │ │ /dia     │        │
│  └──────────┘ └──────────┘ └──────────┘        │
│                                                 │
│  Alertas (se houver):                          │
│  ⚠️  GMD baixo: Lote L001 (0.8 kg/dia)        │
│  🔴 Morte detectada: Animal A0042             │
│                                                 │
│  Gráficos / Tabelas (abaixo):                  │
│  [Gráfico de evolução de peso por lote]       │
│  [Tabela de lotes ativos]                      │
│                                                 │
└─────────────────────────────────────────────────┘
```

### Seções principais:
1. **Header:** Logo, título, navegação, usuário
2. **KPIs (3x2 ou 4x3):** Métricas principais em cards
3. **Alertas:** Box destacada com urgentes
4. **Gráficos:** 1-2 gráficos principais (GMD, preço, evolução)
5. **Tabelas:** Detalhamento (lotes, animais, vendas recentes)

---

## 6. FUNCIONALIDADES MAIS VALORIZADAS (Pesquisa de mercado)

1. ✅ **GMD, Custo@Arroba, CMP** — Indicadores técnicos
2. ✅ **Pesagem integrada** — Balança digital + foto (peso estimado)
3. ✅ **Status reprodutivo/sanitário por animal** — Prenha/Vazia/Doente
4. ✅ **Dashboard financeiro** — Resultado rápido
5. ✅ **Suporte offline** — Campo sem sinal
6. ✅ **Notificações urgentes** — Morte, parto, vacinação pendente
7. ✅ **Relatórios em PDF/Excel** — Exportação
8. ✅ **Múltiplas propriedades** — Gerenciar vários sítios
9. ✅ **Histórico reprodutivo/sanitário** — Por animal
10. ✅ **Análise de resultado por ciclo/lote** — Lucratividade

---

## 7. RECURSOS TÉCNICOS ENCONTRADOS

### Documentação e Calculadoras:
- **Embrapa:** https://www.embrapa.br/en/busca-de-solucoes-tecnologicas/-/produto-servico/5671/ (Planilha de Gerenciamento Rural)
- **PlanilhasTech:** https://planilhastech.com/como-calcular-gmd-gado-de-corte/
- **AppZebuTech:** https://appzebutech.com/blog/como-calcular-ganho-medio-diario-bovinos

### Arquitetura comum (open-source):
- **Frontend:** React 18+ (Vite, TypeScript, TailwindCSS 4)
- **Backend:** Express.js ou Django/FastAPI
- **Database:** PostgreSQL
- **Mobile:** React Native ou PWA (Progressive Web App)
- **Offline:** IndexedDB + Service Workers
- **Gráficos:** Chart.js, Recharts, Apache ECharts
- **Maps:** Leaflet, Mapbox (para visualizar pastos/lotes)

---

## 8. SUGESTÕES PARA GADO-SITIO v5.10+

### 🎨 Design Visual
- [ ] Adotar paleta padrão: Verde (principal), Amarelo (aviso), Vermelho (crítico)
- [ ] Implementar cards de KPI com número grande + rótulo
- [ ] **Sempre acompanhar cores com palavras** (nunca só semáforo)
- [ ] Mobile-first: adaptar tabelas para cards-linhas em <768px
- [ ] Touch targets mínimo 48dp (Android) / 44pt (iOS)

### 📊 Dashboard
- [ ] Reorganizar em seções: KPIs → Alertas → Gráficos → Tabelas
- [ ] Priorizar GMD, CTCab, CMP em cards principais
- [ ] Adicionar gráfico de evolução de peso (linhas)
- [ ] Adicionar gráfico de comparação de custos (colunas)
- [ ] Box destacada para alertas urgentes (vermelho)

### 🔔 Notificações e Alertas
- [ ] Sistema de notificações urgentes (morte, parto, vacinação)
- [ ] Alertas em tempo real no dashboard
- [ ] Integração WhatsApp (já em desenvolvimento)

### 📱 Mobile
- [ ] PWA completo com suporte offline
- [ ] IndexedDB para sincronização quando houver sinal
- [ ] Entrada de dados no campo (câmera, voz, NFC)
- [ ] Ícones grandes, interface visual-first

### 🗺️ Mapa (Feature future)
- [ ] Integrar Leaflet para visualizar pastos e lotes
- [ ] Clicar no pasto → ver animais no local
- [ ] Mover lotes entre pastos no mapa

### 📈 Análise
- [ ] Relatórios em PDF com gráficos
- [ ] Exportação para Excel
- [ ] Análise de lucratividade por lote/período
- [ ] Histórico reprodutivo/sanitário por animal

### 🔗 Integrações
- [ ] Balança digital (pesagem automática)
- [ ] Câmera para peso estimado (já em desenvolvimento)
- [ ] NFC/QR code para leitura de brinco
- [ ] Google Sheets export (compatibilidade)

---

## REFERÊNCIAS E LINKS

### Softwares Comerciais:
- iRancho: https://www.irancho.com.br/
- VSM AGRO: https://www.vsmagro.com.br/
- Leigado: https://leigado.com.br/
- Aegro: https://aegro.com.br/
- MeuGado: https://meugadoapp.tec.br/
- Rebanho Fácil: https://www.ar7app.com/rebanho-facil/
- FinAgro: https://finagro.app/guias

### Open-Source no GitHub:
- BoviTrack (Brasil): https://github.com/CRH535/BoviTrack__Sistema-full-stack-para-gestao-pecuaria
- BoviTrack (Colombia): https://github.com/Bovi-Track/BoviTrack
- Controle Rebanho: https://github.com/amanda-gondra/controle-rebanho
- Gestão Agropecuária: https://github.com/JoseBieco/sistema-de-gestao-agro

### Planilhas Gratuitas:
- TECBOV: https://tecbov.com.br/planilha-gratuita-de-controle-de-gado/
- Excel para Você: https://www.excel-para-voce.com/planilha/controle-gado/
- Planilhas Prontas: https://www.planilhasprontas.com.br/
- Planilhas Tech: https://planilhastech.com/

---

**Próximo passo:** Aplicar esses insights de design no v5.10 (dashboard reorganizado) e v5.11+ (novos componentes, mapa, análise avançada).
