# Features v5.6.0 — Como Acessar

**Status:** Todas as 8 features implementadas e funcionando ✅

---

## 📋 Resumo Rápido

| Feature | Como Acessar | Status |
|---------|--------------|--------|
| 🔍 **Busca Rápida** | Campo no header (🔍) | ✅ Funcionando |
| ⛅ **Previsão do Tempo** | Menu `/tempo` ou card no painel | ✅ Funcionando |
| 📊 **Dashboard Cards** | Home `/` | ✅ Funcionando |
| 🗓️ **Calendário Visual** | Menu `/calendario` | ✅ Funcionando |
| 📈 **Gráficos GMD** | Ficha animal > "Crescimento" | ✅ Funcionando |
| 🔔 **Notificações Push** | Banner "Permitir notificações" | ✅ Funcionando |
| 🐄 **Ficha Mobile** | Acesso em celular `/animais/A0001` | ✅ Funcionando |
| 📊 **Comparativo Vacas** | Menu Leite > "Comparativo" | ✅ Funcionando |

---

## 🔍 Busca Rápida (Campo no Header)

### Onde está?
- **Topo da página**, lado direito do header
- Ícone de lupa (🔍) + campo de texto

### Como usar?
1. Clique no campo
2. Digite o termo (mínimo 2 caracteres)
3. Resultados aparecem em dropdown
4. Clique no resultado para ir direto

### O que busca?
- **Animais:** brinco (ex: "Amarelo 08"), ID (ex: "A0001")
- **Tarefas:** título da tarefa
- **Manejo:** registros (pesagem, cobertura, etc)

### Exemplo:
```
Digite: "Amarelo"
Resultados:
  🐄 Amarelo 08 #A0001 → /animais/A0001
  🐄 Amarelo 15 #A0003 → /animais/A0003
```

**Cache:** Busca recente fica em `sessionStorage` (rápido)

---

## ⛅ Previsão do Tempo

### Onde está?
- **Opção 1:** Card no dashboard (home `/`)
- **Opção 2:** Menu → Tempo → `/tempo`
- **Opção 3:** URL direto: `http://localhost:5000/tempo`

### O que mostra?
- 🌡️ Temperatura atual, umidade, vento
- 📊 Gráfico 7 dias (temperatura vs precipitação)
- ⚠️ Alertas agrometeorológicos (chuva, calor, vento, queda temp)
- 💡 Recomendações por tipo (Leite, Corte, Volumosos)

### Fonte de dados?
- **API:** Open-Meteo (gratuita, sem chave necessária)
- **Cache:** 3 horas (salvo em `tempo_cache.json`)
- **Localização:** Automática via `sitio_config.json` (lat/lon)

### Exemplo de alerta:
```
🔴 URGENTE: Chuva forte prevista (>20mm)
   Leite: Risco de mastite — verificar higiene da ordenha
   Corte: Armazenar bem camas/alimentos — evitar mofo
   Volumosos: Proteger pilhas de feno/silagem
```

---

## 📊 Dashboard Cards Clicáveis (Home `/`)

### Novidade
- Cards agora são **clicáveis**
- Cada card leva a uma página específica
- Badges de alertas no canto (ex: "3 urgentes")

### Cards disponíveis:
1. **🥛 Leite** → `/leite` (resumo diário)
2. **🐄 Corte** → `/` (rebanho)
3. **🌾 Insumos** → `/insumos` (estoque)
4. **📋 Tarefas** → `/tarefas` (agenda)
5. **👶 Reprodução** → `/reproducao` (coberturas, partos)
6. **⛅ Tempo** → `/tempo` (previsão)

---

## 🗓️ Calendário Visual

### Onde está?
- **URL:** `http://localhost:5000/calendario`
- **Parâmetros:** `?mes=11&ano=2026` (opcional)

### O que mostra?
- Grid 7x5 com todos os dias do mês
- Cores por urgência:
  - 🔴 **Urgente** (≤3 dias)
  - 🟡 **Aviso** (≤7 dias)
  - 🟢 **Normal** (>7 dias)

### Eventos incluídos:
- 👶 **Partos previstos** (via reprodução.situacao)
- 💉 **Vacinações** (via saude.py)
- 🛏️ **Colchão urgente** (próxima troca)
- 📋 **Tarefas pendentes**

### Interação:
- Clique no dia para ver **detalhes modais**
- Navegue mês anterior/próximo com setas

---

## 📈 Gráficos de Crescimento (GMD)

### Onde está?
- Abra ficha de um animal: `/animais/A0001`
- Botão "📈 Crescimento" ou clique direto: `/animais/crescimento?id=A0001`

### O que mostra?
- Gráfico peso vs tempo (Chart.js)
- **Tabela de GMD por período** (g/dia entre pesagens)
- **Tendência:** acelerando 🟢 / normal 🟡 / desacelerando 🔴

### Cálculos:
- **GMD:** (peso final - peso inicial) / dias * 1000 (g/dia)
- **Tendência:** compara 1ª metade vs 2ª metade do histórico

### Exemplo:
```
Pesagem 1: 01/01 - 100 kg
Pesagem 2: 11/01 - 110 kg
GMD: (110-100)/10 = 1000 g/dia
Status: ✅ Bom (ganho normal)
```

---

## 🔔 Notificações Push (PWA)

### Como ativar?
1. Abra a página
2. Veja **banner cinza no topo:** "Ativar notificações"
3. Clique em **"Permitir"**
4. Autorize no navegador

### O que notifica?
- 🔴 **Urgentes apenas:**
  - CCS > 400k (mastite)
  - Colchão < 7 dias
  - Outros alertas críticos

### Onde vê?
- **Desktop:** Notificação no canto inferior
- **Mobile:** Notificação native do SO
- Clique para abrir ficha relacionada

---

## 🐄 Ficha Mobile Condensada

### Quando aparece?
- Automático em **celular** (≤768px)
- Ou acesse: `/animais/A0001?modo=mobile`

### Layout:
- Essencial no topo (1 tela):
  - Brinco + ID
  - Peso atual, GMD
  - Status (vivo, estoque)
- **Abas** para mais:
  - Últimas Ações
  - Histórico
  - Fotos

### Botões de ação:
- [⚖️ Pesar]
- [🩺 Examinar]
- [🛒 Vender]

---

## 📊 Comparativo de Vacas

### Onde está?
- **Menu:** Leite > Comparativo
- **URL:** POST `/leite/comparativo`

### Como usar?
1. Selecione até 3 vacas (dropdown com autocomplete)
2. Clique "Comparar"
3. Veja tabela lado-a-lado

### O que compara?
- **Produção:** L/dia (últimos 30 dias)
- **Custo:** R$/dia
- **Receita:** R$/dia
- **Margem:** R$/dia (destaque em cores)
- **Status:** CCS/CPP (semáforo)

### Decisão:
- Margem < R$0: **Deficitária** 🔴 (verificar saúde)
- Margem < R$10: **Baixa** 🟡 (acompanhar)
- Produção < 5L: **Verificar cobertura** 📌

### Exemplo:
```
┌─────────────────────────────────────────────┐
│         Comparativo de Produção             │
├─ Vaca ──────┼─ Produção ┼─ Margem/dia ──┤
│ Amarelo 08  │   18 L    │   +R$ 29 ✅   │
│ Azul 15     │   15 L    │   +R$ 21 ✅   │
│ Verde 23    │    8 L    │    +R$ 2 🟡   │
└─────────────────────────────────────────────┘
```

---

## 🧪 Testando Localmente

```bash
# 1. Inicie a app
python app.py

# 2. Acesse em http://localhost:5000

# 3. Teste cada feature:
http://localhost:5000/              # Dashboard (home)
http://localhost:5000/tempo         # Previsão do tempo
http://localhost:5000/calendario    # Calendário
http://localhost:5000/animais/A0001 # Ficha animal
http://localhost:5000/leite/comparativo  # Comparativo
```

---

## 🚨 Troubleshooting

### "Não vejo a busca no header"
- ✅ Recarregue a página (F5)
- ✅ Verifique se a classe `.search-box` aparece no HTML (inspecione)

### "Previsão do tempo mostra 'Sem conexão'"
- ✅ Verifique internet (Open-Meteo API precisa conexão)
- ✅ Verifique `sitio_config.json` tem `latitude` e `longitude`
- ✅ Cache: aguarde 3 horas ou delete `tempo_cache.json`

### "Notificação não aparece"
- ✅ Verifique permissão do navegador (permitiu?)
- ✅ Testes não enviam notificações (conftest.py autouse)
- ✅ Sem HTTPS: algumas browsers bloqueiam PWA

### "Comparativo mostra tabela vazia"
- ✅ Precisa ter **registros de Leite Produção** para as vacas
- ✅ Selecione apenas vacas com histórico

---

## 📝 Notas Técnicas

### URLs API
```
GET /api/busca?q=termo&tipo=animal
GET /api/leite/comparativo?ids=A0001,A0002
GET /api/notificacoes                        (retorna alertas urgentes)
GET /api/animais/crescimento?id=A0001        (JSON com GMD)
```

### Modules
- `busca.py` - Função `buscar_global(termo, tipo)`
- `tempo.py` - `previsao()`, `alertas_tempo()`
- `calendario.py` - `eventos_mes(mes, ano)`
- `pesagem.py` - `gmd_por_periodo()`, `tendencia_gmd()`
- `comparativo.py` - `comparar_vacas(ids)`
- `notificacoes.py` - `alertas_como_notificacoes()`

---

**Última atualização:** 2026-10-27 (v5.6.0)  
**Próximo:** v5.7 (mobile refinements + dark mode)

