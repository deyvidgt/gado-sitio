/**
 * charts-extended.js — Gráficos avançados v5.8
 * Barras comparativas, linhas, sparklines usando Chart.js
 */

class ComparativeChart {
  /**
   * Gráfico de barras comparativas: "Minha Fazenda" vs "Média Mercado"
   * Uso:
   *   new ComparativeChart('chart-id', {
   *     title: 'Ganho @/ha',
   *     labels: ['Jan', 'Fev', 'Mar'],
   *     myData: [12.5, 13.2, 14.1],
   *     marketData: [11.8, 12.5, 13.0],
   *     unit: '@/ha'
   *   });
   */
  constructor(elementId, options = {}) {
    this.element = document.getElementById(elementId);
    if (!this.element) {
      console.error(`Elemento #${elementId} não encontrado`);
      return;
    }

    this.title = options.title || 'Comparativo';
    this.labels = options.labels || [];
    this.myData = options.myData || [];
    this.marketData = options.marketData || [];
    this.unit = options.unit || '';
    this.type = options.type || 'bar'; // 'bar' ou 'line'

    this.isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    this.updateColors();
    this.observeThemeChange();

    this.chart = null;
    this.render();
  }

  updateColors() {
    const root = document.documentElement;
    const style = getComputedStyle(root);

    this.colors = {
      myFarm: style.getPropertyValue('--green-500').trim() || '#52a044',      // Verde claro
      market: style.getPropertyValue('--green-700').trim() || '#2d5a27',      // Verde escuro
      text: this.isDark ? '#e8ede7' : '#1c1c1c',
      textSecondary: this.isDark ? '#6b7d69' : '#888888',
      gridColor: this.isDark ? 'rgba(139,179,127,.1)' : 'rgba(80,120,60,.1)'
    };
  }

  observeThemeChange() {
    const observer = new MutationObserver((mutations) => {
      const theme = document.documentElement.getAttribute('data-theme');
      if (theme !== (this.isDark ? 'dark' : 'light')) {
        this.isDark = theme === 'dark';
        this.updateColors();
        if (this.chart) this.render();
      }
    });

    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['data-theme']
    });
  }

  render() {
    if (this.chart) {
      this.chart.destroy();
    }

    const ctx = this.element.getContext('2d');

    this.chart = new Chart(ctx, {
      type: this.type,
      data: {
        labels: this.labels,
        datasets: [
          {
            label: 'Minha Fazenda',
            data: this.myData,
            backgroundColor: this.colors.myFarm,
            borderColor: this.colors.myFarm,
            borderWidth: 2,
            borderRadius: 6,
            hoverBackgroundColor: this.colors.myFarm,
            tension: 0.3,
            fill: this.type === 'line',
            pointRadius: 5,
            pointHoverRadius: 7,
            pointBackgroundColor: this.colors.myFarm,
            pointBorderColor: '#fff',
            pointBorderWidth: 2
          },
          {
            label: 'Média Mercado',
            data: this.marketData,
            backgroundColor: this.colors.market,
            borderColor: this.colors.market,
            borderWidth: 2,
            borderRadius: 6,
            hoverBackgroundColor: this.colors.market,
            tension: 0.3,
            fill: this.type === 'line',
            pointRadius: 5,
            pointHoverRadius: 7,
            pointBackgroundColor: this.colors.market,
            pointBorderColor: '#fff',
            pointBorderWidth: 2
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          intersect: false,
          mode: 'index'
        },
        plugins: {
          legend: {
            display: true,
            position: 'top',
            labels: {
              color: this.colors.text,
              font: { size: 13, family: 'DM Sans, sans-serif', weight: '500' },
              padding: 15,
              boxWidth: 12,
              boxHeight: 12,
              borderRadius: 4,
              usePointStyle: true
            }
          },
          tooltip: {
            backgroundColor: this.isDark ? '#333' : '#fff',
            titleColor: this.colors.text,
            bodyColor: this.colors.text,
            borderColor: this.colors.gridColor,
            borderWidth: 1,
            padding: 10,
            titleFont: { size: 13, weight: '600' },
            bodyFont: { size: 12 },
            caretPadding: 10,
            displayColors: true,
            callbacks: {
              label: (context) => {
                let label = context.dataset.label || '';
                if (label) label += ': ';
                label += context.parsed.y + ' ' + this.unit;
                return label;
              }
            }
          }
        },
        scales: {
          x: {
            grid: {
              display: false,
              drawBorder: false
            },
            ticks: {
              color: this.colors.textSecondary,
              font: { size: 12, family: 'DM Sans, sans-serif' }
            }
          },
          y: {
            beginAtZero: true,
            grid: {
              color: this.colors.gridColor,
              drawBorder: false,
              lineWidth: 1
            },
            ticks: {
              color: this.colors.textSecondary,
              font: { size: 12, family: 'DM Sans, sans-serif' },
              callback: (value) => value + ' ' + this.unit
            }
          }
        }
      }
    });
  }

  updateData(myData, marketData) {
    this.myData = myData;
    this.marketData = marketData;
    if (this.chart) this.render();
  }
}

class StackedBarChart {
  /**
   * Gráfico de barras empilhadas: Custo, Receita, Lucro
   * Uso:
   *   new StackedBarChart('chart-id', {
   *     title: 'Destaque do Lote',
   *     labels: ['Lote A', 'Lote B', 'Lote C'],
   *     receita: [15000, 18000, 12000],
   *     custo: [8500, 9200, 7000],
   *     lucro: [6500, 8800, 5000]
   *   });
   */
  constructor(elementId, options = {}) {
    this.element = document.getElementById(elementId);
    if (!this.element) {
      console.error(`Elemento #${elementId} não encontrado`);
      return;
    }

    this.title = options.title || 'Comparativo';
    this.labels = options.labels || [];
    this.receita = options.receita || [];
    this.custo = options.custo || [];
    this.lucro = options.lucro || [];

    this.isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    this.updateColors();
    this.observeThemeChange();

    this.chart = null;
    this.render();
  }

  updateColors() {
    const root = document.documentElement;
    const style = getComputedStyle(root);

    this.colors = {
      receita: style.getPropertyValue('--green-500').trim() || '#52a044',
      custo: style.getPropertyValue('--warn').trim() || '#e67e22',
      lucro: style.getPropertyValue('--info').trim() || '#2980b9',
      text: this.isDark ? '#e8ede7' : '#1c1c1c',
      textSecondary: this.isDark ? '#6b7d69' : '#888888',
      gridColor: this.isDark ? 'rgba(139,179,127,.1)' : 'rgba(80,120,60,.1)'
    };
  }

  observeThemeChange() {
    const observer = new MutationObserver((mutations) => {
      const theme = document.documentElement.getAttribute('data-theme');
      if (theme !== (this.isDark ? 'dark' : 'light')) {
        this.isDark = theme === 'dark';
        this.updateColors();
        if (this.chart) this.render();
      }
    });

    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['data-theme']
    });
  }

  render() {
    if (this.chart) {
      this.chart.destroy();
    }

    const ctx = this.element.getContext('2d');

    this.chart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: this.labels,
        datasets: [
          {
            label: 'Receita',
            data: this.receita,
            backgroundColor: this.colors.receita,
            borderRadius: [6, 6, 0, 0],
            hoverBackgroundColor: '#3d9c2f'
          },
          {
            label: 'Custo',
            data: this.custo,
            backgroundColor: this.colors.custo,
            hoverBackgroundColor: '#d96a1e'
          },
          {
            label: 'Lucro',
            data: this.lucro,
            backgroundColor: this.colors.lucro,
            borderRadius: [0, 0, 6, 6],
            hoverBackgroundColor: '#1f6fa0'
          }
        ]
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          intersect: false,
          mode: 'index'
        },
        plugins: {
          legend: {
            display: true,
            position: 'top',
            labels: {
              color: this.colors.text,
              font: { size: 13, family: 'DM Sans, sans-serif', weight: '500' },
              padding: 15
            }
          },
          tooltip: {
            backgroundColor: this.isDark ? '#333' : '#fff',
            titleColor: this.colors.text,
            bodyColor: this.colors.text,
            borderColor: this.colors.gridColor,
            borderWidth: 1,
            padding: 10
          }
        },
        scales: {
          x: {
            stacked: true,
            grid: {
              color: this.colors.gridColor,
              drawBorder: false
            },
            ticks: {
              color: this.colors.textSecondary,
              font: { size: 12, family: 'DM Sans, sans-serif' },
              callback: (value) => 'R$ ' + (value / 1000).toFixed(1) + 'k'
            }
          },
          y: {
            stacked: true,
            grid: {
              display: false,
              drawBorder: false
            },
            ticks: {
              color: this.colors.textSecondary,
              font: { size: 12, family: 'DM Sans, sans-serif' }
            }
          }
        }
      }
    });
  }
}

class LineChart {
  /**
   * Gráfico de linhas com preenchimento (Produção leite, Peso, etc)
   * Uso:
   *   new LineChart('chart-id', {
   *     title: 'Produção Acumulada',
   *     labels: ['Semana 1', 'Semana 2', 'Semana 3'],
   *     data: [150, 320, 485],
   *     unit: 'L'
   *   });
   */
  constructor(elementId, options = {}) {
    this.element = document.getElementById(elementId);
    if (!this.element) {
      console.error(`Elemento #${elementId} não encontrado`);
      return;
    }

    this.title = options.title || 'Série Temporal';
    this.labels = options.labels || [];
    this.data = options.data || [];
    this.unit = options.unit || '';

    this.isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    this.updateColors();
    this.observeThemeChange();

    this.chart = null;
    this.render();
  }

  updateColors() {
    const root = document.documentElement;
    const style = getComputedStyle(root);

    this.colors = {
      line: style.getPropertyValue('--green-500').trim() || '#52a044',
      fill: this.isDark ? 'rgba(82,160,68,.15)' : 'rgba(82,160,68,.08)',
      text: this.isDark ? '#e8ede7' : '#1c1c1c',
      textSecondary: this.isDark ? '#6b7d69' : '#888888',
      gridColor: this.isDark ? 'rgba(139,179,127,.1)' : 'rgba(80,120,60,.1)'
    };
  }

  observeThemeChange() {
    const observer = new MutationObserver((mutations) => {
      const theme = document.documentElement.getAttribute('data-theme');
      if (theme !== (this.isDark ? 'dark' : 'light')) {
        this.isDark = theme === 'dark';
        this.updateColors();
        if (this.chart) this.render();
      }
    });

    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['data-theme']
    });
  }

  render() {
    if (this.chart) {
      this.chart.destroy();
    }

    const ctx = this.element.getContext('2d');

    this.chart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: this.labels,
        datasets: [
          {
            label: this.title,
            data: this.data,
            borderColor: this.colors.line,
            backgroundColor: this.colors.fill,
            borderWidth: 3,
            fill: true,
            tension: 0.4,
            pointRadius: 6,
            pointHoverRadius: 8,
            pointBackgroundColor: this.colors.line,
            pointBorderColor: '#fff',
            pointBorderWidth: 2
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          intersect: false,
          mode: 'index'
        },
        plugins: {
          legend: {
            display: false
          },
          tooltip: {
            backgroundColor: this.isDark ? '#333' : '#fff',
            titleColor: this.colors.text,
            bodyColor: this.colors.text,
            borderColor: this.colors.gridColor,
            borderWidth: 1,
            padding: 10,
            callbacks: {
              label: (context) => context.parsed.y + ' ' + this.unit
            }
          }
        },
        scales: {
          x: {
            grid: {
              display: false,
              drawBorder: false
            },
            ticks: {
              color: this.colors.textSecondary,
              font: { size: 12, family: 'DM Sans, sans-serif' }
            }
          },
          y: {
            beginAtZero: true,
            grid: {
              color: this.colors.gridColor,
              drawBorder: false
            },
            ticks: {
              color: this.colors.textSecondary,
              font: { size: 12, family: 'DM Sans, sans-serif' },
              callback: (value) => value + ' ' + this.unit
            }
          }
        }
      }
    });
  }

  updateData(newData) {
    this.data = newData;
    if (this.chart) this.render();
  }
}

// Exportar para uso global
window.ComparativeChart = ComparativeChart;
window.StackedBarChart = StackedBarChart;
window.LineChart = LineChart;
