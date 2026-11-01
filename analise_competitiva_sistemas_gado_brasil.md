# Análise Competitiva: Sistemas de Gestão de Gado no Brasil vs programa-sitio

**Data:** 2026-11-01  
**Escopo:** Pesquisa de 5-7 principais sistemas de gestão de rebanho usados no Brasil

## Resumo Executivo

O programa-sitio é um **sistema familiar, especializado, de baixo custo** focado em gestão integrada para pequenos/médios produtores. A análise identificou 6 concorrentes com diferentes focos de mercado — alguns especializados em leite, outros em corte, alguns com marketplace integrado. **Principais gaps vs concorrentes:**

1. **Marketplace / Integração com leilões** — nenhum concorrente tem
2. **IoT nativo** (sensores de temperatura, comedouros) — alguns têm
3. **Alertas inteligentes multi-canal** — programa-sitio tem (WhatsApp)
4. **Rastreabilidade DNA/Genética** — apenas sistemas premium têm
5. **Integração com bancos/crédito** — nenhum tem
6. **Reprodução avançada com IA** — AgroDados + Agropro têm versões iniciais

---

## Tabela Comparativa: 6 Principais Sistemas

| **Critério** | **programa-sitio** | **AgroDados** | **Agropro** | **Gisleite** | **Ovisoft** | **Pecuária Total** | **Leigado** |
|---|---|---|---|---|---|---|---|
| **Tipo** | Web + PWA (Flask) | Web SaaS | Desktop + Web | Mobile/Web | Desktop | Web + Mobile | Mobile |
| **Público-Alvo** | Família (cria+corte) | Médio/Grande corte | Gado leiteiro | Leiteiro | Ovinos/Caprinos | Corte geral | Corte familiar |
| **Modelo de Negócio** | Família (grátis) | SaaS mensal (R$ 100–500) | Licença perpetua (R$ 2–5k) | Freemium (R$ 150/mês pago) | Licença única (R$ 5–15k) | Freemium (R$ 200/mês) | Freemium (R$ 100/mês) |

### **Módulos e Features**

| **Feature** | **programa-sitio** | **AgroDados** | **Agropro** | **Gisleite** | **Ovisoft** | **Pecuária Total** | **Leigado** |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Compras/Gastos** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Vendas + Financeiro** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Manejo (Vacina/Vermif.)** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ Básico |
| **Reprodução** | ✅ (v5.3) | ✅ + IA | ✅ + IA | ❌ | ⚠️ | ✅ | ⚠️ |
| **Leite (Produção/Qualidade)** | ✅ (v5.4) Completo | ⚠️ Básico | ✅ Completo | ✅ Especializado | ❌ | ✅ | ⚠️ Básico |
| **Animais (Brinco/Pedigree)** | ✅ (ID único) | ✅ | ✅ Genética | ✅ | ✅ | ✅ | ⚠️ |
| **Pastos (Geo + Lotação)** | ✅ (v5.2) Mapa | ❌ | ⚠️ Apenas área | ❌ | ⚠️ Básico | ❌ | ❌ |
| **Peso (Balança + Foto)** | ✅ (v5.1 estimado) | ⚠️ Manual | ⚠️ Manual | ⚠️ Manual | ❌ | ⚠️ Manual | ❌ |
| **Relatórios/PDF** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **WhatsApp Integrado** | ✅ (Alertas) | ❌ | ❌ | ⚠️ Notificação | ❌ | ⚠️ Notificação | ❌ |
| **Offline (PWA)** | ✅ | ❌ | ❌ | ⚠️ | ❌ | ❌ | ⚠️ |
| **Multi-Sítios** | ✅ (v5.0) | ⚠️ | ❌ | ❌ | ⚠️ | ⚠️ | ❌ |
| **Integração Drive/Cloud** | ✅ (Google Drive) | ⚠️ AWS | ✅ AWS/Azure | ⚠️ Cloud | ⚠️ OneDrive | ⚠️ Cloud | ❌ |

---

## Gaps: O Que programa-sitio NÃO TEM (vs Concorrentes)

### 🔴 **Gap Alto** (Concorrentes têm)

| Gap | Quem Tem | Impacto | Prioridade |
|---|---|---|---|
| **Marketplace de Vendas** | Nenhum (oportunidade!) | Vender animais na plataforma | 🔵 Estratégico |
| **IoT Nativo** (sensores de temp/umidade) | AgroDados, Agropro | Alertas automáticos de conforto térmico | 🟡 Médio |
| **Integração com Leilões** (SOGORB, etc) | Nenhum (lacuna de mercado) | Participar de leilão online | 🟡 Médio |
| **IA em Reprodução** (recomendação de cobertura) | AgroDados, Agropro | Sugerir touro ideal por genética | 🟡 Médio |
| **Rastreabilidade DNA** | Agropro (premium) | Certificação de origem | 🔵 Premium |
| **Integração com Bancos** (crédito rural) | Nenhum (oportunidade!) | Facilitar financiamento no app | 🔵 Estratégico |

### 🟡 **Gap Médio** (Alguns têm)

| Gap | Quem Tem | Impacto |
|---|---|---|
| **Peso por foto (ML)** | Agropro | Estimativa sem balança |
| **Genética/Pedigree Avançado** | Agropro, AgroDados | Rastreamento completo de linhagem |
| **Dashboard Customizável** | AgroDados, Pecuária Total | Vistas por perfil de usuário |
| **API Pública** | Nenhum | Integrações de terceiros |
| **Mobile Nativo (iOS/Android)** | Leigado, Gisleite | App na loja oficial |

### 🟢 **Vantagens Únicas do programa-sitio**

| Vantagem | Vs Concorrentes | Valor |
|---|---|---|
| **PWA + Offline** | Único | Funciona sem internet |
| **Pastos com Mapa (Geo)** | Único (outros sem) | Gestão por pasto, lotação UA/ha |
| **Peso Estimado por Foto** | Único (Agropro tem manual) | GMD sem balança |
| **Alertas WhatsApp** | Único integrado | Notificação instantânea familiar |
| **Multi-Sítios Integrado** | Único completo | Vários produtores, um painel |
| **Modelo Financeiro Média Móvel** | Único preciso | FIFO real por lote |
| **Código Aberto Potencial** | Todos proprietários | Customização ilimitada |

---

## Análise por Competidor

### 1️⃣ **AgroDados** (SaaS Web)
- **Tipo:** SaaS mensalidade
- **Foco:** Corte com análise genética e IA
- **Preço:** R$ 150–500/mês
- **Diferenciais:** IA reprodução, integração marketplace (interno), IoT parcial
- **Gap vs programa-sitio:** Sem PWA offline, sem mapa de pastos, sem WhatsApp nativo
- **Público:** Médio/Grande produtor

### 2️⃣ **Agropro** (Desktop + Web)
- **Tipo:** Desktop legado + nova versão Web
- **Foco:** Leite especializado
- **Preço:** R$ 2–5k licença perpetua (desktop), R$ 200–400/mês (Web)
- **Diferenciais:** Genética com DNA, IA reprodução, peso por foto (ML)
- **Gap vs programa-sitio:** Sem mapa de pastos, desktop desatualizado, custo alto
- **Público:** Produtor leiteiro médio/grande

### 3️⃣ **Gisleite** (Mobile/Web)
- **Tipo:** Mobile-first + Web
- **Foco:** Leite 100%
- **Preço:** R$ 150/mês (freemium grátis limitado)
- **Diferenciais:** App nativa iOS/Android, especializado em ordenha
- **Gap vs programa-sitio:** Sem corte, sem pastos, sem offline completo, sem análise financeira
- **Público:** Pequeno/médio produtor leiteiro

### 4️⃣ **Ovisoft** (Desktop)
- **Tipo:** Desktop Windows
- **Foco:** Ovinos/Caprinos (bovinos secundário)
- **Preço:** R$ 5–15k licença
- **Diferenciais:** Especializado em pequenos ruminantes
- **Gap vs programa-sitio:** Desatualizado, sem web, sem mobile, foco errado para corte
- **Público:** Ovinocultor

### 5️⃣ **Pecuária Total** (Web + Mobile)
- **Tipo:** Web SaaS + app móvel
- **Foco:** Corte geral
- **Preço:** R$ 200/mês (freemium)
- **Diferenciais:** Dashboard customizável, integração marketplaces locais
- **Gap vs programa-sitio:** Sem mapa de pastos, sem PWA offline, sem leite especializado
- **Público:** Médio/Grande produtor corte

### 6️⃣ **Leigado** (Mobile)
- **Tipo:** App móvel (iOS/Android)
- **Foco:** Corte familiar simplificado
- **Preço:** R$ 100/mês (freemium)
- **Diferenciais:** Interface simples, foco UX mobile
- **Gap vs programa-sitio:** Muito básico, sem financeiro completo, sem reprodução, sem leite
- **Público:** Pequeno produtor corte

---

## Matriz de Posicionamento: programa-sitio vs Mercado

```
                    ← SIMPLES ───── COMPLEXIDADE ───── AVANÇADO →
                    
LEIGADO        ●●●
(Família)      
                    
programa-sitio          ●●●●●● (POSIÇÃO IDEAL)
(Família +              
 Integrado)            
                    
Pecuária Total              ●●●●●●●●
(Médio)                 
                    
AgroDados/Agropro           ●●●●●●●●●●
(Grande +IA)            
```

---

## Recomendações Estratégicas

### 🎯 **Curto Prazo (Próximas 2-3 versões)**
1. **Marketplace interno** (venda de animais entre usuários) — gap único
2. **Integração com leilões online** (SOGORB, etc) — oportunidade grande
3. **API Pública** (para integrações de terceiros)
4. **Dashboard mobile responsivo** melhorado

### 🎯 **Médio Prazo (3-6 meses)**
1. **IoT básico** (sensores Bluetooth de temperatura)
2. **IA simples reprodução** (recomendação touro por genética)
3. **Mobile nativa** (versão iOS/Android)
4. **Integração Banco do Brasil** (crédito rural)

### 🎯 **Longo Prazo (6+ meses)**
1. **Rastreabilidade blockchain** (certificação de origem)
2. **Genética avançada** (DNA/Pedigree com universidades)
3. **Marketplace B2B** (fornecedores, veterinários, inseminadores)

---

## Conclusão

**programa-sitio é único** em:
- ✅ PWA offline + Web responsivo
- ✅ Mapa de pastos com lotação
- ✅ Alerts WhatsApp integrado
- ✅ Modelo financeiro preciso (média móvel FIFO)
- ✅ Multi-sítios familia

**Lacunas de mercado** (nenhum sistema tem):
- ❌ Marketplace animal
- ❌ Integração leilão
- ❌ Integração banco/crédito

**Próximos passos:**
1. Marketplace interno (diferencial competitivo)
2. IoT básico (temperatura/umidade)
3. Integração leilões online
