# 🐂 Análise: Recria e Engorda — Fases e Gaps

**Data:** 28/10/2026  
**Contexto:** Sistema atual não tem "fases" de produção (cria/recria/engorda) separadas

---

## 📚 As 3 Fases Principais

```
┌─────────────────────────────────────────────────────────────────┐
│ CRIA (Bezerro)          │ RECRIA (Novilho)      │ ENGORDA (Gordo)  │
├─────────────────────────────────────────────────────────────────┤
│ Nascimento → Desmame    │ Desmame → Início Eng. │ Peso inicial 360 │
│ 0–10 meses             │ 10–36 meses           │ → 480–500 kg     │
│ Custo foco: Matriz     │ Custo: Pasto/Confi.   │ 90–120 dias      │
│ GMD: 0,6–0,8 kg/dia    │ GMD: 0,8–1,2 kg/dia   │ GMD: 1,2–1,6 kg/dia
│ Objetivo: Sobreviver   │ Objetivo: Crescer     │ Objetivo: Engordar
│ Indicador: Taxa desmame│ Indicador: GMD, Lotação│ Indicador: GMD, CA
└─────────────────────────────────────────────────────────────────┘
```

---

## 📊 Seu Sistema vs Fases

### CRIA (Nascimento → Desmame) — ✅ Parcial

**O que vocês têm:**
- ✅ Registro de nascimento (coluna "Nascimento De")
- ✅ Brinco por animal
- ✅ Histórico de movimentação (Manejo)
- ✅ Vacinação via calendário sanitário

**O que FALTA:**
- ❌ Rastreamento de mãe (genealogia: qual vaca pariu?)
- ❌ Data de desmame registrada
- ❌ Taxa de desmame (quantos sobreviveram?)
- ❌ Peso ao desmame (referência: 180–220 kg)
- ❌ Coeficiente de natalidade (%)
- ❌ Mortalidade de bezerros (%)

**Esforço para completar:** Baixo (10h)

**Impacto:** ⭐⭐⭐ (saber quem é filho de quem é importante)

---

### RECRIA (Desmame → Engorda) — ❌ Não tem estrutura

**O que é:**
- Fase do novilho: 10–36 meses
- Objetivo: Crescer até peso de entrada engorda (360–400 kg)
- Custo varia muito: R$161,82 (pasto) vs R$485,50 (confinamento)

**O que vocês têm:**
- ✅ Pesagem (registra peso)
- ✅ GMD (calcula ganho)
- ✅ Pastos e lotação
- ⚠️ Lotes (mas não diferencia por fase)

**O que FALTA:**
- ❌ **Aba "Recria"** — separada de Compra/Manejo/Venda
- ❌ Data de **entrada em recria** (quando sai da cria?)
- ❌ Data de **saída da recria** (quando entra em engorda?)
- ❌ **Custo de recria** (pasto × confinamento)
- ❌ **Fase de transição** (weaning protocols)
- ❌ **RIP / TIP** (taxas de ingresso/saída)
- ❌ **Idade à engorda** (referência: 18–24 meses)
- ❌ **Período de crescimento** (deve ser 18–36 meses ideal)

**Softwares com isso:**
- Ponta GA: "Ecossistema GA" (cria → recria → engorda integrado)
- Multsoft: "MultBovinos Recria e Engorda"
- iRancho: Rastreamento por fase

**Esforço para implementar:** Alto (60h)
- Nova aba Recria
- Fluxo entrada/saída
- Custo diferenciado por fase
- Relatório de performance

**Impacto:** ⭐⭐⭐⭐⭐ (crítico se vocês recria)

---

### ENGORDA (Terminação) — ⚠️ Parcial

**O que é:**
- Fase final: 90–120 dias
- Novilho magro (360–400 kg) → boi gordo (480–500 kg)
- Pode ser pasto com suplementação ou confinamento

**O que vocês têm:**
- ✅ Pesagem
- ✅ GMD
- ✅ Lotação (pasto)
- ✅ Lotes
- ✅ Data de venda

**O que FALTA:**
- ❌ **Aba "Engorda"** — separada, com duração esperada
- ❌ **Data de entrada em engorda** (começou quando?)
- ❌ **Peso esperado ao abate** (referência: 480–500 kg)
- ❌ **Dias para abate** (projeção: 90–120 dias)
- ❌ **Conversão alimentar** (CA = ração/ganho)
- ❌ **Acabamento** (qualidade de gordura: 1–5)
- ❌ **Simulador de ponto de corte** para engorda
- ❌ **Histórico de engordas** (engorda 2025 vs 2026)

**Esforço:** Médio (40h)
- Aba Engorda
- Simulador ponto de corte
- Histórico de performance

**Impacto:** ⭐⭐⭐⭐⭐ (crítico se vocês engordam)

---

## 💰 Custos por Fase (Brasil 2026)

```
BEZERRO (aquisição):      R$3.400/cabeça
├─ RECRIA a pasto:        R$161,82 (total, 120d)
│  └ R$1,35 por dia
├─ RECRIA confinado:      R$485,50 (total, 120d)
│  └ R$4,04 por dia
└─ ENGORDA confinado:     R$1.667,16 (total, ~100d)
   └ R$16,67 por dia

TOTAL até abate (pasto+eng): R$3.400 + 161 + 1.667 = R$5.228
TOTAL até abate (conf+conf): R$3.400 + 485 + 1.667 = R$5.552
```

**Isso significa:**
- Diferença é pequena entre pasto e confinamento (R$324 = 6%)
- Mas **confinamento na recria encurta fase em 6 meses** = capital ativo

---

## 🎯 Cenário: Vocês Fazem Pasto + Confinamento

Se vocês:
- ✅ Criam bezerro (nascimento → desmame)
- ✅ Recriam em pasto (desmame → 18 meses)
- ✅ Engordam em confinamento (últimos 120 dias)

**O que vocês precisam:**

### Tier 1 (Essencial) — 60 horas

1. **Aba Recria** (20h)
   - Data de entrada/saída
   - Custo de pasto por cabeça/dia
   - GMD esperado vs realizado
   - Lotação controlada

2. **Aba Engorda** (20h)
   - Data de entrada em engorda
   - Peso esperado ao abate
   - Dias projetados (90–120)
   - Simulador de ponto de corte

3. **Rastreamento de Genealogia** (20h)
   - Mãe → Bezerro
   - Genealogia por lote
   - Relatório: "Qual vaca pariu qual animal?"

---

### Tier 2 (Recomendado) — 40 horas

4. **Conversão Alimentar (CA)** (20h)
   - Ração/ganho em confinamento
   - Integração com sistema de ração

5. **Histórico de Fases** (20h)
   - Comparar recria 2025 vs 2026
   - GMD por fase
   - Custo/fase
   - Benchmarking

---

### Tier 3 (Nice-to-have) — 30 horas

6. **Acabamento/Escore de Carcaça** (15h)
   - Qualidade de gordura 1–5 ao abate
   - Integra com valor de venda

7. **Protocolo de Weaning** (15h)
   - Transição desmame (segregação, ração transitória)
   - Impacto em saúde

---

## 🔴 Problema: Você NÃO tem "Fases" no Sistema

### Hoje, vocês registram assim:

```
COMPRAS:    (bezerro, data, valor)
   ↓
MANEJO:     (nascimento, pesagens, vacinação)
   ↓
VENDAS:     (gordo, data, valor)
```

**Problema:** Não há "Recria" e "Engorda" como **objetos separados**. Tudo é "Manejo" genérico.

### O que softwares fazem:

```
CRIA        (bezerro, nascimento, mãe)
   ↓ [desmame]
RECRIA      (novilho, entrada, pasto, GMD, custo/dia)
   ↓ [360 kg]
ENGORDA     (boi magro, entrada, confinamento, GMD, CA, abate)
   ↓ [500 kg]
ABATE       (boi gordo, venda, resultado por fase)
```

Cada fase tem seus próprios **indicadores**, **custos**, **duração**, **GMD esperado**.

---

## 🎨 Estrutura Proposta para Vocês

### Novo fluxo:

```
┌──────────────────────────────────────────┐
│ CRIA (Aba nova?)                         │
├──────────────────────────────────────────┤
│ Data nascimento, Mãe, Peso ao desmame   │
│ Data desmame, Taxa desmame %             │
│ Vacinas (integra calendário)             │
│ Objetivo: rastreabilidade genealógica   │
└──────────────────────────────────────────┘
         ↓ [Data desmame]
┌──────────────────────────────────────────┐
│ RECRIA (Aba nova)                        │
├──────────────────────────────────────────┤
│ Data entrada, Peso entrada (~160 kg)    │
│ Pasto(s) atribuído(s), Lotação (UA/ha)  │
│ GMD esperado: 0,8–1,0 kg/dia            │
│ GMD realizado: pesagens                  │
│ Custo/dia: mantido alimentação          │
│ Data saída planejada, idade esperada     │
│ Relatório: GMD real vs esperado         │
└──────────────────────────────────────────┘
         ↓ [Peso ≥ 360 kg]
┌──────────────────────────────────────────┐
│ ENGORDA (Aba nova)                       │
├──────────────────────────────────────────┤
│ Data entrada, Peso entrada (~360–400 kg)│
│ Tipo: Pasto c/ Suplementação / Confina. │
│ Dieta (se confi): ração, volumoso       │
│ GMD esperado: 1,2–1,6 kg/dia            │
│ Conversão Alimentar: ração/ganho        │
│ Peso esperado abate: 480–500 kg         │
│ Dias para abate (projeção)               │
│ Simulador ponto de corte (quando vender)│
│ Data saída real, peso real, resultado   │
└──────────────────────────────────────────┘
         ↓ [Venda]
┌──────────────────────────────────────────┐
│ RESULTADO CONSOLIDADO POR FASE           │
├──────────────────────────────────────────┤
│ CRIA:    Custo vaca + Custo bezerro     │
│ RECRIA:  GMD, Custo/dia, Duração        │
│ ENGORDA: GMD, CA, Duração, Resultado    │
│ TOTAL:   Custo total até abate          │
│ MARGEM:  Receita - Custo total          │
│ Comparar: 2025 vs 2026                  │
└──────────────────────────────────────────┘
```

---

## 🎯 RECOMENDAÇÃO PRIORIZADA

**Se vocês trabalham com PASTO + CONFINAMENTO** (típico Brasil):

### Fase 1 (Imediato - 60 horas, 2-3 sprints)

**1. Aba RECRIA** (20h)
- Entrada/saída data
- GMD esperado vs realizado
- Custo de pasto/dia
- **Por quê?** Você talvez esteja recriando sem saber custo real

**2. Aba ENGORDA** (20h)
- Entrada/saída data
- GMD, CA (se confinamento)
- Simulador ponto de corte
- **Por quê?** Saber quando vender é crítico

**3. Genealogia** (20h)
- Qual mãe pariu qual bezerro
- Rastreio de cria
- **Por quê?** Validar eficiência de reprodução

---

### Fase 2 (Depois - 40 horas)

**4. Histórico de Fases**
- Série temporal: recria 2025 vs 2026
- GMD por fase
- Custo total até abate
- **Por quê?** Benchmarking (meu 2026 foi bom?)

**5. Conversão Alimentar** (se confinamento)
- Ração consumida / ganho de peso
- Alerta se CA ruim (cull animal)

---

### Fase 3 (Opcional)

- Protocolo de weaning
- Acabamento/escore

---

## 📊 Comparativo: O que Falta

| Funcionalidade | Seu Sistema | Ponta GA | Multsoft | iRancho | Status |
|---|---|---|---|---|---|
| **Cria** (genealogia) | ⚠️ | ✅ | ✅ | ✅ | Vocês perdem |
| **Recria** (aba separada) | ❌ | ✅ | ✅ | ✅ | **Vocês perdem** |
| **Engorda** (aba separada) | ❌ | ✅ | ✅ | ✅ | **Vocês perdem** |
| **GMD por fase** | ⚠️ | ✅ | ✅ | ✅ | Vocês perdem |
| **CA** | ❌ | ✅ | ✅ | ✅ | Vocês perdem |
| **Ponto de corte** | ❌ | ✅ | ✅ | ✅ | Vocês perdem |
| **Histórico de fases** | ❌ | ✅ | ✅ | ✅ | Vocês perdem |
| **Média móvel financeira** | ✅ | ❌ | ❌ | ❌ | **Vocês ganham** |
| **Pastos + mapa** | ✅ | ⚠️ | ⚠️ | ✅ | Empate |

---

## 💡 Cenários de Implementação

### **Cenário A: Vocês só fazem PASTO (sem confinamento)**

→ Prioridade: **Recria** (20h) + **Genealogia** (20h) = 40h

Sistema fica:
- Bezerro nasce → Rastreia mãe ✅
- Recria em pasto (dados separados) ✅
- Vende novilho (resultado por recria) ✅

---

### **Cenário B: Vocês fazem PASTO + CONFINAMENTO de recria**

→ Prioridade: **Recria** (20h) + **Engorda** (20h) + **Genealogia** (20h) = 60h

Sistema fica:
- Bezerro nasce ✅
- Recria a pasto OU confinado (separa custos) ✅
- Engorda em confinamento ✅
- Sabe custo total até abate ✅

---

### **Cenário C: Vocês fazem PASTO + CONFINAMENTO integral (recria+engorda)**

→ Prioridade: **Tudo** (recria + engorda + genealogia + CA + ponto de corte) = 100h = 4-5 sprints

Sistema fica = **Concorrente de Ponta GA**

---

## 🔥 Diferencial Único

Se vocês implementarem **Recria + Engorda + Genealogia + Ponto de Corte + Média Móvel**:

```
Leigado/Gisleite: "Vender quando atingir 500kg"
Vocês: "Vender quando Custo+Dias > Preço esperado DADO EM QUAL FASE?"

← Única info que ninguém mais tem (até agora)
```

---

## 📝 Resumo em 1 parágrafo

Seu sistema não tem "fases" (cria/recria/engorda) separadas — tudo é manejo genérico. Se vocês trabalham com pasto + confinamento, precisa: (1) **Aba Recria** (20h) — rastreia crescimento em pasto, (2) **Aba Engorda** (20h) — rastreia terminal fase + simulador ponto de corte, (3) **Genealogia** (20h) — qual mãe pariu qual bezerro. Total 60h em 2-3 sprints = vocês viram Ponta GA junior (que é o sistema mais completo de recria+engorda no Brasil).

---

### Fontes
- [Embrapa - Fases cria recria engorda](https://old.cnpgc.embrapa.br/eventos/2000/dcnelore/apostila2.html)
- [iRancho - Fases produção gado corte](https://www.irancho.com.br/pecuaria-de-corte-do-bezerro-a-engorda-final-conheca-as-fases-da-producao/)
- [Rehagro - Fases bovinocultura corte](https://rehagro.com.br/blog/as-fases-da-bovinocultura-de-corte-quais-sao/)
- [Ponta Agro - Recria intensiva](https://pontaagro.com/recria-intensiva-a-pasto-e-gmd/)
- [Multsoft - MultBovinos](https://multsoft.agr.br/multbovinos-recria-e-engorda-a-pasto)
- [iRancho - Custo bezerro engorda](https://www.irancho.com.br/custo-do-bezerro-para-engorda-como-avaliar-se-a-reposicao-vale-a-pena/)
