/**
 * Modal Component — v5.7 Sprint 4
 *
 * Features:
 * - Focus trap (Tab key cycles through focusable elements)
 * - ESC key to close
 * - Click outside modal to close
 * - Smooth animations
 * - ARIA attributes for accessibility
 * - Public API: Modal.confirm()
 *
 * Usage:
 *   const modal = new Modal({
 *     title: 'Confirmar ação',
 *     content: '<p>Tem certeza?</p>',
 *     buttons: [
 *       { label: 'Cancelar', action: 'cancel', type: 'outline' },
 *       { label: 'Confirmar', action: 'confirm', type: 'primary', onClick: () => console.log('Confirmed') }
 *     ]
 *   });
 *   modal.open();
 */

class Modal {
  constructor(options = {}) {
    this.title = options.title || 'Dialog';
    this.content = options.content || '';
    this.buttons = options.buttons || [];
    this.onClose = options.onClose || null;
    this.focusTrap = options.focusTrap !== false;

    this.overlay = null;
    this.modal = null;
    this.previousFocus = null;
    this.handleEscKey = null;
    this.handleTabKey = null;

    this.create();
  }

  /**
   * Create modal DOM elements
   */
  create() {
    // Create overlay (click outside to close)
    this.overlay = document.createElement('div');
    this.overlay.className = 'modal-overlay';
    this.overlay.addEventListener('click', (e) => {
      if (e.target === this.overlay) {
        this.close();
      }
    });

    // Create modal container
    this.modal = document.createElement('div');
    this.modal.className = 'modal';
    this.modal.setAttribute('role', 'dialog');
    this.modal.setAttribute('aria-modal', 'true');
    this.modal.setAttribute('aria-labelledby', 'modal-title-' + this._generateId());

    // Create header
    const header = document.createElement('div');
    header.className = 'modal-header';
    const titleEl = document.createElement('h2');
    titleEl.className = 'modal-title';
    titleEl.textContent = this.title;
    const closeBtn = document.createElement('button');
    closeBtn.className = 'modal-close';
    closeBtn.setAttribute('aria-label', 'Fechar');
    closeBtn.innerHTML = '&times;';
    closeBtn.addEventListener('click', () => this.close());

    header.appendChild(titleEl);
    header.appendChild(closeBtn);

    // Create body
    const body = document.createElement('div');
    body.className = 'modal-body';
    body.innerHTML = this.content;

    // Create footer with buttons
    let footerElement = null;
    if (this.buttons.length > 0) {
      footerElement = document.createElement('div');
      footerElement.className = 'modal-footer';

      this.buttons.forEach(btn => {
        const button = document.createElement('button');
        button.className = `btn btn-${btn.type || 'outline'}`;
        button.textContent = btn.label;
        button.setAttribute('data-action', btn.action);
        button.addEventListener('click', (e) => {
          if (btn.onClick) {
            btn.onClick(e);
          }
          if (btn.closeOnClick !== false) {
            this.close();
          }
        });
        footerElement.appendChild(button);
      });
    }

    // Assemble modal
    this.modal.appendChild(header);
    this.modal.appendChild(body);
    if (footerElement) {
      this.modal.appendChild(footerElement);
    }

    this.overlay.appendChild(this.modal);
    document.body.appendChild(this.overlay);
  }

  /**
   * Setup focus trap (Tab key cycles within modal)
   */
  setupFocusTrap() {
    const focusableSelectors = 'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])';
    const focusableElements = Array.from(this.modal.querySelectorAll(focusableSelectors));

    if (focusableElements.length === 0) {
      return;
    }

    const firstElement = focusableElements[0];
    const lastElement = focusableElements[focusableElements.length - 1];

    // Focus first element
    setTimeout(() => firstElement.focus(), 0);

    // Handle Tab key for focus trap
    this.handleTabKey = (e) => {
      if (e.key !== 'Tab') return;

      if (e.shiftKey) {
        // Shift+Tab: move focus backward
        if (document.activeElement === firstElement) {
          lastElement.focus();
          e.preventDefault();
        }
      } else {
        // Tab: move focus forward
        if (document.activeElement === lastElement) {
          firstElement.focus();
          e.preventDefault();
        }
      }
    };

    this.modal.addEventListener('keydown', this.handleTabKey);
  }

  /**
   * Open modal
   */
  open() {
    this.previousFocus = document.activeElement;
    this.overlay.classList.add('active');

    // Setup focus trap if enabled
    if (this.focusTrap) {
      this.setupFocusTrap();
    }

    // Setup ESC key handler
    this.handleEscKey = (e) => {
      if (e.key === 'Escape') {
        this.close();
      }
    };
    document.addEventListener('keydown', this.handleEscKey);

    // Prevent body scroll
    document.body.style.overflow = 'hidden';
  }

  /**
   * Close modal
   */
  close() {
    this.overlay.classList.remove('active');

    // Remove event listeners
    if (this.handleEscKey) {
      document.removeEventListener('keydown', this.handleEscKey);
    }
    if (this.handleTabKey) {
      this.modal.removeEventListener('keydown', this.handleTabKey);
    }

    // Restore body scroll
    document.body.style.overflow = '';

    // Remove from DOM after animation
    setTimeout(() => {
      if (this.onClose) {
        this.onClose();
      }
      this.overlay.remove();
      // Restore focus to previously focused element
      if (this.previousFocus && document.contains(this.previousFocus)) {
        this.previousFocus.focus();
      }
    }, 300);
  }

  /**
   * Generate unique ID for modal
   */
  _generateId() {
    return 'modal-' + Math.random().toString(36).substr(2, 9);
  }

  /**
   * Static API: Show confirm dialog
   * Usage: Modal.confirm('Title', 'Message', () => { ... })
   */
  static confirm(title, message, onConfirm) {
    const modal = new Modal({
      title: title,
      content: `<p>${message}</p>`,
      buttons: [
        {
          label: 'Cancelar',
          action: 'cancel',
          type: 'outline',
          closeOnClick: true
        },
        {
          label: 'Confirmar',
          action: 'confirm',
          type: 'primary',
          onClick: onConfirm,
          closeOnClick: true
        }
      ]
    });
    modal.open();
    return modal;
  }

  /**
   * Static API: Show alert dialog
   * Usage: Modal.alert('Title', 'Message')
   */
  static alert(title, message) {
    const modal = new Modal({
      title: title,
      content: `<p>${message}</p>`,
      buttons: [
        {
          label: 'OK',
          action: 'ok',
          type: 'primary',
          closeOnClick: true
        }
      ]
    });
    modal.open();
    return modal;
  }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = Modal;
}
