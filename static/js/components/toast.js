/**
 * Toast Notifications — v5.7 Sprint 4 Phase 2
 *
 * Features:
 * - Queue system (notifications stack and dismiss in order)
 * - Auto-dismiss after configurable duration
 * - 4 types: success, error, warning, info
 * - Smooth animations (slide-in from right, fade-out)
 * - ARIA live region for screen readers
 * - Mobile-friendly (slides from bottom)
 *
 * Usage:
 *   Toast.success('Item saved successfully!');
 *   Toast.error('Something went wrong', 5000);
 *   Toast.warning('This action cannot be undone');
 *   Toast.info('Loading...');
 *
 *   // Custom
 *   Toast.show('Custom message', 'info', 3000);
 */

class Toast {
  // Static properties
  static queue = [];
  static isShowing = false;
  static containerElement = null;

  /**
   * Show a toast notification
   * @param {string} message - Notification message
   * @param {string} type - Type: info, success, warning, error
   * @param {number} duration - Duration in milliseconds (0 = no auto-dismiss)
   */
  static show(message, type = 'info', duration = 4000) {
    const toast = new Toast(message, type, duration);
    this.queue.push(toast);
    if (!this.isShowing) {
      this.showNext();
    }
    return toast;
  }

  /**
   * Show next toast in queue
   */
  static showNext() {
    if (this.queue.length === 0) {
      this.isShowing = false;
      return;
    }

    const toast = this.queue.shift();
    Toast.isShowing = true;

    // Show toast
    setTimeout(() => {
      toast.element.classList.add('visible');
    }, 10);

    // Auto-dismiss if duration > 0
    if (toast.duration > 0) {
      setTimeout(() => {
        toast.dismiss();
      }, toast.duration);
    }
  }

  /**
   * Static convenience methods
   */
  static success(message, duration = 4000) {
    return this.show(message, 'success', duration);
  }

  static error(message, duration = 5000) {
    return this.show(message, 'error', duration);
  }

  static warning(message, duration = 4000) {
    return this.show(message, 'warning', duration);
  }

  static info(message, duration = 3000) {
    return this.show(message, 'info', duration);
  }

  /**
   * Instance constructor
   */
  constructor(message, type = 'info', duration = 4000) {
    this.message = message;
    this.type = type; // info, success, warning, error
    this.duration = duration;
    this.element = null;

    this.create();
  }

  /**
   * Create toast DOM element
   */
  create() {
    this.element = document.createElement('div');
    this.element.className = `toast toast-${this.type}`;
    this.element.setAttribute('role', 'status');
    this.element.setAttribute('aria-live', 'polite');
    this.element.setAttribute('aria-atomic', 'true');
    this.element.textContent = this.message;

    // Append to body (creates on demand)
    document.body.appendChild(this.element);

    // Add event listener for click to dismiss (optional)
    this.element.style.cursor = 'pointer';
    this.element.addEventListener('click', () => {
      this.dismiss();
    });
  }

  /**
   * Dismiss toast
   */
  dismiss() {
    // Remove visible class
    this.element.classList.remove('visible');

    // Remove from DOM after animation
    setTimeout(() => {
      if (this.element && this.element.parentNode) {
        this.element.remove();
      }
      Toast.showNext();
    }, 300);
  }

  /**
   * Clear all toasts in queue
   */
  static clearAll() {
    this.queue = [];
    const toasts = document.querySelectorAll('.toast');
    toasts.forEach(toast => {
      toast.classList.remove('visible');
      setTimeout(() => toast.remove(), 300);
    });
  }
}

// Auto-initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
  window.Toast = Toast;
});

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = Toast;
}
