# 📚 Documentação Completa do Sistema — Gado v5.25.0

## 🏗️ Arquitetura Geral

```
Sítio Santo Antonio (Gestão de Gado)
├── Backend (Flask)
│   ├── app.py                    # Entry point
│   ├── extensions.py             # Flask config, cache, helpers
│   ├── config.py                 # Constantes, colunas, membros
│   └── routes_*.py               # ~20 módulos de rotas
├── Frontend
│   ├── templates/                # Jinja2 HTML
│   ├── static/
│   │   ├── css/                  # Design tokens + componentes
│   │   ├── js/                   # Gestures, Dark mode, Components
│   │   └── sw.js                 # Service Worker (offline)
├── Data Layer
│   ├── db.py                     # Excel I/O, migração
│   ├── gado_familia.xlsx         # 11 abas de dados
│   └── ~/gado-dados/             # Produção (fora do Git)
└── Core Modules
    ├── calculos.py               # Média móvel, resultado financeiro
    ├── animais.py                # Cadastro, brincos, cores
    ├── pesagem.py                # Peso, GMD, histórico
    ├── pastos.py                 # Mapa, situação, lotação
    ├── reproducao.py             # Cobertura, parto, diagnóstico
    ├── leite.py                  # Lactação, CCS, CPP, ração
    ├── peso_foto.py              # Estimativa por Schaeffer
    ├── bcs.py                    # Body Condition Score × Peso
    └── ... (20+ módulos)
```

## 📦 Módulos Principais (v5.8.0)

### 1. **calculos.py** — Motor Financeiro
- `_simular_media_movel()`: Algoritmo de média móvel perpétua (base do resultado)
- `calcular_todos_membros()`: Resultado por membro (estoque, custo, receita)
- Invariantes: `custo_vendidos + perdas + capital == total_custo`

### 2. **animais.py** — Cadastro & Identificação
- Brinco por cor/número (ex: "Amarelo 21" = #A0021)
- Cores configuráveis por sítio
- Status: Vivo/Vendido/Morto/Perdido

### 3. **pesagem.py** — Peso & Crescimento
- `todas()`: Histórico de peso
- `peso_medio()`: Média móvel de peso vivo
- GMD (Ganho Médio Diário) por animal

### 4. **pastos.py** — Mapa & Lotação (v5.2)
- **NOVO (v5.8.0):** `animais_por_pasto()` — rastreia qual animal está em qual pasto
- GeoJSON contornos, cálculo de área (Leaflet)
- Lotação UA/ha vs capacidade (semáforo)

### 5. **reproducao.py** — Cobertura & Parto (v5.3)
- Cobertura (monta/IA) + Diagnóstico (Prenha/Vazia)
- Cálculo de parto (285 dias), toque (35 dias), secagem (60 dias)
- **NOVO (v5.8.0):** `planejamento_ia()` — candidatas a IA com priorização

### 6. **leite.py** — Módulo Leiteiro (v5.4)
- 7 abas: Produção, Config, Alimentação, Necessidades, Tratamentos, Conforto, Colchão
- CCS/CPP com alertas (mastite, higiene)
- Calculador de ração (Embrapa)

### 7. **peso_foto.py** — Pesagem por Câmera (v5.1)
- Schaeffer: `peso = perímetro² × comprimento / 10838`
- Calibração com balança (fator 0.7–1.3)
- **NOVO (v5.8.0):** `historico_estimativas()`, `comparar_estimativa_vs_balanca()`

### 8. **bcs.py** — Body Condition Score (v5.8.0)
- Score visual 1-5 correlacionado com peso
- Detecta subnutrição, risco reprodutivo
- Análise de tendência com avisos

---

## 🔄 Fluxos Principais

### Compra de Gado
```
POST /compras/nova
  → salvar_linha("Compras", ...)
  → média móvel recalcula custo
  → painel atualiza (cache invalidado)
```

### Venda de Gado
```
POST /vendas/nova
  → salvar_linha("Vendas", ...)
  → média móvel: receita = cabeças × custo_médio
  → resultado por membro calculado
  → CMP/GPCab atualizados
```

### Movimentação de Pasto
```
POST /pastos/mover
  → salvar_linha("Manejo", Movimentação de Pasto)
  → /api/pastos/animais retorna novo estado
  → Mapa Leaflet atualiza (JS)
```

### Pesagem + Estimativa
```
GET  /animais/<id>/peso-foto    [form]
POST → peso_foto.registrar() → grava "Peso Estimado" no Manejo
GET  /animais/<id>/historico-peso → historico_estimativas() → gráfico
```

---

## 🗄️ Estrutura do Excel (gado_familia.xlsx)

| Aba | Colunas | Uso |
|-----|---------|-----|
| **Compras** | Data, Animal, Kg, Valor, Membro | Entrada de gado + gastos |
| **Vendas** | Data, Animal, Kg, Valor, Membro, Custo Médio | Saída + resultado |
| **Gastos** | Data, Tipo, Valor, Produto, Membro | Despesas (ração, vac, etc) |
| **Manejo** | Data, Tipo, Brincos, Descrição, Produto, Pasto | Cobertura, parto, movimento |
| **Animais** | ID, Nome, Cor, Status, Mãe, Uso | Cadastro individual |
| **Fotos** | ID Animal, URL Drive, Data | Galeria (Drive) |
| **Pastos** | ID, Nome, Área, Contorno GeoJSON, Cor | Mapa |
| **Leite** | Data, Animal, Litros, CCS, CPP | Produção láctea |
| **Configuração** | Chave, Valor | Peso médio, capacidade UA/ha |
| **Tarefas** | Data, Descrição, Feito, Repetir | Agenda |
| **Colchão** | ID Pasto, Material, Última Troca, Próxima | Cama (alertas) |

---

## 🔐 Segurança & Dados

- **Senhas:** Hash SHA256 em `config.py` (padrão: `sitio2025`)
- **CSRF:** Token em POST (Flask-SeaSurf)
- **Backup:** Automático diário em `~/gado-dados/backups/`
- **Vários sítios:** `sitios.json` com acesso por membro
- **Cache:** Invalidado ao salvar (versão de arquivo)

---

## 📱 Mobile & PWA

- **Service Worker v2** (`static/sw.js`): cache-first (assets), network-first (API), SWR (HTML)
- **Offline:** IndexedDB (visitas, fotos) + sync quando online
- **Design:** Mobile-first, 3 breakpoints (480px, 768px, 1024px+)
- **Dark Mode:** CSS variables, localStorage
- **Gestures:** Swipe, long-press, scroll

---

## 🎯 Features por Sprint

| Sprint | Features | Testes |
|--------|----------|--------|
| **1** | Mobile UI, Dark mode, Gestures | 26 |
| **2** | Design tokens, Skeleton, Lazy images, SW | - |
| **3** | Bottom nav, Badges | 26 |
| **4.1** | Modal (dialogs, confirm/alert) | 40 |
| **4.2** | Toast (notificações, fila) | 36 |
| **4.3** | Accordion, Form Validator | 102 |
| **4.4** | Integration & Polish | 32 |
| **5.8** | Animais no mapa, BCS, Planejamento IA | - |

---

## 🚀 Como Rodar

```bash
# Dev local
python app.py                    # http://localhost:5000

# Testes
python -m pytest tests/ -v       # ~5s

# Produção (PythonAnywhere)
cd ~/gado && git pull origin main
# Reload na web → `/var/www/deyvidgt_pythonanywhere_com_wsgi.py`
```

---

## 📖 Próximas Prioridades

1. ✅ Central de Alertas com atalhos para abas
2. ✅ Gráfico gordura×peso (BCS)
3. ⏳ Dashboard de reprodução (calendário de partos)
4. ⏳ Relatório PDF por período
5. ⏳ Integração com WhatsApp (alertas automáticos)

---

**Versão:** 5.8.0  
**Atualizado:** 2026-10-27  
**Arquitetura:** Flask + Excel + PWA  
**Deploy:** PythonAnywhere (WSGI)
