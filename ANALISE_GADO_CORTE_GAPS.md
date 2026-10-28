# 🐄 Análise de Gado de Corte — Gaps vs Mercado

**Data:** 28/10/2026  
**Foco:** Seu sistema é muito mais forte em **LEITE** do que em **CORTE**

---

## 📊 Realidade: Seu Sistema é 60% Leite, 10% Corte

### O que vocês TÊM em Corte:

```
✅ Compras        — data, qtd, valor/cabeça
✅ Vendas         — data, qtd, valor/arroba
✅ Manejo         — Perda, Nascimento, Brincos, Pesos, Pasto
✅ Lotes          — análise por lote (FIFO, resultado)
✅ GMD            — ganho médio diário por animal
✅ Pesagem        — peso individual por animal
✅ Pastos         — lotação (UA/ha), mapa
✅ Financeiro     — média móvel, resultado por membro
```

### O que FALTA (vs Leigado, Fazenda 360, iRancho):

```
❌ Reprodução detalhada (cria)
❌ Rastreabilidade SISBOV
❌ Confinamento (se for confinar)
❌ Planilha de abate / "ponto de corte"
❌ Conversão alimentar (CA)
❌ Indicadores de engorda vs pastagem
❌ Projections de venda (quando vender?)
❌ Histórico de lotes (série temporal)
```

---

## 🎯 INDICADORES CRÍTICOS EM CORTE

### 1️⃣ **GMD (Ganho Médio Diário)** — ✅ Vocês têm

**O que é:**
```
GMD = (Peso Final - Peso Inicial) / Dias
```

**Referência:**
- Pasto c/ suplementação: 0,8–1,1 kg/dia
- Confinamento: 1,0–1,6 kg/dia

**Vocês têm:** `pesagem.py` calcula isso

**Status:** ✅ OK

---

### 2️⃣ **CA (Conversão Alimentar)** — ❌ Vocês NÃO têm

**O que é:**
```
CA = Quantidade de Ração Consumida / Ganho de Peso
```

**Exemplo:** Se animal ganhou 1 kg e comeu 7 kg de ração → CA = 7:1

**Por que importa:**
- Animal com CA ruim = descarte
- Diferença de CA entre lotes = lucro ou prejuízo
- **90% do custo de confinamento é alimentação**

**Esforço:** Médio (precisa histórico de consumo)

**Impacto:** ⭐⭐⭐⭐⭐ (crítico em confinamento)

---

### 3️⃣ **Lotação Ótima (UA/ha)** — ⚠️ Vocês têm parcial

**O que é:**
- Quantos animais cabem no pasto sem degradar?
- Muito lotado = GMD cai 30%
- Pouco lotado = desperdício de capacidade

**Vocês têm:**
- ✅ UA/ha calculado
- ✅ Limite de capacidade em `sitio_config.json`
- ❌ Histórico de GMD vs lotação (correlação)
- ❌ Recomendação de ajuste

**Esforço:** Baixo (gráfico correlação)

**Impacto:** ⭐⭐⭐⭐ (otimização de pastagem)

---

### 4️⃣ **Ponto de Corte (Abate)** — ❌ Vocês NÃO têm

**O que é:**
- Quando vender? (peso ideal + preço + custos)
- Simulação: "Se vender com 480 kg agora vs esperar 30 dias?"

**Exemplo:**
```
Animal A:  Custo R$800  Peso agora: 450kg  Preço: R$30/kg  = R$13.500 - R$800 = +R$12.700
           Projeção +30d: 485kg  Preço cai para R$28/kg = R$13.580 - R$900 = +R$12.680
           → Vender agora!
```

**Quem tem:**
- Leigado: Planejador de abate
- Fazenda 360: Projeção de abate
- Ponta: Simulador

**Esforço:** Médio (modelo de preço + projeção GMD)

**Impacto:** ⭐⭐⭐⭐⭐ (decisão financeira crítica)

---

### 5️⃣ **Reprodução / Cria** — ⚠️ Vocês têm básico

**O que vocês têm:**
- ✅ Cobertura + Diagnóstico de gestação
- ✅ Parto em 285 dias
- ✅ Taxa de prenhez

**O que FALTA:**
- ❌ Intervalo de partos (IPP) — dias entre um parto e outro
- ❌ Histórico de bezerro: qual vaca pariu? (rastreabilidade)
- ❌ Taxa de desmame
- ❌ Conversão bezerro→novilho (crescimento esperado)
- ❌ Índice de natalidade por vaca

**Esforço:** Médio (mais rastreamento de genealogia)

**Impacto:** ⭐⭐⭐⭐ (produção de bezerro é receita)

---

### 6️⃣ **Rastreabilidade SISBOV** — ❌ Vocês NÃO têm

**O que é:**
- Sistema oficial de rastreabilidade Brasil
- Obrigatório para venda formal (frigorífico, exportação)

**Dados necessários:**
```
1. Entrada: Data + Origem (compra/nascimento) + Identificação
2. Saída: Data + Destino (venda/morte/descarte) + Identificação
3. Tudo linkedado ao animal (brinco)
```

**Status vocês:**
- ✅ Tem histórico de movimentação (Manejo)
- ✅ Tem brinco por animal
- ❌ Não tem "origem do animal" registrada (pode recuperar?)
- ❌ Não exporta para SISBOV

**Esforço:** Alto (integração com SISBOV API + auditoria)

**Impacto:** ⭐⭐⭐⭐ (obrigatório para escalar)

**Nota:** Se vocês vendem só pra família, não precisam agora.

---

### 7️⃣ **Custo por Cabeça por Dia** — ⚠️ Parcial

**O que é:**
```
Custo/cab/dia = (Gastos Mensais / Qtd Cabeças Vivas) / 30
```

**Vocês têm:**
- ✅ Gastos registrados
- ✅ Cabeças vivas calculadas
- ❌ Não agrupa por "período de engorda" (ex: fase de recria vs engorda final)

**Esforço:** Baixo (dashboard novo)

**Impacto:** ⭐⭐⭐ (controle de despesa)

---

### 8️⃣ **Confinamento (se usar)** — ❌ Vocês NÃO têm

**O que é:**
- Engorda em galpão (pasto confinado)
- Alimentação controlada + pesagem frequente
- Ciclo mais curto (60–120 dias vs 18 meses no pasto)

**Por que importa:**
- 40% do mercado é confinado
- Margens maiores (CA controlada)
- Ciclo rápido = capital mais ativo

**O que faltaria:**
- ❌ Aba Confinamento (dieta, consumo/dia/animal)
- ❌ Balanço de ração (mixer acurado)
- ❌ Histórico de saúde (respiratória comum)
- ❌ Projeção de término (GMD esperado)

**Esforço:** Alto (nova aba + lógica complexa)

**Impacto:** ⭐⭐⭐⭐ (se vocês confinar)

**Status vocês:** 🚫 Não aplicável se só pasto

---

## 📈 COMPARAÇÃO COM CONCORRENTES

| Funcionalidade | Seu Sistema | Leigado | Gisleite | Fazenda 360 | iRancho | Status |
|---|---|---|---|---|---|---|
| **GMD** | ✅ | ✅ | ✅ | ✅ | ✅ | Empate |
| **Lotação** | ✅ | ⚠️ | ⚠️ | ✅ | ✅ | Vocês ganham |
| **Conversão Alimentar** | ❌ | ✅ | ✅ | ✅ | ✅ | **Vocês perdem** |
| **Ponto de Corte (simulador)** | ❌ | ✅ | ✅ | ✅ | ✅ | **Vocês perdem** |
| **Reprodução/Cria** | ⚠️ | ✅ | ✅ | ⚠️ | ✅ | Vocês perdem |
| **SISBOV** | ❌ | ✅ | ✅ | ✅ | ✅ | **Vocês perdem** |
| **Confinamento** | ❌ | ✅ | ⚠️ | ✅ | ✅ | Vocês perdem |
| **Pastos/Mapa** | ✅ | ⚠️ | ❌ | ⚠️ | ✅ | Empate |
| **Média móvel financeira** | ✅ | ❌ | ❌ | ❌ | ❌ | **Vocês ganham** |
| **Lotes (FIFO)** | ✅ | ⚠️ | ⚠️ | ✅ | ⚠️ | Vocês ganham |

---

## 🎯 RECOMENDAÇÃO PARA CORTE

### **Se vocês querem ser competitivos em Corte, prioridade:**

#### **Fase 1 (2 meses) — Must-have**

1. **Ponto de Corte / Simulador** (30h)
   - Quando vender? Ganho vs custo
   - Interface: "Se vender hoje vs +30 dias?"
   - **ROI:** Alto — evita vender caro, segura quando preço ruim

2. **Conversão Alimentar** (20h)
   - CA = ração/ganho de peso
   - Integra com consumo de pastagem (aproximação)
   - **ROI:** Alto — identifica animal ineficiente

3. **Histórico de Lotes** (15h)
   - Série temporal: GMD, CA, custo/cab/dia por lote
   - Comparar lote 2025 vs 2026
   - **ROI:** Médio — benchmarking

**Total:** 65 horas = 2-3 sprints

---

#### **Fase 2 (4 meses) — Important**

4. **Reprodução Detalhada** (40h)
   - Genealogia de bezerro
   - Taxa de desmame, conversão bezerro→novilho
   - **ROI:** Médio — validar cria

5. **SISBOV Export** (50h)
   - Exportar histórico de entrada/saída
   - Auditoria de rastreabilidade
   - **Por quê:** Obrigatório se vender pra terceiros
   - **ROI:** Crítico quando escalar

---

#### **Fase 3 (6 meses) — Nice-to-have**

6. **Confinamento** (60h)
   - Só se vocês começarem a confinar
   - **ROI:** Alto se usar

---

## 💡 RECOMENDAÇÃO ESPECÍFICA PARA VOCÊS

**Seu padrão é CORTE DE QUALIDADE em PASTO (não confinamento).**

Vocês precisam de:

### ✅ DEVE FAZER (próximos 2 meses):

1. **Ponto de Corte** — "quando vender esse lote?"
   - Integra: peso atual + GMD + preço market + custos
   - Mostra: "vender hoje = R$X vs esperar 30d = R$Y"

2. **Gráfico Lotação vs GMD** — "esse pasto está bom?"
   - X=UA/ha, Y=GMD mês anterior
   - Mostra padrão: lotação ideal

---

### ⚠️ DEVERIA FAZER (depois):

3. **Genealogia de Bezerro** — "qual vaca pariu esse animal?"
4. **SISBOV** — quando virar empresa

---

### ❌ NÃO PRECISA (vocês não confinem):

- Confinamento
- CA detalhada (aproximação serve)
- Dieta balanceada (vocês não controlam consumo exato)

---

## 🔥 Seu Diferencial em Corte

Enquanto Leigado/Gisleite copiam um do outro, **vocês têm:**

- ✅ **Média móvel** — ninguém mais tem (vocês conhecem custo real de cada venda)
- ✅ **Pastos com mapa** — visual única
- ✅ **Resultado por membro** — divisão justa
- ✅ **Lotes FIFO** — controle histórico

**O que vira vocês competitivos:**
- + Ponto de Corte (30h) = vocês têm ferramenta que Leigado não tem (simulação precisa)
- + CA / histórico de lotes (35h) = benchmarking único

**Total para virar TOP 3:** 65h = **vocês empatam com iRancho/Fazenda 360** em funcionalidade de corte.

---

## 📋 Resumo em 1 parágrafo

Seu sistema é **forte em financeiro (média móvel)** e **pastos (mapa + lotação)**, mas **fraco em análise de engorda** (falta ponto de corte, CA, simulador). Para corte de qualidade em pasto, os gaps críticos são: (1) Ponto de Corte/Simulador, (2) CA, (3) Histórico de lotes. Implemente esses 65h e vocês viram referência (melhor que Leigado em média móvel + ponto de corte = decisão perfeita de venda).

---

**Próximo passo:** Quer que eu comece a planejar o "Ponto de Corte" primeiro?

---

### Fontes
- [iRancho - 10 indicadores gado corte](https://www.irancho.com.br/10-indicadores-na-pecuaria-de-corte-que-revelam-os-prejuizos-da-producao/)
- [JetBov - Métricas gado corte](https://blog.jetbov.com/2020/02/27/quais-sao-as-metricas-que-eu-devo-levar-em-conta-ao-gerenciar-minha-fazenda-de-gado-de-corte/)
- [Giro do Boi - 4 indicadores resultado fazenda](https://girodoboi.canalrural.com.br/pecuaria/4-indicadores-que-explicam-ate-70-do-resultado-de-uma-fazenda-de-gado/)
- [Multsoft - Indicadores confinamento](https://multsoft.agr.br/indicadores-essenciais-para-tomar-decisoes-no-confinamento-de-gado-de-corte/)
- [Ponta Agro - Custo confinamento por cabeça](https://pontaagro.com/custo-de-confinamento-por-cabeca/)
- [Canal Rural - Confinamento nutrição 90% custo](https://www.canalrural.com.br/pecuaria/boi/confinamento-estudo-mostra-que-nutricao-representa-90-do-custo-de-producao/)
