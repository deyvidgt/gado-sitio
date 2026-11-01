# Plano Consolidado: Ondas 12-14 + Análise Competitiva

**Data**: 2026-10-31 (handoff + pesquisa)  
**Status**: Planejamento → Execução Onda 12  
**Modo**: Ponytail (menor código, máximo impacto)

---

## 📊 RESUMO EXECUTIVO

| Onda | Nome | Escopo | Prioridade | Duração |
|------|------|--------|-----------|---------|
| **12** | Reprodução Avançada | IATF, sincronização cio, IEP otimizado | 🔴 MUST | 3-4 sem |
| **12.X** | Medicações + Ponto de Corte + CA | 3 funcs críticas | 🟠 SHOULD | 2-3 sem (paralelo) |
| **13** | IoT Sensores | Peso, temperatura, colares | 🟡 NICE | 4-5 sem |
| **14** | Relatórios Avançados | PDF 50+pp, exportação | 🟡 NICE | 3-4 sem |

**Total estimado**: 12-16 semanas (3-4 meses)

---

## 🎯 ONDA 12: REPRODUÇÃO AVANÇADA (3-4 semanas)

### Features a Implementar

#### **12.1 Sincronização de Cio (IATF Protocol)**
- [ ] Protocolo IATF padrão (GnRH + progesterona + PGF2α)
- [ ] Calendário automático: dia 0 → 7 → 8 → 9 (inseminação)
- [ ] Alertas: "fazer GnRH hoje", "aplicar progesterona", "dia inseminação"
- [ ] Registro de cada fase com efetividade

**Arquivo**: `reproducao.py` (expand) → `_protocolo_iatf()`

#### **12.2 Detecção de Cio Automática**
- [ ] Registro manual: "Observação de cio" no Manejo
- [ ] Campos: data/hora, intensidade (1-5), sinais (postura, corrimento, mucosa)
- [ ] Alertas em tempo real: "Cio detectado em Preta 23 #A0042"
- [ ] Histórico: últimos 21 dias (ciclo normal)

**Arquivo**: `reproducao.py` → `_detectar_cio()`

#### **12.3 Agendamento Automático de Coberturas**
- [ ] Sincroniza com protocolo IATF + detecção manual
- [ ] Sugestão automática: "Inseminar Preta 23 em 31/10/2026 às 14:00"
- [ ] Confirmação/edição via app
- [ ] Histórico de coberturas com taxa sucesso

**Arquivo**: `reproducao.py` → `_agendar_cobertura()`

#### **12.4 IEP (Intervalo Entre Partos) Otimizado**
- [ ] Fórmula: dias entre partos consecutivos
- [ ] Meta: 365-400 dias (excelente < 370)
- [ ] Cálculo automático: parto₁ → parto₂
- [ ] Dashboard: IEP por vaca + média da fazenda
- [ ] Alertas: vaca com IEP > 420 = candidata a culling

**Arquivo**: `reproducao.py` → `_iep_otimizado()`

#### **12.5 Sugestões de Descarte (Culling)**
- [ ] Critério: IEP > 420 OU taxa prenhez < 3 tentativas
- [ ] Análise: idade, genética, histórico
- [ ] Sugestão: "Preta 23 candidata descarte: IEP 450, mastite 5x/ano"
- [ ] Dashboard "Reprodução" com lista de culling

**Arquivo**: `reproducao.py` → `_sugestoes_culling()`

#### **12.6 Histórico Reprodutivo Completo**
- [ ] Timeline por vaca: primeira cobertura → diagnóstico → parto → próximo cio
- [ ] Gráfico: evolução IEP últimos 12 meses
- [ ] Taxa prenhez: (n_diagnósticos_prenha / n_coberturas) × 100

**Arquivo**: `routes_reproducao.py` → `/reproducao/vaca/<brinco_id>`

### Dependências & Integrações
- ✅ `reproducao.py` já existe (cobertura, diagnóstico, partos)
- ✅ `leite.py` tem dados de qualidade (usar para correlação)
- ✅ `alertas_whatsapp.py` pronto (estender com avisos IATF)
- ✅ `pesagem.py` tem pesos (usar para BCS - body condition score)

### Estrutura de Dados (Excel)
- **Expand `Manejo`**: novo tipo "Sincronização IATF", "Observação de Cio"
- **Expand `Reprodução`** (se não tiver): `Protocolo`, `Fase IATF`, `Taxa Sucesso`
- **Nova aba (opcional)**: `Eventos IATF` com timeline completa

### UI/UX
- Página: `/reproducao/iatf` — dashboard IATF com calendário
- Página: `/reproducao/cio` — histórico de cios por vaca
- Modal: "Agendar cobertura" com sugestões automáticas
- Card no dashboard: "Fêmeas em cio hoje" + "Inseminações agendadas"

### Esforço
- Backend `reproducao.py`: 20h
- Frontend + templates: 10h
- Testes + validações: 5h
- **Total: 35h (~2 semanas)**

---

## 🩹 MEDICAÇÕES + PONTO DE CORTE + CA (Paralelo com 12)

### **12.X.1 Histórico de Medicações** (20h)
De `docs/2026-10-28-historico-medicacoes-ponto-corte-ca.md`:

**Backend**: `medicacoes.py` (novo)
- Registrar medicação: data, brincos, tipo, princípio ativo, dosagem, via, motivo, quarentena
- Calcular data de liberação automática
- Alertas: animais em quarentena hoje

**Frontend**: 
- GET `/animais/<brinco_id>/medicacoes` — histórico
- POST `/animais/medicacao/registrar` — novo registro
- Dashboard: card "Animais em Quarentena"

### **12.X.2 Ponto de Corte (Simulador)** (25h)
**Backend**: `calculos.py` (novo função)
- `simular_ponto_corte(animal_id, dias=[0, 7, 14, 30])` 
- Compara: receita hoje vs. futuro (com declínio de preço)
- Retorna melhor data para vender

**Frontend**:
- GET `/vendas/simular-corte?animal_id=X` — modal interativo
- Inputs: animal, preço hoje, GMD, dias
- Resultado: tabela comparativa com recomendação

### **12.X.3 Conversão Alimentar (CA)** (20h)
**Backend**: `calculos.py` (expand)
- `calcular_ca(animal_id, data_inicio, data_fim)`
- CA físico: kg ração / kg ganho
- CA financeiro: R$ ração / kg ganho

**Frontend**:
- GET `/nutrição/conversão` — dashboard CA
- GET `/animais/<animal_id>/ca` — histórico
- Alertas: CA > 8 = vermelho

### Prioridade
1. **Medicações**: crítico para leite (quarentena)
2. **Ponto de Corte**: impacto financeiro alto
3. **CA**: otimização

---

## 🔌 ONDA 13: IoT SENSORES (4-5 semanas)

### Features
- [ ] API POST `/api/iot/dados` — receber JSON de sensores
- [ ] Sensores suportados: peso (balança), temperatura/umidade, colares atividade
- [ ] Integração com Manejo: pesagem automática → `Pesagem` aba
- [ ] Alertas: febre (>39.5°C), comportamento anormal
- [ ] Dashboard IoT: status em tempo real

### Módulo
`iot_sensores.py` (novo) com funções:
- `receber_dados_sensor(tipo, animal_id, valor, timestamp)`
- `processar_peso_balanca()` → cria registro em Pesagem
- `detectar_anomalias()` → alertas (febre, inatividade)

### Arquivo Excel
- Nova aba: `IoT Sensores` com histórico de leituras

---

## 📋 ONDA 14: RELATÓRIOS AVANÇADOS (3-4 semanas)

### Relatórios (PDF + Excel + WhatsApp)
1. **Reprodutivo**: IEP, taxa prenhez, culling, IATF
2. **Sanitário**: medicações, carência leite, eventos saúde
3. **Financeiro**: resultado/membro, ponto corte, CA
4. **Leite**: produção, CCS/CPP, mastite, top10
5. **Anual**: todas as ondas consolidadas (50+ páginas)

### Módulo
`relatorios_avancados.py` (novo) com:
- `gerar_relatorio(tipo, periodo, formato)` → PDF/Excel/JSON
- `enviar_relatorio_whatsapp(tipo, membros)` — automático 1º de cada mês

---

## 🎯 GAPS COMPETITIVOS vs PROGRAMA-SITIO

*(Aguardando resultado do agent de pesquisa)*

**Prováveis gaps a cobrir:**
- ✅ IATF protocol → Onda 12
- ✅ Medicações → Onda 12.X
- ✅ Ponto de corte → Onda 12.X
- ✅ IoT sensores → Onda 13
- ✅ Relatórios PDF avançados → Onda 14
- ❓ Marketplace de vendas (integração com plataforma)
- ❓ Integração com banco de dados genéticos (Ulysses, etc)
- ❓ Consultor IA (recomendações automáticas)

---

## 📅 TIMELINE DE EXECUÇÃO

```
Semana 1-2: Onda 12 (Reprodução IATF)
            + Medicações (paralelo)

Semana 3-4: Ponto de Corte
            + Continuação IATF se precisar

Semana 5-6: Conversão Alimentar
            + Testes finais 12.X

Semana 7-11: Onda 13 (IoT)

Semana 12-15: Onda 14 (Relatórios)

**Total: 15 semanas (3,5 meses)**
```

---

## ✅ PRÓXIMOS PASSOS

1. ✅ Análise competitiva (agent em andamento)
2. ⏳ Confirmação de escopo com usuário
3. ⏳ Design specs para Onda 12
4. ⏳ Iniciar implementação Onda 12 (reproducao_avancada.py)

---

**Última atualização**: 2026-10-31 | **Modo**: Ponytail ✅
