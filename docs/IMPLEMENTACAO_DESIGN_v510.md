# Implementação de Design v5.10+ — Padrões e Componentes

**Baseado em:** Análise de design de 15+ softwares de controle de gado (iRancho, VSM AGRO, Leigado, BoviTrack, etc)

---

## 1. PALETA DE CORES PADRÃO

```css
/* Já implementada em templates/base.html */
:root {
  --cor-verde-escuro: #1B5E20;   /* Primary: OK, success, principal */
  --cor-verde-medio: #388E3C;    /* Secondary: hover, active */
  --cor-verde-claro: #C8E6C9;    /* Background, suave */
  
  --cor-amarelo: #FFF9C4;        /* Aviso, atenção */
  --cor-laranja: #FFE0B2;        /* Atenção moderada */
  
  --cor-vermelho: #FFCDD2;       /* Erro, crítico (background) */
  --cor-vermelho-escuro: #BF360C; /* Texto crítico */
  
  --cor-azul-escuro: #1A237E;    /* Informação, neutro */
  --cor-azul-claro: #E3F2FD;     /* Background neutro */
}
```

✅ **Já temos implementado em `config.py`** — usar `CORES` dict.

---

## 2. COMPONENTES PRINCIPAIS

### 2.1 KPI Card (Métrica Principal)

**HTML/Jinja2 padrão:**
```html
<!-- Card de KPI: Número grande + rótulo + trend -->
<div class="card metric">
  <div class="metric-value">{{ value }}</div>
  <div class="metric-label">{{ label }}</div>
  <div class="metric-trend" style="color: {% if trend > 0 %}#1B5E20{% elif trend < 0 %}#BF360C{% else %}#666{% endif %}">
    {% if trend > 0 %}↑ +{{ trend }}%{% elif trend < 0 %}↓ {{ trend }}%{% else %}— 0%{% endif %}
  </div>
</div>
```

**CSS (adicionar em base.html <style>):**
```css
.card.metric {
  text-align: center;
  padding: 1.5rem;
  background: white;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  min-width: 120px;
}

.metric-value {
  font-size: 2.5rem;  /* Número grande */
  font-weight: bold;
  color: #1B5E20;
  line-height: 1.2;
}

.metric-label {
  font-size: 0.875rem;  /* Rótulo pequeno */
  color: #666;
  margin-top: 0.5rem;
  font-weight: 500;
}

.metric-trend {
  font-size: 0.75rem;
  margin-top: 0.5rem;
  font-weight: 600;
}
```

**Uso no template:**
```html
<div class="metrics">
  <div class="card metric">
    <div class="metric-value">{{ r.estoque }}</div>
    <div class="metric-label">Cabeças Ativas</div>
    <div class="metric-trend" style="color: #1B5E20;">↑ +2.5%</div>
  </div>
  
  <div class="card metric">
    <div class="metric-value">{{ r.ctcab|fmt_brl }}</div>
    <div class="metric-label">CTCab</div>
    <div class="metric-trend" style="color: #BF360C;">↓ -3%</div>
  </div>
</div>
```

---

### 2.2 Badge/Status (com cor + palavra)

**HTML:**
```html
<!-- ✅ Correto: cor + palavra -->
<span class="badge badge-ok">✓ Ativo</span>
<span class="badge badge-aviso">⚠ Atenção</span>
<span class="badge badge-ruim">✗ Crítico</span>

<!-- ❌ Errado: só cor -->
<span class="badge" style="background: green;"></span>
```

**CSS (já em base.html):**
```css
.badge {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
  font-size: 0.875rem;
  font-weight: 600;
}

.badge-ok {
  background-color: #C8E6C9;
  color: #1B5E20;
}

.badge-aviso {
  background-color: #FFF9C4;
  color: #F57F17;
}

.badge-ruim {
  background-color: #FFCDD2;
  color: #BF360C;
}
```

**Uso:**
```html
<td>{{ animal.status }} <span class="badge badge-ok">✓ Ativo</span></td>
<td>GMD: {{ lote.gmd }} 
    {% if lote.gmd < 0.5 %}
      <span class="badge badge-ruim">✗ Baixo</span>
    {% elif lote.gmd < 0.8 %}
      <span class="badge badge-aviso">⚠ Moderado</span>
    {% else %}
      <span class="badge badge-ok">✓ OK</span>
    {% endif %}
</td>
```

---

### 2.3 Semáforo (Status Indicador)

**HTML:**
```html
<!-- ✅ Correto: cor + palavra -->
<div class="semaforo">
  <div class="semaforo-indicador" style="background-color: #1B5E20;"></div>
  <span class="semaforo-label">Saúde: OK</span>
</div>
```

**CSS:**
```css
.semaforo {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem;
  border-radius: 6px;
  background-color: #f5f5f5;
}

.semaforo-indicador {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  flex-shrink: 0;
}

.semaforo-label {
  font-size: 0.875rem;
  font-weight: 600;
  color: #333;
}
```

---

### 2.4 Barra de Progresso (com cor semáforo)

**HTML:**
```html
<!-- GMD vs meta -->
<div class="barra-progress">
  <div class="barra-label">GMD: 0.9 kg/dia (meta: 1.2)</div>
  <div class="barra-container">
    <div class="barra-fill" style="width: 75%; background-color: #FFF9C4;"></div>
  </div>
  <div class="barra-hint">75% da meta</div>
</div>
```

**CSS:**
```css
.barra-progress {
  margin: 1rem 0;
}

.barra-label {
  font-size: 0.875rem;
  font-weight: 600;
  color: #333;
  margin-bottom: 0.5rem;
}

.barra-container {
  height: 12px;
  background-color: #e0e0e0;
  border-radius: 6px;
  overflow: hidden;
}

.barra-fill {
  height: 100%;
  transition: width 0.3s ease;
  /* Usar cor conforme range:
     - 0-50%: #BF360C (vermelho)
     - 50-80%: #FFF9C4 (amarelo)
     - 80%+: #1B5E20 (verde)
  */
}

.barra-hint {
  font-size: 0.75rem;
  color: #999;
  margin-top: 0.25rem;
}
```

---

### 2.5 Tabela Responsiva (adapta para mobile)

**HTML:**
```html
<!-- Desktop: tabela normal -->
<!-- Mobile: converte para cards-linha -->
<table class="table-responsiva">
  <thead>
    <tr>
      <th>Animal</th>
      <th>Peso (kg)</th>
      <th>GMD</th>
      <th>Status</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td data-label="Animal">A0001</td>
      <td data-label="Peso">350</td>
      <td data-label="GMD">1.2</td>
      <td data-label="Status"><span class="badge badge-ok">✓ Ativo</span></td>
    </tr>
  </tbody>
</table>
```

**CSS:**
```css
.table-responsiva {
  width: 100%;
  border-collapse: collapse;
  background-color: white;
}

.table-responsiva thead {
  background-color: #f5f5f5;
  border-bottom: 2px solid #1B5E20;
}

.table-responsiva th {
  padding: 0.75rem;
  text-align: left;
  font-weight: 600;
  color: #333;
  font-size: 0.875rem;
}

.table-responsiva td {
  padding: 0.75rem;
  border-bottom: 1px solid #e0e0e0;
}

/* Mobile: converter para cards-linha */
@media (max-width: 768px) {
  .table-responsiva {
    display: block;
  }
  
  .table-responsiva thead {
    display: none;
  }
  
  .table-responsiva tbody {
    display: block;
  }
  
  .table-responsiva tr {
    display: block;
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    padding: 1rem;
    margin-bottom: 1rem;
    background-color: white;
  }
  
  .table-responsiva td {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.5rem 0;
    border: none;
  }
  
  .table-responsiva td::before {
    content: attr(data-label);
    font-weight: 600;
    color: #666;
    flex-grow: 1;
  }
}
```

---

### 2.6 Alerta/Aviso Destacado

**HTML:**
```html
<!-- Alertas críticos: linha de Aviso no topo -->
<div class="alertas-container">
  <div class="alerta alerta-critico">
    <span class="alerta-icon">🔴</span>
    <span class="alerta-texto">GMD baixo: Lote L001 (0.8 kg/dia)</span>
  </div>
  
  <div class="alerta alerta-aviso">
    <span class="alerta-icon">⚠️</span>
    <span class="alerta-texto">Vacinação pendente: 12 animais</span>
  </div>
</div>
```

**CSS:**
```css
.alertas-container {
  margin: 1rem 0;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.alerta {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  border-radius: 6px;
  font-size: 0.875rem;
  font-weight: 500;
}

.alerta-critico {
  background-color: #FFCDD2;
  color: #BF360C;
  border-left: 4px solid #BF360C;
}

.alerta-aviso {
  background-color: #FFF9C4;
  color: #F57F17;
  border-left: 4px solid #FFF9C4;
}

.alerta-icon {
  font-size: 1.25rem;
  flex-shrink: 0;
}

.alerta-texto {
  flex-grow: 1;
}
```

---

### 2.7 Gráfico de Colunas (Comparação)

**HTML + Chart.js:**
```html
<div style="height: 300px;">
  <canvas id="grafico-lotes"></canvas>
</div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js"></script>
<script>
const ctx = document.getElementById('grafico-lotes').getContext('2d');
new Chart(ctx, {
  type: 'bar',
  data: {
    labels: ['L001', 'L002', 'L003', 'L004'],
    datasets: [{
      label: 'GMD (kg/dia)',
      data: [0.9, 1.2, 0.8, 1.1],
      backgroundColor: [
        '#BF360C',  // L001: < 0.9 (vermelho)
        '#1B5E20',  // L002: >= 1.0 (verde)
        '#BF360C',  // L003: < 0.9 (vermelho)
        '#1B5E20',  // L004: >= 1.0 (verde)
      ],
      borderRadius: 6
    }]
  },
  options: {
    indexAxis: 'y',
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false }
    },
    scales: {
      x: {
        beginAtZero: true,
        ticks: { font: { size: 11 } }
      }
    }
  }
});
</script>
```

---

### 2.8 Gráfico de Linhas (Evolução Temporal)

**HTML + Chart.js:**
```html
<div style="height: 300px;">
  <canvas id="grafico-evolucao"></canvas>
</div>

<script>
const ctx = document.getElementById('grafico-evolucao').getContext('2d');
new Chart(ctx, {
  type: 'line',
  data: {
    labels: ['Sem 1', 'Sem 2', 'Sem 3', 'Sem 4', 'Sem 5'],
    datasets: [{
      label: 'Peso Médio (kg)',
      data: [300, 310, 320, 335, 350],
      borderColor: '#1B5E20',
      backgroundColor: 'rgba(27, 94, 32, 0.1)',
      borderWidth: 3,
      fill: true,
      pointBackgroundColor: '#1B5E20',
      pointRadius: 6,
      tension: 0.4
    }]
  },
  options: {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { position: 'top' } },
    scales: { y: { beginAtZero: false } }
  }
});
</script>
```

---

## 3. LAYOUT PADRÃO DE DASHBOARD

**Usar esta estrutura em novo template `dashboard_v510.html`:**

```html
{% extends "base.html" %}

{% block title %}Dashboard — Gado Sítio{% endblock %}

{% block content %}
<div class="dashboard">
  
  <!-- Seção 1: KPIs Principais (3x2) -->
  <section class="seção-kpis">
    <h2>Estado Atual</h2>
    <div class="metrics-grid">
      <div class="card metric">
        <div class="metric-value">{{ r.estoque }}</div>
        <div class="metric-label">Cabeças Ativas</div>
      </div>
      <div class="card metric">
        <div class="metric-value">{{ r.ctcab|fmt_brl }}</div>
        <div class="metric-label">CTCab</div>
      </div>
      <div class="card metric">
        <div class="metric-value">{{ indicadores.gmd_medio }}</div>
        <div class="metric-label">GMD Médio</div>
      </div>
      <div class="card metric">
        <div class="metric-value">{{ r.cmp|fmt_brl }}</div>
        <div class="metric-label">CMP</div>
      </div>
      <div class="card metric">
        <div class="metric-value">{{ r.capital_imobilizado|fmt_brl }}</div>
        <div class="metric-label">Capital</div>
      </div>
      <div class="card metric">
        <div class="metric-value">{{ r.resultado_total|fmt_brl }}</div>
        <div class="metric-label">Resultado</div>
      </div>
    </div>
  </section>

  <!-- Seção 2: Alertas Urgentes -->
  {% if alertas %}
  <section class="seção-alertas">
    <h2>⚠️ Atenção</h2>
    <div class="alertas-container">
      {% for alerta in alertas %}
      <div class="alerta {% if alerta.urgente %}alerta-critico{% else %}alerta-aviso{% endif %}">
        <span class="alerta-icon">{{ '🔴' if alerta.urgente else '⚠️' }}</span>
        <span class="alerta-texto">{{ alerta.texto }}</span>
      </div>
      {% endfor %}
    </div>
  </section>
  {% endif %}

  <!-- Seção 3: Gráficos -->
  <section class="seção-graficos">
    <h2>Análise</h2>
    <div class="graficos-grid">
      <div class="grafico-container">
        <h3>Evolução de Peso</h3>
        <canvas id="grafico-peso"></canvas>
      </div>
      <div class="grafico-container">
        <h3>GMD por Lote</h3>
        <canvas id="grafico-gmd"></canvas>
      </div>
    </div>
  </section>

  <!-- Seção 4: Tabelas Detalhadas -->
  <section class="seção-tabelas">
    <h2>Lotes Ativos</h2>
    <table class="table-responsiva">
      <thead>
        <tr>
          <th>Lote</th>
          <th>Cabeças</th>
          <th>Peso Médio</th>
          <th>GMD</th>
          <th>Dias</th>
          <th>Status</th>
        </tr>
      </thead>
      <tbody>
        {% for lote in lotes_ativos %}
        <tr>
          <td data-label="Lote">{{ lote.lote_id }}</td>
          <td data-label="Cabeças">{{ lote.quantidade }}</td>
          <td data-label="Peso">{{ lote.peso_medio }} kg</td>
          <td data-label="GMD">
            {{ lote.gmd }}
            {% if lote.gmd < 0.5 %}
              <span class="badge badge-ruim">✗ Crítico</span>
            {% elif lote.gmd < 0.8 %}
              <span class="badge badge-aviso">⚠ Baixo</span>
            {% else %}
              <span class="badge badge-ok">✓ OK</span>
            {% endif %}
          </td>
          <td data-label="Dias">{{ lote.dias_confinado }}</td>
          <td data-label="Status"><span class="badge badge-ok">✓ Ativo</span></td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </section>

</div>

<style>
.dashboard { padding: 2rem; }

.seção-kpis,
.seção-alertas,
.seção-graficos,
.seção-tabelas {
  margin-bottom: 2rem;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 1rem;
}

.graficos-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: 1.5rem;
}

.grafico-container {
  background: white;
  padding: 1.5rem;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

@media (max-width: 768px) {
  .metrics-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .graficos-grid {
    grid-template-columns: 1fr;
  }
}
</style>
{% endblock %}
```

---

## 4. CSS GLOBAL (adicionar em templates/base.html)

```css
/* Variáveis de cores (já existem em config.py) */
:root {
  --cor-verde-escuro: #1B5E20;
  --cor-verde-medio: #388E3C;
  --cor-verde-claro: #C8E6C9;
  --cor-amarelo: #FFF9C4;
  --cor-laranja: #FFE0B2;
  --cor-vermelho: #FFCDD2;
  --cor-vermelho-escuro: #BF360C;
  --cor-azul-escuro: #1A237E;
  --cor-azul-claro: #E3F2FD;
}

/* Tipografia */
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  color: #333;
  line-height: 1.6;
}

h1 { font-size: 2rem; font-weight: 700; margin: 1.5rem 0 1rem; }
h2 { font-size: 1.5rem; font-weight: 600; margin: 1.25rem 0 0.75rem; }
h3 { font-size: 1.125rem; font-weight: 600; margin: 1rem 0 0.5rem; }

/* Cards */
.card {
  background-color: white;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 1rem;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
}

.card:hover {
  box-shadow: 0 4px 12px rgba(0,0,0,0.12);
  transition: box-shadow 0.2s ease;
}

/* Mobile responsividade */
@media (max-width: 768px) {
  h1 { font-size: 1.5rem; }
  h2 { font-size: 1.25rem; }
}
```

---

## 5. PRÓXIMAS ETAPAS DE IMPLEMENTAÇÃO

1. ✅ **Análise concluída** — Design de 15+ softwares estudado
2. 🔜 **v5.10 Release** — Aplicar componentes de KPI card, badges, alertas
3. 🔜 **v5.11** — Reorganizar dashboard completo com novo layout
4. 🔜 **v5.12** — Integrar gráficos avançados (Chart.js)
5. 🔜 **v5.13** — Mapa interativo (Leaflet) para pastos e lotes
6. 🔜 **v5.14** — Relatórios em PDF com design profissional

---

## CHECKLIST DE IMPLEMENTAÇÃO

- [ ] Adicionar CSS de cards, badges, semáforos em base.html
- [ ] Criar template dashboard_v510.html com novo layout
- [ ] Adaptar todos os templates para usar novos componentes
- [ ] Testar responsividade em mobile (768px, 480px)
- [ ] Integrar Chart.js em financeiro.html e resultado.html
- [ ] Implementar alertas com cores corretas (sempre com palavra)
- [ ] Validar acessibilidade (daltonismo, contraste, semântica)

---

**Documento criado:** 2026-10-28  
**Atualizar conforme:** novos componentes forem implementados
