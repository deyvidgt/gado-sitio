# 📊 Análise Comparativa: Seu Sistema vs Mercado

**Data:** 28/10/2026  
**Versão do Sistema:** v5.6.0  
**Escopo:** Manejo de gado leiteiro + corte, família (3 membros)

---

## 🟢 O QUE VOCÊ JÁ TEM (Strengths)

### Core - Módulo Financeiro (⭐⭐⭐⭐⭐)
- ✅ **Média móvel perpétua** — custo das vendas (COGS) preciso
- ✅ **Resultado por membro** — divisão equitativa de lucro/prejuízo
- ✅ **Capital imobilizado** — rastreamento do $ parado no rebanho
- ✅ **Invariantes contábeis** — validação matemática (nada desaparece)
- ✅ **Análise por período** (dia/semana/mês/ano)

📌 **Diferencial:** Nenhum concorrente (nem Leigado, nem Gisleite) tem média móvel tão robusta.

---

### Módulo Leiteiro (v5.4) — ⭐⭐⭐⭐
- ✅ **Produção por animal** — registro de ordenha individual
- ✅ **7 abas dedicadas** (Produção, Configuração, Alimentação, Necessidades, Tratamentos, Conforto, Colchão)
- ✅ **Gráficos CCS/CPP** — qualidade do leite
- ✅ **Alertas automáticos** — mastite (CCS >200k), higiene (CPP >100k)
- ✅ **Cálculo de ração** — balanceamento por Embrapa
- ✅ **Dias em lactação** — por vaca individual
- ✅ **Estado do colchão** — previsão de troca
- ✅ **Conforto térmico** — scores 1-5

📌 **Diferencial:** Muito mais completo que Leigado/Gisleite no controle individual de vacas.

---

### Rastreabilidade Animal (v4.3) — ⭐⭐⭐⭐
- ✅ **Brincos com cor + número** (Amarelo 01–99, Geane/Deyvid/Nilson)
- ✅ **Histórico por animal** — todas as movimentações
- ✅ **Comando de voz** — prefill de formulários
- ✅ **Fotos no Google Drive** — linked ao brinco

📌 **Diferencial:** Brinco por cor/dono é elegante; maioria usa só número.

---

### Reprodução (v5.3) — ⭐⭐⭐
- ✅ **Cobertura + Diagnóstico** — sem sensor
- ✅ **Parto em 285 dias** — previsão automática
- ✅ **Taxa de prenhez / IEP** — indicadores
- ✅ **Alertas** — vaca pariu, atrasada, etc.

📌 **Nota:** Básico mas funcional; mercado não investe muito aqui.

---

### Operacional (v5.3) — ⭐⭐⭐⭐
- ✅ **Pastos com mapa** (Leaflet, satélite Esri)
- ✅ **Lotação (UA/ha)** — nível da capacidade
- ✅ **Tarefas + Agenda** — com repetição
- ✅ **WhatsApp automático** — urgentes diários, resumo semanal
- ✅ **Backup diário** — PythonAnywhere
- ✅ **Offline-first** — PWA, IndexedDB, sincronização

📌 **Diferencial:** Integração offline + WhatsApp é rara no mercado.

---

### Análise por Lote (v5.3) — ⭐⭐⭐
- ✅ **FIFO de compra** — venda consome lote mais antigo
- ✅ **Custo/cabeça por lote** — rateio por dia vivo
- ✅ **Resultado realizado** — por lote individual

📌 **Nota:** Inovador; maioria não faz isso.

---

### Peso e Crescimento (v5.1) — ⭐⭐⭐⭐
- ✅ **Peso estimado por foto** — medidas da foto → Schaeffer
- ✅ **Fator de calibração** — ajuste balança vs bruto
- ✅ **GMD (Ganho Médio Diário)** — por animal e período
- ✅ **BCS na estimativa** — avaliação visual

📌 **Diferencial:** Estimativa por foto é inovadora (Fazenda 360 tb tem).

---

## 🔴 O QUE FALTA (Gaps vs Mercado)

### 1️⃣ **Rastreabilidade SISBOV / Regulatória** — ❌
**O que é:** Sistema oficial de rastreabilidade Brasil (exigido para exportação/venda)

**Quem tem:** Fazenda 360, iRancho, MyRebanho, Ponta, iBOI

**Por que importa:**
- Rastreio de origem do animal (entrada → saída)
- SISBOV export para sistema oficial
- Conformidade legal (PLR, GTA)
- Pré-requisito para vender para frigorífico

**Esforço:** Médio (integração com SISBOV API)

**Impacto:** ⭐⭐⭐⭐ (obrigatório para escala)

---

### 2️⃣ **Rastreabilidade GPS / IoT em Tempo Real** — ❌
**O que é:** Brinco com GPS (cercas virtuais, localização, bem-estar)

**Quem tem:** iBOI, iRancho, Ponta

**Por que importa:**
- Localizar animal perdido
- Detecção de cio (movimento ↑)
- Prova de bem-estar animal
- Seguro pecuário mais barato

**Esforço:** Alto (integração com hardware, API de brinco)

**Impacto:** ⭐⭐⭐ (nicho premium)

---

### 3️⃣ **Integração com Balanças Eletrônicas** — ❌
**O que é:** Ler peso direto da balança (RFID + eletrônica)

**Quem tem:** iRancho, Fazenda 360, MyRebanho, Ponta

**Por que importa:**
- Zero erros de digitação
- Histórico automático
- Integração com brinco (qual animal pesou?)

**Esforço:** Médio (driver serial/USB + protocolo da balança)

**Impacto:** ⭐⭐⭐ (precisão no GMD)

---

### 4️⃣ **Saneamento / Calendário Sanitário Detalhado** — ⚠️ Parcial
**O que vocês têm:** Só `saude.py` com Triângulo Mineiro (vacinas, brucelose, vermifugação)

**O que falta:**
- ❌ Tratamento individual (animal + medicamento + dosagem)
- ❌ Histórico de medicações por vaca
- ❌ Controle de resíduo (quarentena de leite)
- ❌ Controle de parasitas (ectoparasitas, endoparasitas)
- ❌ Protocolo de limpeza de bebedouro/cocho
- ❌ Teste de mastite (CMT, Californiano)

**Quem tem:** Leigado, Gisleite, iRancho (parcial)

**Esforço:** Médio (mais abas, mais lógica)

**Impacto:** ⭐⭐⭐⭐ (qualidade do leite depende disso)

---

### 5️⃣ **Nutrição / Ração Individualizada por Vaca** — ⚠️ Parcial
**O que vocês têm:** `racao.py` → calculador genérico (balanceamento por ingrediente)

**O que falta:**
- ❌ Histórico de ração oferecida vs consumido
- ❌ Análise de alimento (proteína bruta medida)
- ❌ Recomendação automática por estágio lactacional
- ❌ Eficiência alimentar (kg leite / kg MS consumido)
- ❌ Custo da ração vs preço do leite
- ❌ Integração com volumoso (`routes_volumosos.py` existe mas vazio?)

**Quem tem:** Leigado, Gisleite (parcial)

**Esforço:** Alto (ciência animal + histórico + análises)

**Impacto:** ⭐⭐⭐⭐ (produção ↑ 20% com ração certa)

---

### 6️⃣ **Genética / Melhoramento Animal** — ❌
**O que é:** Seleção de touros/vacas por DEP (Diferença Esperada na Progênie)

**Quem tem:** Gisleite, MyRebanho

**Por que importa:**
- Escolher qual vaca vender/manter
- Qual touro usar
- Predição de produção dos bezerros
- RGN (Registro Genealógico Nacional)

**Esforço:** Alto (integração com base de dados genéticos)

**Impacto:** ⭐⭐⭐ (longo prazo; rebanho bom em 5 anos)

---

### 7️⃣ **Gráficos e Dashboard Avançado** — ⚠️ Parcial
**O que vocês têm:** Painel principal + gráficos CCS/CPP + lotes

**O que falta:**
- ❌ Séries temporais de produção (últimos 6 meses)
- ❌ Comparativo mês a mês (Jan 2025 vs Jan 2026)
- ❌ Box plot de produção por vaca (quartis)
- ❌ Heatmap de CCS por vaca (matriz vacas × tempo)
- ❌ Dashboard de reprodução (timeline gestação + parto)
- ❌ Projeção de caixa (fluxo de receita)

**Quem tem:** Leigado, Gisleite, iRancho

**Esforço:** Baixo (JS + Recharts/Plot.ly)

**Impacto:** ⭐⭐⭐ (decisão data-driven)

---

### 8️⃣ **Manejo Comportamental / Bem-estar** — ❌
**O que é:** Monitoramento de comportamento (escore de marcha, locomoção, cascos)

**Quem tem:** Gisleite (parcial), iRancho

**Por que importa:**
- CCS alta = inflamação = claudicação
- Casco podre = não vai cio
- Score de locomoção = prediz saída

**Esforço:** Médio (form + foto + scoring)

**Impacto:** ⭐⭐⭐ (previne perdas)

---

### 9️⃣ **Integração com Plataformas de Análise (BI)** — ❌
**O que é:** Export para Power BI, Tableau, Google Sheets

**Quem tem:** Ponta, iRancho, Gisleite

**Por que importa:**
- Análises ad-hoc (SQL custom)
- Dashboard executivo (acionista)
- Integração com contabilista

**Esforço:** Baixo (API + export JSON/CSV)

**Impacto:** ⭐⭐ (nice-to-have)

---

### 🔟 **Simulador de Cenários** — ❌
**O que é:** "E se vender 10 animais em vez de 5? E se o leite cair 10%?"

**Quem tem:** Gisleite (MDA simulator)

**Por que importa:**
- Planejamento financeiro
- Decisão de investimento (compra de terra, vaca)

**Esforço:** Médio (fork estado + cálculos)

**Impacto:** ⭐⭐⭐ (gestão estratégica)

---

## 📈 PRIORIZANDO O QUE IMPLEMENTAR

### Categoria A — **Viável + Alto Impacto** (Próximos 2-3 meses)

1. **Saneamento Detalhado** (✅ Obriga a ter histórico de medicações)
   - Ganho: Qualidade leite melhor → preço sobe
   - Esforço: 40 horas
   - ROI: Alto (toda fazenda precisa)

2. **Gráficos Avançados + Heatmap de CCS**
   - Ganho: Ver padrão de vaca problemática
   - Esforço: 20 horas
   - ROI: Médio (decisão visual)

3. **Integração com Balanças (simulação)**
   - Ganho: GMD mais preciso
   - Esforço: 30 horas (começa com mock, depois real)
   - ROI: Alto

4. **Manejo de Cascos / Locomoção**
   - Ganho: Previne claudicação
   - Esforço: 15 horas
   - ROI: Alto

---

### Categoria B — **Mais Complexo** (6-12 meses)

5. **SISBOV Export** — obrigatório para escalar
6. **Genética / DEP** — diferencial de 5 anos
7. **Simulador de Cenários** — planejamento estratégico

---

### Categoria C — **Nice-to-have** (Depois)

8. **GPS / iBOI** — premium, alto custo
9. **BI Export** — se houver demanda

---

## 🎯 RECOMENDAÇÃO

**Foco nos próximos 3 meses:**

1. **Saneamento** (medicações por vaca + resíduo)
2. **Gráficos heatmap** (CCS por vaca ao longo do tempo)
3. **Locomoção** (escore de marcha)

Isso vai:
- ✅ Fechar o gap de qualidade de leite
- ✅ Dar visibilidade de problema (heatmap mostra qual vaca)
- ✅ Manter vocês à frente de Leigado/Gisleite

**Por que não SISBOV agora?**
- Vocês não fazem venda formal (é familiar)
- Mas deixe a porta aberta na UI (já pensar na estrutura)

---

## 📊 Quadro Comparativo Final

| Funcionalidade | Seu Sistema | Leigado | Gisleite | iRancho | Status |
|---|---|---|---|---|---|
| Média móvel financeira | ✅ | ❌ | ❌ | ❌ | **Vocês ganham** |
| Produção leite individual | ✅ | ✅ | ✅ | ✅ | Empate |
| Reprodução básica | ✅ | ✅ | ✅ | ✅ | Empate |
| Pastos + mapa | ✅ | ⚠️ | ⚠️ | ✅ | Vocês ganham |
| Peso por foto | ✅ | ❌ | ❌ | ❌ | **Vocês ganham** |
| Offline-first | ✅ | ✅ | ❌ | ⚠️ | Vocês ganham |
| WhatsApp automático | ✅ | ⚠️ | ⚠️ | ⚠️ | Vocês ganham |
| Saneamento detalhado | ⚠️ | ✅ | ✅ | ✅ | **Vocês perdem** |
| SISBOV | ❌ | ✅ | ✅ | ✅ | Vocês perdem |
| Gráficos avançados | ⚠️ | ✅ | ✅ | ✅ | Vocês perdem |
| Genética / DEP | ❌ | ⚠️ | ✅ | ❌ | Vocês perdem |
| GPS / IoT | ❌ | ❌ | ❌ | ✅ | Vocês perdem |

---

## 💡 Conclusão

**Vocês já têm um sistema maduro e diferenciado.** Os pontos fracos são todos solucionáveis em 2-3 sprints. O que torna o sistema único:

1. **Média móvel** — ninguém mais tem
2. **Offline + PWA** — raro
3. **Fotos por animal** — visual
4. **Pastos + mapa** — moderno

**Próximo passo:** Saneamento + Gráficos = vocês viram concorrentes de Gisleite.

---

**Fontes de pesquisa:**
- [Gisleite](https://gisleite.cnpgl.embrapa.br/)
- [Leigado](https://leigado.com.br/)
- [iRancho](https://www.irancho.com.br/)
- [Fazenda 360](https://www.vetarq.com.br/)
- [MyRebanho](https://myrebanho.com/)
- [Embrapa - Indicadores](https://www.infoteca.cnptia.embrapa.br/)
- [Ponta Agro](https://pontaagro.com/)
- [iBOI](https://www.canalrural.com.br/)
