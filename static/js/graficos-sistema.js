/**
 * graficos-sistema.js — Biblioteca de gráficos Chart.js
 * Copiada dos exemplos visuais (CATALOGO.md, imagens 1-62)
 * Adaptada para dados reais do sistema de gado
 */

// ── Paletas de cores dos exemplos
const PALETAS = {
  verde_natureza: {
    primary: '#8ba753',    // verde oliva (imagem 2)
    secondary: '#a6b560',  // verde limão
    tertiary: '#708731',   // verde escuro
    light: '#c6edb4',      // verde suave
  },
  azul_corporativo: {
    primary: '#19316f',    // azul royal (imagens 52-55)
    secondary: '#0c1c2b',  // azul marinha
    light: '#9dc6e4',      // azul claro
    accent: '#428dd1',     // azul brilho
  },
  verde_acao: {
    primary: '#72b148',    // verde lima (imagens 57-62)
    secondary: '#71b546',
    light: '#c6edb4',
    accent: '#6ddf65',     // verde neon
  },
  neutro_claro: {
    bg: '#ffffff',
    text: '#131313',
    light: '#f1f9fb',
    accent: '#124c4d',
  },
};

const CORES_TEMA = {
  claro: {
    bg: '#ffffff',
    text: '#3d3d3d',
    grid: '#eaeaea',
    accent: PALETAS.verde_natureza.primary,
  },
  escuro: {
    bg: '#0c1c2b',
    text: '#e3e3e3',
    grid: '#0b1222',
    accent: PALETAS.azul_corporativo.primary,
  },
};

/**
 * Gráfico de Barras Horizontais (Comparativo)
 * Uso: Gastos por tipo, resultado por membro, etc
 * Referência: Imagens 2, 10
 */
function grafico_barras_horizontal(ctx, labels, data, opcoes = {}) {
  const tema = opcoes.tema || 'claro';
  const cores_tema = CORES_TEMA[tema];

  return new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [{
        label: opcoes.label || 'Valor',
        data: data,
        backgroundColor: opcoes.colors || PALETAS.verde_natureza.primary,
        borderRadius: 4,
        borderSkipped: false,
      }],
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: true,
      plugins: {
        legend: { display: false },
        title: { display: false },
      },
      scales: {
        x: {
          beginAtZero: true,
          grid: { color: cores_tema.grid, drawBorder: false },
          ticks: { color: cores_tema.text, font: { size: 12 } },
        },
        y: {
          grid: { display: false },
          ticks: { color: cores_tema.text, font: { size: 12 } },
        },
      },
    },
  });
}

/**
 * Gráfico de Colunas (Série Temporal)
 * Uso: Resultado mensal, vendas por mês, etc
 * Referência: Imagens 1, 6
 */
function grafico_colunas(ctx, labels, dataset, opcoes = {}) {
  const tema = opcoes.tema || 'claro';
  const cores_tema = CORES_TEMA[tema];
  const cores = opcoes.colors || [PALETAS.verde_natureza.primary];

  return new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: Array.isArray(dataset[0])
        ? dataset.map((d, i) => ({
            label: opcoes.labels?.[i] || `Série ${i+1}`,
            data: d,
            backgroundColor: cores[i] || cores[0],
            borderRadius: 4,
          }))
        : [{
            label: opcoes.label || 'Valor',
            data: dataset,
            backgroundColor: cores[0],
            borderRadius: 4,
          }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: {
        legend: {
          display: opcoes.legend !== false,
          labels: { color: cores_tema.text, font: { size: 12 } },
        },
        title: { display: false },
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: { color: cores_tema.text, font: { size: 12 } },
        },
        y: {
          beginAtZero: true,
          grid: { color: cores_tema.grid, drawBorder: false },
          ticks: { color: cores_tema.text, font: { size: 12 } },
        },
      },
    },
  });
}

/**
 * Gráfico de Linhas (Trends)
 * Uso: Evolução CMP, GPCab, CCS/CPP, etc
 * Referência: Imagens 6, 7, 8
 */
function grafico_linhas(ctx, labels, datasets, opcoes = {}) {
  const tema = opcoes.tema || 'claro';
  const cores_tema = CORES_TEMA[tema];
  const cores_padrao = [
    PALETAS.verde_natureza.primary,
    PALETAS.azul_corporativo.primary,
    PALETAS.verde_acao.primary,
  ];

  return new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: datasets.map((d, i) => ({
        label: d.label || `Série ${i+1}`,
        data: d.data,
        borderColor: d.color || cores_padrao[i % cores_padrao.length],
        backgroundColor: (d.color || cores_padrao[i % cores_padrao.length]) + '20', // 20% alpha
        borderWidth: 2,
        fill: opcoes.fill !== false,
        tension: 0.4,
        pointRadius: 4,
        pointBackgroundColor: d.color || cores_padrao[i % cores_padrao.length],
        pointBorderColor: cores_tema.bg,
        pointBorderWidth: 2,
      })),
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: {
        legend: {
          display: opcoes.legend !== false,
          labels: { color: cores_tema.text, font: { size: 12 } },
        },
        title: { display: false },
      },
      scales: {
        x: {
          grid: { color: cores_tema.grid, drawBorder: false },
          ticks: { color: cores_tema.text, font: { size: 12 } },
        },
        y: {
          beginAtZero: opcoes.beginAtZero !== false,
          grid: { color: cores_tema.grid, drawBorder: false },
          ticks: { color: cores_tema.text, font: { size: 12 } },
        },
      },
    },
  });
}

/**
 * Gráfico de Área (Distribuição)
 * Uso: Composição de receita, ocupação de pastos, etc
 * Referência: Imagens variadas
 */
function grafico_area_empilhada(ctx, labels, datasets, opcoes = {}) {
  const tema = opcoes.tema || 'claro';
  const cores_tema = CORES_TEMA[tema];
  const cores_padrao = [
    PALETAS.verde_natureza.primary,
    PALETAS.azul_corporativo.accent,
    PALETAS.verde_acao.primary,
    '#e67e22', // laranja
    '#e74c3c', // vermelho
  ];

  return new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: datasets.map((d, i) => ({
        label: d.label || `Categoria ${i+1}`,
        data: d.data,
        borderColor: d.color || cores_padrao[i % cores_padrao.length],
        backgroundColor: d.color || cores_padrao[i % cores_padrao.length],
        fill: true,
        tension: 0.4,
        pointRadius: 0,
      })),
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: {
        filler: { propagate: true },
        legend: {
          display: opcoes.legend !== false,
          labels: { color: cores_tema.text, font: { size: 12 } },
        },
      },
      scales: {
        x: {
          stacked: true,
          grid: { color: cores_tema.grid, drawBorder: false },
          ticks: { color: cores_tema.text, font: { size: 12 } },
        },
        y: {
          stacked: true,
          beginAtZero: true,
          grid: { color: cores_tema.grid, drawBorder: false },
          ticks: { color: cores_tema.text, font: { size: 12 } },
        },
      },
    },
  });
}

/**
 * Gráfico de Gauge (KPI Circular)
 * Uso: Taxa de ocupação, % de meta, CPP/CCS normalizado, etc
 * Referência: Imagens estimadas 1, 4, 5
 */
function grafico_gauge(ctx, valor, maximo = 100, opcoes = {}) {
  const tema = opcoes.tema || 'claro';
  const cores_tema = CORES_TEMA[tema];
  const percentual = (valor / maximo) * 100;

  // Cores por range (verde > amarelo > vermelho)
  let cor;
  if (percentual >= 80) cor = PALETAS.verde_acao.primary;
  else if (percentual >= 60) cor = '#f39c12'; // amarelo
  else cor = '#e74c3c'; // vermelho

  return new Chart(ctx, {
    type: 'doughnut',
    data: {
      datasets: [{
        data: [percentual, 100 - percentual],
        backgroundColor: [cor, cores_tema.grid],
        borderWidth: 0,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      circumference: 180,
      rotation: 270,
      plugins: {
        legend: { display: false },
        tooltip: { enabled: false },
      },
    },
    plugins: [{
      id: 'textCenter',
      beforeDatasetsDraw(c) {
        const { width, height, ctx: c_ctx } = c;
        c_ctx.restore();

        // Número grande no centro
        const fontSize = (height / 200).toFixed(2);
        c_ctx.font = `bold ${fontSize}em sans-serif`;
        c_ctx.textBaseline = 'middle';
        c_ctx.fillStyle = cores_tema.text;

        const text = `${percentual.toFixed(0)}%`;
        const textX = Math.round((width - c_ctx.measureText(text).width) / 2);
        const textY = height / 2;

        c_ctx.fillText(text, textX, textY);
        c_ctx.save();
      },
    }],
  });
}

/**
 * Gráfico de Pizza/Donut (Composição)
 * Uso: Resultado por membro, composição de gasto, etc
 * Referência: Imagens variadas
 */
function grafico_pizza(ctx, labels, data, opcoes = {}) {
  const tema = opcoes.tema || 'claro';
  const cores_tema = CORES_TEMA[tema];
  const cores_padrao = [
    PALETAS.verde_natureza.primary,
    PALETAS.azul_corporativo.primary,
    PALETAS.verde_acao.primary,
    '#e67e22',
    '#95a5a6',
  ];

  return new Chart(ctx, {
    type: opcoes.tipo || 'doughnut',
    data: {
      labels: labels,
      datasets: [{
        data: data,
        backgroundColor: opcoes.colors || cores_padrao.slice(0, labels.length),
        borderColor: cores_tema.bg,
        borderWidth: 2,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: {
        legend: {
          display: opcoes.legend !== false,
          position: 'bottom',
          labels: { color: cores_tema.text, font: { size: 12 } },
        },
        tooltip: {
          callbacks: {
            label: function(c) {
              const total = c.dataset.data.reduce((a, b) => a + b, 0);
              const pct = ((c.parsed / total) * 100).toFixed(1);
              return `${c.label}: ${pct}%`;
            },
          },
        },
      },
    },
  });
}

/**
 * Gráfico Comparativo de 2 Eixos (Resultado vs Cabeças)
 * Uso: Correlação entre métricas
 * Referência: Imagens 6, 7, 8 (estimado)
 */
function grafico_duplo_eixo(ctx, labels, data1, data2, opcoes = {}) {
  const tema = opcoes.tema || 'claro';
  const cores_tema = CORES_TEMA[tema];

  return new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [
        {
          label: opcoes.label1 || 'Série 1',
          data: data1,
          borderColor: PALETAS.verde_natureza.primary,
          yAxisID: 'y',
          tension: 0.4,
          fill: false,
        },
        {
          label: opcoes.label2 || 'Série 2',
          data: data2,
          borderColor: PALETAS.azul_corporativo.primary,
          yAxisID: 'y1',
          tension: 0.4,
          fill: false,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: {
        legend: {
          labels: { color: cores_tema.text, font: { size: 12 } },
        },
      },
      scales: {
        x: {
          grid: { color: cores_tema.grid, drawBorder: false },
          ticks: { color: cores_tema.text, font: { size: 12 } },
        },
        y: {
          type: 'linear',
          display: true,
          position: 'left',
          grid: { color: cores_tema.grid, drawBorder: false },
          ticks: { color: cores_tema.text, font: { size: 12 } },
        },
        y1: {
          type: 'linear',
          display: true,
          position: 'right',
          grid: { drawOnChartArea: false },
          ticks: { color: cores_tema.text, font: { size: 12 } },
        },
      },
    },
  });
}

export {
  PALETAS,
  CORES_TEMA,
  grafico_barras_horizontal,
  grafico_colunas,
  grafico_linhas,
  grafico_area_empilhada,
  grafico_gauge,
  grafico_pizza,
  grafico_duplo_eixo,
};
