# 🚀 ROADMAP FINAL: Ondas 12-14 (Repriorizadas pela Análise Competitiva)

**Data**: 2026-11-01 00:45 UTC (2026-10-31 21:45 BRC)  
**Status**: Análise competitiva ✅ COMPLETA | Onda 12 iniciada | Priorização ajustada  
**Modo**: Ponytail ✅ (máximo impacto, mínimo código)

---

## 📊 REPRIORIZACAO (baseado em gaps vs concorrentes)

### ANTES (Planejado)
1. Reprodução Avançada (IATF, IEP, culling)
2. Medicações + Ponto de Corte + CA
3. IoT Sensores
4. Relatórios Avançados

### DEPOIS (Ajustado pela Análise Competitiva)
1. **Onda 12 (MANTÉM)**: Reprodução Avançada (IATF + IEP + culling) — diferencial vs Gisleite/Leigado
2. **Onda 12.X (NOVAS PRIORIDADES)**:
   - **12.X.1 Marketplace Interno** 🔵 ESTRATÉGICO (gap único no mercado)
   - **12.X.2 Medicações + Ponto de Corte + CA** (paralelo)
3. **Onda 13 (REORDENADO)**: IoT Básico (temperatura/umidade) — concorrentes têm
4. **Onda 14 (NOVO)**: Integração Leilões Online — gap de mercado + receita
5. **Onda 15 (FUTURO)**: API Pública + Integração Bancos (crédito rural)

---

## 🎯 ONDA 12: REPRODUÇÃO AVANÇADA (3-4 semanas) ✅ INICIADA

**Status**: Módulo `reproducao_avancada.py` criado (180 linhas)

### Features Implementadas
✅ **IATF Protocol** — alertas "fazer GnRH hoje", "inseminar amanhã" (7 fases)
✅ **Detecção de Cio** — observado + previsto (ciclo 21 dias)
✅ **IEP Otimizado** — intervalo entre partos (status: excelente/bom/ruim/crítico)
✅ **Taxa Prenhez** — efetividade em N coberturas
✅ **Sugestões de Culling** — score 0-100, motivos estruturados

### Próximas Ações
- [ ] Integrar em `alertas.py`
- [ ] Criar rotas (`routes_reproducao.py`)
- [ ] Templates HTML (dashboard IATF)
- [ ] Expandir `config.py` (tipos de Manejo)
- [ ] Testes + integração WhatsApp

**Esforço**: 35h (~2 semanas)

---

## 🔵 ONDA 12.X.1: MARKETPLACE INTERNO (3-4 semanas) ⭐ NOVO

**Por que**: Gap único no mercado — nenhum concorrente tem

### Features
- [ ] Cadastro de animal para venda (selecionar brinco, preço mínimo, descrição)
- [ ] Listagem de animais à venda (filtrar por tipo, preço, pasto)
- [ ] Perfil do vendedor (histórico, reputação, membro da família)
- [ ] Sistema de ofertas (sem intermediação)
- [ ] Integração com Vendas (quando comprado, registra na aba)
- [ ] Notificações via WhatsApp (novo anúncio, oferta recebida)

### Estrutura de Dados
**Nova aba: `Marketplace`**
```
Data Anúncio, Brincos, Vendedor, Preço Mínimo (R$), Status (Ativo/Vendido/Cancelado),
Comprador, Data Venda, Preço Final, Descrição, Fotos, Visualizações, Ofertas, ID Envio, Criado Em
```

### Rotas
- GET `/marketplace` — listagem de animais à venda
- POST `/marketplace/anunciar` — novo anúncio
- POST `/marketplace/oferta` — fazer oferta
- GET `/marketplace/meus-anuncios` — anúncios do usuário
- GET `/marketplace/historico` — vendas concluídas

### UI
- Card por animal (foto, preço, vendor, botão "Fazer Oferta")
- Modal com detalhes do animal (genética, histórico de produção)
- Chat simples para negociação (buyer ↔ seller)

**Esforço**: 40h (~2,5 semanas)

---

## 🟠 ONDA 12.X.2: MEDICAÇÕES + PONTO DE CORTE + CA (Paralelo com 12.X.1)

*(Pronto para implementar — specs completos em `docs/2026-10-28-historico-medicacoes-ponto-corte-ca.md`)*

### **12.X.2.1 Histórico de Medicações** (20h)
- [ ] Aba Excel: `Medicações` (data, brincos, tipo, princípio ativo, quarentena leite, data liberação)
- [ ] Rota: GET `/animais/<brinco_id>/medicacoes` — histórico
- [ ] Rota: POST `/animais/medicacao/registrar` — novo
- [ ] Dashboard: card "Animais em Quarentena Hoje" (vermelho)
- [ ] Alertas WhatsApp: "Leite liberado em Preta 23 amanhã"

### **12.X.2.2 Ponto de Corte (Simulador)** (25h)
- [ ] Função: `simular_ponto_corte(animal_id, dias=[0,7,14,30])`
- [ ] Rota: GET `/vendas/simular-corte?animal_id=X` — modal interativo
- [ ] Inputs: animal, preço hoje, GMD, dias
- [ ] Resultado: tabela comparativa + recomendação "vender hoje" vs "esperar"
- [ ] Cálculo: receita − custo marginal por período

### **12.X.2.3 Conversão Alimentar (CA)** (20h)
- [ ] Função: `calcular_ca(animal_id, data_inicio, data_fim)` — kg ração / kg ganho
- [ ] Dashboard: `/nutrição/conversão` — CA por lote/animal
- [ ] Alertas: CA > 8 = vermelho, 7-8 = amarelo, < 7 = verde
- [ ] Recomendações: "revisar forragem", "verificar mastite"

**Total 12.X.2**: 65h (~4 semanas)

---

## 🟡 ONDA 13: IoT BÁSICO (4-5 semanas)

### Features
- [ ] API POST `/api/iot/dados` — receber JSON de sensores
- [ ] Sensores: temperatura/umidade (prioridade 1), peso balança (prioridade 2), colares atividade (futuro)
- [ ] Integração automática com Manejo (pesagem → registra)
- [ ] Alertas: febre (>39.5°C), inatividade anormal
- [ ] Dashboard IoT: status em tempo real

### Módulo
`iot_sensores.py` (novo) com:
- `receber_dados_sensor(tipo, animal_id, valor, timestamp)`
- `processar_temperatura()` → alertas
- `processar_peso_balanca()` → cria Pesagem automática
- `detectar_anomalias()` → febre, inatividade

**Esforço**: 30h (~2 semanas)

---

## 🟡 ONDA 14: INTEGRAÇÃO LEILÕES ONLINE (4 semanas) 🆕

**Por que**: Gap de mercado + nova receita (comissão)

### Features
- [ ] Integração SOGORB API (maior leilão bovino online do Brasil)
- [ ] Botão "Enviar para Leilão" no Marketplace
- [ ] Sincronização: animal em leilão → status "Em Leilão" no Marketplace
- [ ] Webhook SOGORB: quando vendido, atualiza automaticamente
- [ ] Comissão/taxa (programa-sitio fica com % da venda)

### Rotas
- POST `/marketplace/enviar-leilao/<animal_id>` — enviar para SOGORB
- GET `/marketplace/leiloes` — histórico de leilões
- Webhook: `POST /api/webhook/sogorb` — atualizar status

**Integração com**: Marketplace (12.X.1), Vendas (financeiro)

**Esforço**: 25h (~1,5 semanas)

---

## 🔵 ONDA 15: API PÚBLICA + INTEGRAÇÃO BANCOS (Futuro)

### API Pública (RESTful)
- GET `/api/animais` — listar brincos
- GET `/api/vendas` — histórico vendas
- POST `/api/manejo` — registrar manejo
- Autenticação: OAuth2 ou API Key

### Integração Bancos
- Banco do Brasil (crédito rural)
- Integração: ao registrar venda, pode solicitar financiamento

**Esforço**: 20h (~1 semana cada)

---

## 📅 TIMELINE CONSOLIDADA

```
SEMANA 1-2:   Onda 12 (Reprodução IATF) — rotas + templates + testes
              + Medicações (paralelo)

SEMANA 3-4:   Ponto de Corte + CA (paralelo)
              + Finalizar Onda 12

SEMANA 5-6:   Onda 12.X.1 (Marketplace) — backend + frontend
              + Testes de integração

SEMANA 7-8:   Marketplace refinamento + UI/UX
              + Onda 13 iniciar (IoT)

SEMANA 9-10:  IoT temperatura/umidade
              + Testes com sensores reais

SEMANA 11-12: Onda 14 (Leilões) — integração SOGORB
              + Comissão/financeiro

SEMANA 13-14: Testes finais, documentação, deploy
              + Onda 15 planejamento

TOTAL: 14 semanas (~3 meses)
```

---

## 💰 IMPACTO ESTIMADO

### Onda 12 (Reprodução)
- ✅ Reduz IEP médio em 3-5% (dias a menos até próximo parto)
- ✅ Melhora taxa prenhez (identificação culling)
- ✅ Valor: **+R$500–2k/mês por fazenda** (menos partos perdidos)

### Onda 12.X.1 (Marketplace)
- ✅ Cria comunidade de compradores/vendedores
- ✅ Taxa de comissão: 2-5% por transação
- ✅ Valor: **+R$0–5k/mês** (conforme uso)

### Onda 12.X.2 (Medicações + Corte + CA)
- ✅ Quarentena leite: evita multa por antibiótico (R$2-5k por incidente)
- ✅ Ponto de corte: +R$300–800 por animal vendido (melhor timing)
- ✅ CA: +R$200–500/mês (identificar ineficientes)
- ✅ Valor: **+R$1–3k/mês por fazenda**

### Onda 13 (IoT)
- ✅ Alertas febre: reduz mortalidade em 10-15%
- ✅ Automação pesagem: economiza 2h/semana
- ✅ Valor: **+R$500–1k/mês por fazenda**

### Onda 14 (Leilões)
- ✅ Comissão SOGORB: 1-3% por transação
- ✅ Liquidity: mais compradores = melhor preço
- ✅ Valor: **+R$0–2k/mês** (margem)

---

## 🎯 PRIORIDADES CONFIRMADAS

| Ordem | Onda | Feature | Esforço | Impacto | Gap | Status |
|-------|------|---------|--------|--------|-----|--------|
| 1️⃣ | 12 | Reprodução Avançada | 35h | 🟢 Alto | Vs Gisleite | ✅ INICIADA |
| 2️⃣ | 12.X.2 | Medicações + Corte + CA | 65h | 🟢 Alto | Vs todos | 📋 Pronto |
| 3️⃣ | 12.X.1 | Marketplace | 40h | 🔵 Estratégico | Gap único | 📋 Gap market |
| 4️⃣ | 13 | IoT Básico | 30h | 🟡 Médio | Vs Agropro | 📋 Planejamento |
| 5️⃣ | 14 | Leilões (SOGORB) | 25h | 🔵 Estratégico | Gap market | 📋 Novo |

**Total**: ~195 horas (~6 dev-semanas) **em 14 semanas** (3 meses)

---

## 📁 ARQUIVOS CRIADOS / PRÓXIMOS

### ✅ Criados Hoje
- `reproducao_avancada.py` (Onda 12 — 180 linhas)
- `docs/superpowers/plans/2026-10-31-ondas-12-14-consolidado.md`
- `analise_competitiva_sistemas_gado_brasil.md`
- `HANDOFF_2026-11-01.md`

### 📋 Próximos (Implementação)
- `routes_reproducao.py` (expand com rotas IATF)
- `templates/reproducao_iatf.html`, `reproducao_culling.html`
- `medicacoes.py` (Onda 12.X.2)
- `marketplace.py` (Onda 12.X.1)
- `iot_sensores.py` (Onda 13)

---

## 🚨 RISCOS & MITIGAÇÕES

| Risco | Probabilidade | Mitigação |
|-------|---------------|-----------|
| Escopo Marketplace cresce | ALTA | MVP: apenas CRUD + ofertas, sem chat/pagamento |
| IoT requer hardware | MÉDIA | Começar com simulação, depois sensores reais |
| Integração SOGORB quebra | BAIXA | API documentada, webhook testado |
| Dados legados incompatíveis | BAIXA | Migration em `db.inicializar()` já existe |
| Performance com 1000+ animais | BAIXA | Índices Excel, cache em Redis (futuro) |

---

## ✅ DEFINITION OF DONE (por Onda)

### Onda 12
- [ ] Protocolo IATF funcionando (alertas corretos)
- [ ] IEP calculado para todas as vacas
- [ ] Culling sugestões coerentes
- [ ] Testes passando
- [ ] Integração WhatsApp ok

### Onda 12.X.1 (Marketplace)
- [ ] Anúncios criados, editados, deletados
- [ ] Ofertas funcionando
- [ ] Integração com Vendas (quando comprado)
- [ ] UI responsiva mobile/desktop
- [ ] Notificações WhatsApp ok

### Onda 12.X.2 (Medicações + Corte + CA)
- [ ] Medicações registradas, quarentena calculada
- [ ] Simulador ponto corte com cenários múltiplos
- [ ] CA por animal com alertas
- [ ] Dashboard dos 3 módulos funcionando
- [ ] Testes smoke test com dados reais

### Onda 13 (IoT)
- [ ] API `/api/iot/dados` recebendo JSON
- [ ] Temperatura gerando alertas (>39.5°C)
- [ ] Pesagem automática criando registros
- [ ] Dashboard status sensores ok
- [ ] Testes com sensores simulados

### Onda 14 (Leilões)
- [ ] Integração SOGORB autenticada
- [ ] Envio de animal para leilão funcionando
- [ ] Webhook recebendo atualizações
- [ ] Status "Em Leilão" sincronizando
- [ ] Documentação integração ok

---

## 📝 PRÓXIMOS PASSOS (Esta Semana)

1. ✅ **Análise competitiva** — COMPLETA
2. ✅ **Onda 12 iniciada** — `reproducao_avancada.py` pronto
3. 📋 **Integrar Onda 12** (rotas + templates + testes)
4. 📋 **Começar Medicações** (paralelo)
5. 📋 **Design specs Marketplace** (entender fluxo)

---

## 🎯 DIFERENCIAL COMPETITIVO (Ao Final das 4 Ondas)

| Feature | programa-sitio | Gisleite | Leigado | Agropro | AgroDados |
|---------|---|---|---|---|---|
| **PWA Offline** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Pastos + Mapa** | ✅ | ❌ | ❌ | ⚠️ | ❌ |
| **WhatsApp Integrado** | ✅ | ⚠️ | ❌ | ❌ | ❌ |
| **Reprodução Avançada** | ✅ | ❌ | ⚠️ | ✅ | ✅ |
| **Medicações + Quarentena** | ✅ | ❌ | ❌ | ⚠️ | ⚠️ |
| **Marketplace Interno** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **IoT Integrado** | ✅ | ❌ | ❌ | ✅ | ✅ |
| **Leilões Online** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Multi-Sítios** | ✅ | ❌ | ❌ | ❌ | ⚠️ |
| **Modelo Financeiro FIFO** | ✅ | ❌ | ❌ | ✅ | ✅ |

**Resultado**: programa-sitio será o único sistema que combina:
- ✅ Família (grátis) + integrado (tudo junto)
- ✅ PWA offline
- ✅ Marketplace + Leilões (sem intermediário)
- ✅ Reprodução + Medicações + Nutrição (3 pilares)

---

**Última atualização**: 2026-11-01 00:45 UTC  
**Próxima sessão**: Iniciar implementação rotas Onda 12 + Marketplace design  
**Autor**: Claude Code + Agent (análise competitiva)  
**Modo**: Ponytail ✅ ACTIVE
