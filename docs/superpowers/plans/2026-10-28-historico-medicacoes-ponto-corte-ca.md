# 📋 Plano de Implementação: 3 Funcionalidades Críticas

**Data:** 28/10/2026  
**Escopo:** Histórico de medicações + Ponto de Corte + Conversão Alimentar  
**Esforço estimado:** 65 horas  
**Fases:** 3 sprints de 2 semanas (paralelo)

---

## 1️⃣ Histórico de Medicações por Vaca

### Objetivo
Rastrear qual medicação foi dada a qual animal, quando, dosagem, e impacto em quarentena de leite.

### Estrutura de Dados

**Nova aba Excel: "Medicações"**
```
Colunas:
- Data (dd/mm/aaaa)
- Brincos (ex: "Amarelo 01 #A0001, Amarelo 02 #A0002")
- Tipo Medicação (Antibiótico IM, IV, Oral, Antiparasitário, etc.)
- Principio Ativo (ex: "Penicilina benzatina", "Ivermectina")
- Dosagem (ex: "20 mL", "1 comprimido")
- Via (IM / IV / Oral / Tópico)
- Motivo (Mastite, Metrite, Ferida, Controle parasitário, etc.)
- Quarentena Leite (dias) — automaticamente >= 3 dias antibiótico
- Data de Liberação (Data + Quarentena)
- Responsável
```

### Implementação

**Backend (`medicacoes.py`):**
```python
def registrar_medicacao(data, brincos, tipo, principio, dosagem, via, motivo, quarentena_leite):
    # 1. Validar brincos (existem em Animais?)
    # 2. Calcular data_liberacao = data + quarentena_leite
    # 3. Guardar em aba Medicações
    
def historico_animal(brinco_id):
    # Retorna todas as medicações do animal + data liberação leite
    
def alertas_medicacoes():
    # Hoje, quais animais estão em quarentena?
    # Qual data libera?
```

**Frontend (`routes_animais.py` novo endpoint):**
- GET `/animais/<brinco_id>/medicacoes` — histórico por animal
- POST `/animais/medicacao/registrar` — form novo registro
- GET `/alertas/quarentena-leite` — quais animais em quarentena hoje?

**Dashboard:**
- Card "Animais em Quarentena Hoje" — vermelho se houver
- Histórico de medicações por vaca (tabela)
- Gráfico: medicações/tipo ao longo do tempo

### Validações
- ✅ Brinco deve existir em Animais
- ✅ Data não pode ser futura
- ✅ Quarentena >= 3 dias para antibiótico
- ✅ Via correta conforme tipo

### Esforço: 20 horas
- Config + estrutura de dados: 3h
- Backend + CRUD: 7h
- Frontend + form: 5h
- Dashboard + alertas: 5h

---

## 2️⃣ Ponto de Corte (Simulador de Quando Vender)

### Objetivo
Responder: "Vendo HOJE por R$X ou espero 30 dias por R$Y?"

### Fórmula Lógica

```
HOJE:
  Receita = Peso_Atual × Preço_Hoje
  Custo = 0 (já gasto)
  Resultado = Receita - Custo_já_investido
  Margem = Resultado / Custo_total

ESPERAR N DIAS:
  Peso_Futuro = Peso_Atual + (GMD × N)
  Receita = Peso_Futuro × Preço_Esperado_N_dias
  Custo = Custo_diário × N
  Resultado = Receita - Custo_já_investido - Custo_N_dias
  Margem = Resultado / Custo_total

DECISÃO:
  Se Resultado_Hoje > Resultado_N_dias
    → Vender HOJE
  Senão
    → Esperar
```

### Implementação

**Backend (`calculos.py` novo função):**
```python
def simular_ponto_corte(animal_id, dias_futuros=[0, 7, 14, 30, 60]):
    # Buscar histórico do animal: peso, custo acumulado, GMD
    # Buscar preço atual do leite/corte
    # Simular preço futuro (declínio típico: -2% por semana em corte)
    # Retornar tabela comparativa
    
    return {
        "hoje": {"peso": X, "receita": Y, "resultado": Z},
        "7d": {"peso": X, "receita": Y, "resultado": Z},
        "14d": {...},
        "melhor_data": "hoje" ou "7d" ou "14d"
    }
```

**Frontend (`routes_vendas.py` novo endpoint):**
- GET `/vendas/simular-corte?animal_id=XXX` — modal interativo
- Form inputs:
  - Animal (autocomplete de brincos)
  - Preço hoje (R$/kg ou R$/arroba)
  - GMD esperado (padrão por fase/pasto)
  - Dias a simular (0, 7, 14, 30, 60)
  - Custo diário (opcional, default = média histórica)

**UI:**
```
┌────────────────────────────────────┐
│ Simulador de Ponto de Corte        │
├────────────────────────────────────┤
│ Animal: [Amarelo 05 #A0005]        │
│ Peso Atual: 450 kg                 │
│ GMD: 0,9 kg/dia                    │
│ Preço Hoje: R$30/kg                │
│ Custo/Dia: R$18                    │
│                                    │
│ ┌─ Simulação ─────────────────┐   │
│ │ Hoje:    R$13.500 - R$800 = │   │
│ │          +R$12.700 ✓ MELHOR │   │
│ │ +7d:     R$13.400 - R$926 = │   │
│ │          +R$12.474           │   │
│ │ +14d:    R$13.250 - R$1.052│   │
│ │          +R$12.198           │   │
│ │ +30d:    R$12.950 - R$1.340│   │
│ │          +R$11.610           │   │
│ └──────────────────────────────┘   │
│                                    │
│ 🎯 Recomendação: Vender HOJE!     │
└────────────────────────────────────┘
```

### Integrações
- Buscar preço do leite/corte de `calculos._build_timeline()`
- Buscar GMD do animal (`pesagem.py`)
- Buscar custo acumulado (`calculos._simular_media_movel()`)

### Esforço: 25 horas
- Cálculo + lógica: 8h
- Backend + integração: 7h
- Frontend + modal interativo: 7h
- Testes + validações: 3h

---

## 3️⃣ Conversão Alimentar (CA)

### Objetivo
Rastrear: "Esse animal gastou 7 kg de ração para ganhar 1 kg" → CA = 7:1

### Estrutura de Dados

**Estender Manejo tipo "Alimentação":**
```
Tipo Manejo:  "Alimentação"
Qtd Cabeças:  1
Produto:      "Ração Concentrada 18%PB" ou "Silagem"
Qtd Sacos:    2 (para Ração) ou Kg (para volumoso)
Data:         dd/mm/aaaa
Descrição:    "Fornecido em comedouro"
Brincos:      "Amarelo 01 #A0001"  ← NOVO: animal individual
```

**Novo bloco em Manejo: "Consumo de Alimentação"**
```
Colunas novas em MANEJO:
- Tipo Alimento (Ração Concentrada, Silagem, Pasto, Suplementação, etc.)
- Quantidade (kg ou sacos)
- Data Fornecimento
- Animal (Brinco) — para rastrear consumo individual
- Custo Unitário (R$/kg ou R$/saco) — para CA financeiro
```

### Implementação

**Backend (`calculos.py`):**
```python
def calcular_ca(animal_id, data_inicio, data_fim):
    # 1. Somar alimento consumido (kg MS = matéria seca)
    # 2. Ganho de peso (pesagem_fim - pesagem_inicio)
    # 3. CA = alimento_kg / ganho_kg
    
    return {
        "alimento_consumido_kg": X,
        "ganho_peso_kg": Y,
        "ca": X/Y,  # 7:1, 6:1, etc
        "ca_financeiro": custo_alimento / ganho_peso  # R$/kg ganho
    }

def alertas_ca(animal_id):
    # CA > 8:1 em confinamento? RUIM
    # Animal candidato a culling?
    pass
```

**Frontend (`routes_lotes.py` novo endpoint):**
- GET `/lotes/<lote_id>/ca` — CA por lote (grupo de animais)
- GET `/animais/<animal_id>/ca` — CA histórico do animal
- Dashboard:
  - Tabela: Animal | CA | Período | Alimento Total | Ganho | Custo/kg
  - Gráfico: CA ao longo do tempo (trend)
  - Alerta: CA > 8 = RED, 7-8 = YELLOW, <7 = GREEN

### Integrações
- Consumo: Registra em Manejo tipo "Alimentação"
- Ganho: Busca em `pesagem.py` (peso final - peso inicial)
- Custo: Integra com preços de alimento (cache)

### Validações
- ✅ Animal deve ter pelo menos 2 pesagens (inicial + final)
- ✅ Data de alimento >= data_inicio e <= data_fim
- ✅ Alimento deve ter categoria/tipo válida
- ✅ CA deve ser > 1 (senão há erro)

### Esforço: 20 horas
- Estrutura + migrations: 5h
- Backend + cálculos: 7h
- Frontend + dashboard: 5h
- Testes + alertas: 3h

---

## 📋 Checklist de Implementação

### Fase 1: Preparação (8 horas)
- [ ] Criar abas Excel novas (Medicações, estender Manejo)
- [ ] Atualizar `config.py` com COLUNAS_MEDICACOES
- [ ] Atualizar `db.py` para migração de colunas
- [ ] Testes de carregamento de dados

### Fase 2: Backend (30 horas)
- [ ] `medicacoes.py` — CRUD + validações
- [ ] `calculos.py` — ponto_corte() e ca()
- [ ] `pesagem.py` — integração com CA
- [ ] `routes_animais.py` — endpoints medicações
- [ ] `routes_vendas.py` — endpoint ponto de corte
- [ ] `routes_lotes.py` — endpoint CA
- [ ] Testes unitários

### Fase 3: Frontend (20 horas)
- [ ] Página medicações por animal
- [ ] Modal simulador ponto de corte
- [ ] Dashboard CA por lote/animal
- [ ] Alertas (quarentena leite, CA alto)
- [ ] Forms responsive

### Fase 4: Integração + Deploy (7 horas)
- [ ] Integração entre módulos
- [ ] Smoke test com dados reais
- [ ] Dashboard principal atualizado
- [ ] Documentação
- [ ] Deploy

---

## 🎯 Prioridade de Implementação

**Sprint 1 (Semana 1-2): Medicações (20h)**
- Mais crítico para qualidade de leite
- Menor escopo
- Rápido retorno (alerta quarentena)

**Sprint 2 (Semana 3-4): Ponto de Corte (25h)**
- Maior impacto financeiro
- Depende de GMD + preço (já existem)
- Pode rodar paralelo com Medicações

**Sprint 3 (Semana 5-6): Conversão Alimentar (20h)**
- Integração com Manejo (mais complexa)
- Depende de dados históricos
- Roda paralelo com Ponto de Corte

**Timeline:** 6 semanas, 1-2 devs

---

## ✅ Definition of Done

### Medicações
- [ ] Aba Excel criada e migrada
- [ ] CRUD completo (criar, editar, deletar)
- [ ] Alertas funcionais (quarentena hoje)
- [ ] Histórico por animal visível
- [ ] Validações passando

### Ponto de Corte
- [ ] Simulador interativo funcionando
- [ ] Cálculos validados com dados reais
- [ ] Preço market integrado
- [ ] Relatório imprimível

### Conversão Alimentar
- [ ] CA calculado corretamente
- [ ] Histórico por animal visível
- [ ] Dashboard CA funcional
- [ ] Alertas CA > 8 em RED

---

## 🚀 Após Implementação

**Impacto esperado:**
- ✅ Qualidade de leite: -20% em mastite (controle medicações)
- ✅ Financeiro: +R$2-5k/mês (ponto de corte preciso)
- ✅ Eficiência: Identificar animais ineficientes (CA)
- ✅ Competitividade: Equiparável a Gisleite + melhor que Leigado
