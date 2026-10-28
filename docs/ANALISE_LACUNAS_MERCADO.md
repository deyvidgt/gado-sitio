# 📊 Análise de Lacunas — Gado-Sitio vs Mercado (2026)

**Objetivo:** Comparar o gado-sitio com softwares e planilhas de controle de gado (cria, recria, engorda, leiteiro, corte) e identificar funcionalidades faltantes.

**Data:** 2026-10-28  
**Pesquisa:** Programas, apps e planilhas disponíveis no Brasil

---

## 📱 Softwares e Apps Encontrados no Mercado

### **Softwares Especializados (Desktop/Web)**
1. **[iRancho](https://www.irancho.com.br/)** — Gestão integrada de cria/recria/engorda e confinamento
2. **[VSM AGRO](https://www.vsmagro.com.br/)** — Especializado em cria/recria/engorda e matrizes PO
3. **[Embrapec](https://www.embrapa.br/)** — Modelo bioeconômico Embrapa para simulação de sistemas completos
4. **[Leigado](https://leigado.com.br/)** — Leite + corte integrados, com brincos eletrônicos
5. **[Rebanho Pro](https://rebanhopro.com.br/)** — Gestão inteligente com análise de lucratividade
6. **[MultBovinos](https://multsoft.agr.br/)** — Especializado em confinamento (alimentação, custos, desempenho)
7. **[TGC (Tecnologia de Gestão em Confinamentos)](https://pontaagro.com/)** — Gestão completa de confinamentos
8. **[Esteio Gestão](https://blog.esteiogestao.com.br/)** — Indicadores zootécnicos e análise de desempenho

### **Aplicativos Móveis (Android/iOS)**
1. **[Bovinix](https://www.bovinix.com.br/)** — App gratuito com offline, pesagens/sanidade/reprodução
2. **[Cria Rebanho Pro](https://criarebanho.app.br/)** — 2 módulos: Recria (individual) + Corte (lotes)
3. **[Leigado App](https://leigado.com.br/)** — Integração com sensores, brincos eletrônicos, balanças
4. **[Rebanho Fácil](https://www.ar7app.com/rebanho-facil/)** — Gestão simples por brinco/vacinas/vendas
5. **[Ganadero](https://apps.apple.com/br/app/ganadero-gestor-de-rebanho/id6744004302)** — Offline com sync na nuvem
6. **[VacApp](https://vacapp.net/pt)** — Foco em explorações extensivas

### **Planilhas Excel**
- Múltiplas opções de planilhas gratuitas e pagas para controle básico
- Versões específicas: leiteiro, corte, cria/recria, confinamento

---

## ✅ O Que Gado-Sitio JÁ TEM

### **Módulo de Controle Básico** (v1.0–v4.0)
- [x] Cadastro de compras, gastos, vendas
- [x] Registros de manejo (vacinação, vermifugação, etc)
- [x] Controle de rebanho (cabeças, peso médio)
- [x] Estoque de insumos (sal, proteinado, ração)

### **Módulo Leiteiro** (v5.4)
- [x] 7 abas de produção leiteira (produção, configuração, alimentação, necessidades, tratamentos, conforto, colchão)
- [x] Registros de ordenha (individual/total)
- [x] Alertas de mastite (CCS > 200k/400k) e higiene
- [x] Cálculo de ração (NecessidadesCategorias com fórmulas Embrapa)
- [x] Conforto térmico (scores 1-5)

### **Módulo de Reprodução** (v5.3)
- [x] Registros de cobertura (Manejo tipo "Cobertura")
- [x] Diagnóstico de gestação (Manejo tipo "Diagnóstico")
- [x] Parto (cadastro de bezerro com referência a mãe)
- [x] Indicadores: taxa de prenhez, IEP, alertas de atrasadas

### **Módulo de Animais** (v4.3)
- [x] Cadastro individual por brinco (cor + nº 01–99)
- [x] Brincos únicos por animal (ID A0001, A0002, etc)
- [x] Histórico de manejo/vendas/mortes

### **Módulo de Pastos** (v5.2)
- [x] Mapa com contorno GeoJSON
- [x] Movimentação de pasto (Manejo tipo "Movimentação")
- [x] Cálculo de UA/ha e lotação
- [x] Comparação com capacidade recomendada

### **Indicadores v5.8.1** (NOVO)
- [x] Engorda vs Pastagem (GMD, lotes ativos, melhor pasto)
- [x] GMD vs Lotação (análise histórica, correlação)
- [x] Ração Consumo (eficiência alimentar, desperdício %)
- [x] Mortalidade Bezerros (taxa, causas top-5)

### **Financeiro**
- [x] Média móvel perpétua (custo das vendas)
- [x] Resultado por membro (rateio por cabeça)
- [x] Capital imobilizado
- [x] Fluxo de caixa visual (entrada/saída mensal)

### **PWA/Offline**
- [x] Visitas offline (IndexedDB, sync com /api/visitas)
- [x] Fotos offline (redimensionamento, upload depois)

---

## ❌ LACUNAS ENCONTRADAS

### **1️⃣ CONFINAMENTO INTEGRADO** — Prioridade ALTA ⚠️

**O que falta:**
- Nenhuma aba ou módulo específico para confinamento
- Sem registro de dietas por lote/baia
- Sem controle de ração (quantidade oferecida vs consumida)
- Sem custo de alimentação integrado ao financeiro
- Sem acompanhamento de desperdício por baia

**Softwares que têm:**
- [VSM AGRO](https://www.vsmagro.com.br/), [MultBovinos](https://multsoft.agr.br/), [iRancho](https://www.irancho.com.br/), [FeedTratto](https://www.feedtratto.com/), [TGC](https://pontaagro.com/)

**O que implementar:**
```
Aba "Confinamento Lotes" com:
  - Lote ID, Data entrada, Data saída
  - Dieta (mix de ingredientes, custo/dia)
  - Peso inicial, Peso final, GMD
  - Ração oferecida (kg/dia), Consumida (kg/dia), Taxa consumo (%)
  - Conversão alimentar
  - Custo/arroba produzida
  - Status (ativo/encerrado)

Integração financeira:
  - Gasto de ração por lote
  - Resultado por lote (receita - custo)
```

---

### **2️⃣ MELHORAMENTO GENÉTICO** — Prioridade ALTA ⚠️

**O que falta:**
- Nenhuma ferramenta de simulação de acasalamentos
- Sem cálculo automático de coeficiente de endogamia
- Sem alertas de consanguinidade
- Sem histórico genético do animal (pai/mãe, genealogia)
- Sem análise de ganho genético

**Softwares que têm:**
- [iRancho](https://www.irancho.com.br/) (melhoramento genético), [Embrapa Gir Leiteiro](https://www.milkpoint.com.br/noticias-e-mercado/giro-noticias/novo-software-favorece-o-ganho-genetico-e-reduz-a-consanguinidade-na-raca-gir-leiteiro-241475/), [SMART DAIRY (GENEX Brasil)](https://portal.agrosummit.com.br/)

**O que implementar:**
```
Aba "Genealogia" com:
  - Animal ID, Pai, Mãe (referências a outros animais)
  - Raça/Genótipo
  - Escore genético (se disponível)

Simulador de Acasalamento:
  - Selecionar dois animais
  - Calcular coeficiente de endogamia
  - Alertar se > limite recomendado (ex: 10%)
  - Sugerir alternativas (touros não consanguíneos)

Relatório de Ganho Genético:
  - Peso médio por geração
  - Ganho médio anual (kg/ano)
```

---

### **3️⃣ INTEGRAÇÃO COM SENSORES IoT** — Prioridade MÉDIA 🟡

**O que falta:**
- Nenhuma integração com balanças eletrônicas
- Sem suporte a leitura RFID/brincos eletrônicos
- Sem sincronização com dados de peso em tempo real
- Sem sensores de temperatura/umidade para conforto

**Softwares/Tecnologias que têm:**
- [Leigado](https://leigado.com.br/) (integração com balanças/RFID), [iRancho](https://www.irancho.com.br/) (brincos eletrônicos), [iBoi](https://canaldocriador.com.br/noticias/brinco-gps-iboi-rastreamento-gado-up2tech/) (brinco GPS)

**O que implementar:**
```
API REST /api/sensores/pesar para receber:
  - Animal ID (RFID)
  - Peso (kg)
  - Data/hora
  - Origem (balança modelo X)

Auto-registro de pesagem no Manejo
Gráfico de evolução de peso automático
```

---

### **4️⃣ ANÁLISE ECONÔMICA AVANÇADA** — Prioridade MÉDIA 🟡

**O que falta:**
- Sem análise de lucratividade por lote (entrada até venda)
- Sem projeção de preço de mercado vs custo (margem)
- Sem simulador de "ponto de corte" (quando vender é melhor?)
- Sem relatório de "custo por arroba" por período
- Sem comparativo de desempenho (ano anterior vs atual)

**Softwares que têm:**
- [iRancho](https://www.irancho.com.br/) (custo de produção), [Rebanho Pro](https://rebanhopro.com.br/) (lucratividade), [TGC](https://pontaagro.com/) (result analysis)

**O que implementar:**
```
Página /lotes/analise com:
  - Custo acumulado por lote (FIFO)
  - Receita estimada vs realizada
  - Resultado por lote (receita - custo - perdas)
  - Comparativo mensal/anual (este ano vs anterior)
  - Simulador: "Se vender hoje vs esperar X dias"

Indicador: Margem Bruta por Arroba
```

---

### **5️⃣ IDENTIFICAÇÃO VISUAL INTEGRADA** — Prioridade BAIXA 🔵

**O que falta:**
- Cadastro de foto de cada animal (cor, padrões visuais)
- Sem reconhecimento visual (IA para identificar por foto)
- Sem "Fotos Manejo" para registrar procedimentos com imagem

**Softwares que têm:**
- [iRancho](https://www.irancho.com.br/) (fotos + áudio + localização)

**O que gado-sitio já tem:**
- [x] Aba Fotos (Google Drive) com proxy/cache
- Falta: integrar foto do animal no cadastro de brinco

**O que implementar:**
```
Campo "Foto Principal" na aba Animais (última foto do Drive)
Galeria de fotos do animal na página /animais/<id>
```

---

### **6️⃣ ALERTAS SANITÁRIOS AVANÇADOS** — Prioridade MÉDIA 🟡

**O que falta:**
- Sem histórico detalhado de tratamentos por animal
- Sem alertas automáticos (ex: "Animal não vacinado há 6 meses")
- Sem protocolo sanitário por categoria (bezerro/recria/adulta)
- Sem integração com calendário Triângulo Mineiro (já tem em `saude.py`)

**O que gado-sitio já tem:**
- [x] Aba Medicações (v5.7)
- [x] Calendário sanitário (saude.py)
- [x] Alertas no WhatsApp

**O que implementar:**
```
Página /saude-animais com:
  - Filtro por categoria (bezerro/recria/adulta/vaca)
  - Status de vacinação por animal (em dia / atrasada)
  - Próximas vacinas (data recomendada)
  - Histórico de medicações por animal
```

---

### **7️⃣ RASTREABILIDADE E CERTIFICAÇÃO** — Prioridade BAIXA 🔵

**O que falta:**
- Sem rastreamento de origem (CGR/SISBOV)
- Sem certificação de propriedade livre de doenças
- Sem registro de brinco/microchip para venda
- Sem guia de transporte digital

**Softwares que têm:**
- [Leigado](https://leigado.com.br/) (integração com sistemas oficiais)
- [iBoi](https://www.bra1.com.br/agronegocio/id-704696/novo_brinco_inteligente_permite_rastrear_gado_em_tempo_real_e-facilitar-emprestimos-bancarios) (rastreamento + facilitador de empréstimo)

---

### **8️⃣ SIMULAÇÃO E PREVISÃO** — Prioridade BAIXA 🔵

**O que falta:**
- Sem simulador de cenários (ex: "Se aumentar lotação, qual será o GMD?")
- Sem previsão de custo/cabeça por período
- Sem Embrapec (simulador bioeconômico Embrapa)

**Softwares que têm:**
- [Embrapec](https://www.embrapa.br/) (modelo bioeconômico com simulação)
- [iRancho](https://www.irancho.com.br/) (projeções de desempenho)

---

## 📋 RESUMO DAS LACUNAS POR PRIORIDADE

| # | Funcionalidade | Prioridade | Impacto | Esforço | Status |
|---|---|---|---|---|---|
| 1 | Confinamento (dieta, ração, GMD/lote) | 🔴 ALTA | Múltiplos sistemas perdem clientes com confinamento | Médio | ❌ Não tem |
| 2 | Melhoramento genético (simulador, endogamia) | 🔴 ALTA | Criadores/matrizes exigem isso | Alto | ❌ Não tem |
| 3 | Integração IoT (balanças, RFID, sensores) | 🟡 MÉDIA | Automação + dados em tempo real | Alto | ❌ Não tem |
| 4 | Análise econômica avançada (lotes, margem, simulador) | 🟡 MÉDIA | Decisão de venda melhorada | Médio | ⚠️ Parcial |
| 5 | Alertas sanitários automáticos por animal | 🟡 MÉDIA | Saúde preventiva | Baixo | ⚠️ Parcial |
| 6 | Fotos do animal integradas | 🔵 BAIXA | UX melhorada | Baixo | ⚠️ Parcial |
| 7 | Rastreabilidade/Certificação | 🔵 BAIXA | Venda premium + crédito | Alto | ❌ Não tem |
| 8 | Simulação/Embrapec | 🔵 BAIXA | Planejamento estratégico | Muito alto | ❌ Não tem |

---

## 🎯 RECOMENDAÇÃO IMEDIATA

**Para competir no mercado (curto prazo):**

1. **Prioridade 1 (Novembro 2026):** Implementar **Confinamento** (aba Confinamento Lotes + integração financeira)
2. **Prioridade 2 (Dezembro 2026):** Implementar **Melhoramento Genético** (genealogia + simulador de acasalamento)
3. **Prioridade 3 (Janeiro 2027):** API de **Integração com Sensores** (balanças, RFID)

**Diferenciais do gado-sitio hoje:**
- ✅ Multi-site integrado (coisa rara no mercado)
- ✅ Módulo leiteiro + corte (maioria tem um OU outro)
- ✅ Fotos + Drive integrado
- ✅ PWA com offline
- ✅ Open-source (vantagem para consultores)

---

## 📚 FONTES

- [iRancho](https://www.irancho.com.br/)
- [VSM AGRO](https://www.vsmagro.com.br/)
- [Leigado](https://leigado.com.br/)
- [MultBovinos - Multsoft](https://multsoft.agr.br/)
- [Rebanho Pro](https://rebanhopro.com.br/)
- [Bovinix](https://www.bovinix.com.br/)
- [Cria Rebanho Pro](https://criarebanho.app.br/)
- [Embrapa Pecuária](https://www.embrapa.br/)
- [Indicadores Zootécnicos - ReHagro](https://rehagro.com.br/blog/indicadores-zootecnicos-pecuaria-de-corte/)
- [Embrapa Gir Leiteiro - Ganho Genético](https://www.milkpoint.com.br/noticias-e-mercado/giro-noticias/novo-software-favorece-o-ganho-genetico-e-reduz-a-consanguinidade-na-raca-gir-leiteiro-241475/)
