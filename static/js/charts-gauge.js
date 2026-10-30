/**
 * charts-gauge.js — Gauge SVG (velocímetro) para métricas de taxa
 * v5.8: Margem de Lucro, Taxa de Serviço, Taxa de Concepção, Taxa de Prenhez
 *
 * Uso:
 *   <div id="gauge-margem"></div>
 *   <script>
 *     new Gauge("gauge-margem", {
 *       value: 30.4,
 *       max: 100,
 *       label: "Margem de Lucro",
 *       unit: "%",
 *       thresholds: [30, 70]  // vermelho até 30%, amarelo até 70%, verde acima
 *     });
 *   </script>
 */

class Gauge {
  constructor(elementId, options = {}) {
    this.element = document.getElementById(elementId);
    if (!this.element) {
      console.error(`Elemento #${elementId} não encontrado`);
      return;
    }

    this.value = options.value || 0;
    this.max = options.max || 100;
    this.label = options.label || "Métrica";
    this.unit = options.unit || "%";
    this.thresholds = options.thresholds || [30, 70]; // [baixo, alto]
    this.width = options.width || 300;
    this.height = options.height || 180;
    this.size = Math.min(this.width, this.height * 1.5);

    // Cores baseadas em data-theme
    this.isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    this.updateColors();

    // Observar mudança de tema
    this.observeThemeChange();

    this.render();
  }

  updateColors() {
    const root = document.documentElement;
    const style = getComputedStyle(root);

    this.colors = {
      danger: style.getPropertyValue('--danger').trim() || '#c0392b',  // Vermelho
      warn: style.getPropertyValue('--warn').trim() || '#e67e22',      // Laranja
      success: style.getPropertyValue('--green-500').trim() || '#52a044', // Verde
      text: this.isDark ? '#e8ede7' : '#1c1c1c',
      textSecondary: this.isDark ? '#6b7d69' : '#888888',
      background: this.isDark ? '#1a2119' : '#ffffff'
    };
  }

  observeThemeChange() {
    const observer = new MutationObserver((mutations) => {
      const theme = document.documentElement.getAttribute('data-theme');
      if (theme !== (this.isDark ? 'dark' : 'light')) {
        this.isDark = theme === 'dark';
        this.updateColors();
        this.render();
      }
    });

    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['data-theme']
    });
  }

  getColor(percentage) {
    const [low, high] = this.thresholds;
    if (percentage < low) return this.colors.danger;
    if (percentage < high) return this.colors.warn;
    return this.colors.success;
  }

  render() {
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('viewBox', `0 0 ${this.width} ${this.height}`);
    svg.setAttribute('width', this.width);
    svg.setAttribute('height', this.height);
    svg.style.maxWidth = '100%';
    svg.style.height = 'auto';

    const centerX = this.width / 2;
    const centerY = this.height / 1.5;
    const radius = this.size / 3;

    // Fundo (arco cinza de fundo)
    const bgArc = this.createArc(centerX, centerY, radius, 0, 180);
    const bgPath = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    bgPath.setAttribute('d', bgArc);
    bgPath.setAttribute('stroke', this.isDark ? '#444' : '#e0e0e0');
    bgPath.setAttribute('stroke-width', radius * 0.25);
    bgPath.setAttribute('fill', 'none');
    bgPath.setAttribute('stroke-linecap', 'round');
    svg.appendChild(bgPath);

    // Arco colorido (0% a valor atual)
    const valuePercentage = Math.min(this.value / this.max, 1);
    const valueArc = this.createArc(centerX, centerY, radius, 0, 180 * valuePercentage);
    const valuePath = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    valuePath.setAttribute('d', valueArc);
    valuePath.setAttribute('stroke', this.getColor(this.value));
    valuePath.setAttribute('stroke-width', radius * 0.25);
    valuePath.setAttribute('fill', 'none');
    valuePath.setAttribute('stroke-linecap', 'round');
    valuePath.style.filter = `drop-shadow(0 0 8px ${this.getColor(this.value)}40)`;
    svg.appendChild(valuePath);

    // Agulha indicadora
    const angle = (valuePercentage * 180 - 90) * (Math.PI / 180);
    const needleLength = radius * 0.8;
    const needleX = centerX + needleLength * Math.cos(angle);
    const needleY = centerY + needleLength * Math.sin(angle);

    const needle = document.createElementNS('http://www.w3.org/2000/svg', 'line');
    needle.setAttribute('x1', centerX);
    needle.setAttribute('y1', centerY);
    needle.setAttribute('x2', needleX);
    needle.setAttribute('y2', needleY);
    needle.setAttribute('stroke', this.colors.text);
    needle.setAttribute('stroke-width', radius * 0.1);
    needle.setAttribute('stroke-linecap', 'round');
    svg.appendChild(needle);

    // Centro (círculo pequeno)
    const center = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
    center.setAttribute('cx', centerX);
    center.setAttribute('cy', centerY);
    center.setAttribute('r', radius * 0.12);
    center.setAttribute('fill', this.colors.text);
    svg.appendChild(center);

    // Marcas (0%, 50%, 100%)
    const marks = [0, 50, 100];
    marks.forEach(mark => {
      const markAngle = (mark - 90) * (Math.PI / 180);
      const markRadiusOuter = radius * 1.1;
      const markRadiusInner = radius * 0.95;
      const x1 = centerX + markRadiusInner * Math.cos(markAngle);
      const y1 = centerY + markRadiusInner * Math.sin(markAngle);
      const x2 = centerX + markRadiusOuter * Math.cos(markAngle);
      const y2 = centerY + markRadiusOuter * Math.sin(markAngle);

      const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
      line.setAttribute('x1', x1);
      line.setAttribute('y1', y1);
      line.setAttribute('x2', x2);
      line.setAttribute('y2', y2);
      line.setAttribute('stroke', this.colors.textSecondary);
      line.setAttribute('stroke-width', 2);
      svg.appendChild(line);

      // Label (0%, 50%, 100%)
      const labelRadius = radius * 1.25;
      const labelX = centerX + labelRadius * Math.cos(markAngle);
      const labelY = centerY + labelRadius * Math.sin(markAngle);

      const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      text.setAttribute('x', labelX);
      text.setAttribute('y', labelY);
      text.setAttribute('text-anchor', 'middle');
      text.setAttribute('dominant-baseline', 'central');
      text.setAttribute('fill', this.colors.textSecondary);
      text.setAttribute('font-size', radius * 0.25);
      text.setAttribute('font-family', 'DM Sans, sans-serif');
      text.setAttribute('font-weight', '400');
      text.textContent = `${mark}${this.unit}`;
      svg.appendChild(text);
    });

    // Valor grande no centro inferior
    const valueText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    valueText.setAttribute('x', centerX);
    valueText.setAttribute('y', centerY + radius * 0.5);
    valueText.setAttribute('text-anchor', 'middle');
    valueText.setAttribute('dominant-baseline', 'central');
    valueText.setAttribute('fill', this.colors.text);
    valueText.setAttribute('font-size', radius * 0.6);
    valueText.setAttribute('font-family', 'DM Sans, sans-serif');
    valueText.setAttribute('font-weight', '700');
    valueText.textContent = `${this.value.toFixed(1)}${this.unit}`;
    svg.appendChild(valueText);

    // Label do gauge
    const labelText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    labelText.setAttribute('x', centerX);
    labelText.setAttribute('y', this.height - 10);
    labelText.setAttribute('text-anchor', 'middle');
    labelText.setAttribute('dominant-baseline', 'central');
    labelText.setAttribute('fill', this.colors.textSecondary);
    labelText.setAttribute('font-size', radius * 0.3);
    labelText.setAttribute('font-family', 'DM Sans, sans-serif');
    labelText.setAttribute('font-weight', '400');
    labelText.textContent = this.label;
    svg.appendChild(labelText);

    this.element.innerHTML = '';
    this.element.appendChild(svg);
  }

  createArc(centerX, centerY, radius, startAngle, endAngle) {
    const start = this.polarToCartesian(centerX, centerY, radius, endAngle);
    const end = this.polarToCartesian(centerX, centerY, radius, startAngle);
    const largeArc = endAngle - startAngle <= 180 ? '0' : '1';
    return `M ${start.x} ${start.y} A ${radius} ${radius} 0 ${largeArc} 0 ${end.x} ${end.y}`;
  }

  polarToCartesian(centerX, centerY, radius, angleInDegrees) {
    const angleInRadians = (angleInDegrees - 90) * (Math.PI / 180);
    return {
      x: centerX + radius * Math.cos(angleInRadians),
      y: centerY + radius * Math.sin(angleInRadians)
    };
  }

  // Atualizar valor dinamicamente
  updateValue(newValue) {
    this.value = Math.max(0, Math.min(newValue, this.max));
    this.render();
  }
}

// Exportar para uso global
window.Gauge = Gauge;
