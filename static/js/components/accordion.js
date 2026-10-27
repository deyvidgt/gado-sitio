/**
 * Accordion Component — v5.7 Sprint 4 Phase 3
 *
 * Features:
 * - Expandable/collapsible sections
 * - Smooth slide animation with max-height
 * - Single or multiple open items
 * - ARIA labels (aria-expanded, aria-controls)
 * - Keyboard support (Enter, Space to toggle)
 * - Arrow key navigation (optional)
 *
 * Usage (HTML):
 *   <div class="accordion">
 *     <div class="accordion-item">
 *       <button class="accordion-header" aria-expanded="false" aria-controls="panel1">
 *         Section 1
 *         <span class="accordion-icon">▼</span>
 *       </button>
 *       <div id="panel1" class="accordion-body">
 *         <div class="accordion-body-content">Content here</div>
 *       </div>
 *     </div>
 *   </div>
 *
 * Usage (JavaScript):
 *   new Accordion('.accordion', { allowMultiple: true });
 */

class Accordion {
  constructor(selector, options = {}) {
    this.container = document.querySelector(selector);
    if (!this.container) return;

    this.allowMultiple = options.allowMultiple !== false;
    this.closeOthers = options.closeOthers !== false && !this.allowMultiple;

    this.headers = this.container.querySelectorAll('.accordion-header');
    this.init();
  }

  /**
   * Initialize accordion
   */
  init() {
    this.headers.forEach((header, index) => {
      // Setup ARIA if not already set
      if (!header.hasAttribute('aria-expanded')) {
        header.setAttribute('aria-expanded', 'false');
      }

      const panelId = header.getAttribute('aria-controls') || `accordion-panel-${index}`;
      const panel = document.getElementById(panelId);

      if (panel) {
        header.setAttribute('aria-controls', panelId);
      }

      // Click handler
      header.addEventListener('click', () => this.toggle(header));

      // Keyboard handler
      header.addEventListener('keydown', (e) => this.handleKeydown(e, header));
    });
  }

  /**
   * Toggle accordion item
   */
  toggle(header) {
    const isExpanded = header.getAttribute('aria-expanded') === 'true';

    if (isExpanded) {
      this.close(header);
    } else {
      this.open(header);
    }
  }

  /**
   * Open accordion item
   */
  open(header) {
    if (this.closeOthers) {
      // Close other headers
      this.headers.forEach((h) => {
        if (h !== header && h.getAttribute('aria-expanded') === 'true') {
          this.close(h);
        }
      });
    }

    header.setAttribute('aria-expanded', 'true');

    // Trigger animation
    const panelId = header.getAttribute('aria-controls');
    if (panelId) {
      const panel = document.getElementById(panelId);
      if (panel) {
        panel.style.maxHeight = panel.scrollHeight + 'px';
      }
    }
  }

  /**
   * Close accordion item
   */
  close(header) {
    header.setAttribute('aria-expanded', 'false');

    const panelId = header.getAttribute('aria-controls');
    if (panelId) {
      const panel = document.getElementById(panelId);
      if (panel) {
        panel.style.maxHeight = '0';
      }
    }
  }

  /**
   * Handle keyboard navigation
   */
  handleKeydown(e, header) {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      this.toggle(header);
    }

    // Arrow keys for navigation (optional)
    if (e.key === 'ArrowUp') {
      e.preventDefault();
      const index = Array.from(this.headers).indexOf(header);
      if (index > 0) {
        this.headers[index - 1].focus();
      }
    }

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      const index = Array.from(this.headers).indexOf(header);
      if (index < this.headers.length - 1) {
        this.headers[index + 1].focus();
      }
    }

    if (e.key === 'Home') {
      e.preventDefault();
      this.headers[0].focus();
    }

    if (e.key === 'End') {
      e.preventDefault();
      this.headers[this.headers.length - 1].focus();
    }
  }

  /**
   * Open all items
   */
  openAll() {
    if (this.allowMultiple) {
      this.headers.forEach((header) => this.open(header));
    }
  }

  /**
   * Close all items
   */
  closeAll() {
    this.headers.forEach((header) => this.close(header));
  }

  /**
   * Destroy accordion
   */
  destroy() {
    this.headers.forEach((header) => {
      header.removeEventListener('click', () => {});
      header.removeEventListener('keydown', () => {});
    });
  }
}

// Auto-initialize accordions on DOM ready
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('[data-accordion]').forEach((el) => {
    const allowMultiple = el.getAttribute('data-accordion-multiple') === 'true';
    new Accordion(`#${el.id || ''}`, { allowMultiple });
  });

  window.Accordion = Accordion;
});

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = Accordion;
}
