/**
 * Form Validator Component — v5.7 Sprint 4 Phase 3
 *
 * Features:
 * - Real-time field validation
 * - Multiple validation rules (required, email, min-length, pattern, etc.)
 * - Error message display
 * - Submit button management (disabled until form valid)
 * - ARIA live regions for screen readers
 * - Accessibility support
 *
 * Usage:
 *   const validator = new FormValidator('form-id', {
 *     name: { required: true, minLength: 3 },
 *     email: { required: true, type: 'email' },
 *     message: { required: true, minLength: 10 }
 *   });
 *
 *   validator.validate('name', 'John');
 *   validator.isFormValid();
 */

class FormValidator {
  constructor(formSelector, rules = {}, options = {}) {
    this.form = document.querySelector(formSelector);
    if (!this.form) return;

    this.rules = rules;
    this.options = options;
    this.errors = {};
    this.submitButton = this.form.querySelector('button[type="submit"]');
    this.ariaLive = this.createAriaLive();

    this.init();
  }

  /**
   * Initialize form validator
   */
  init() {
    this.form.addEventListener('submit', (e) => this.handleSubmit(e));

    // Attach validation listeners to all inputs
    this.form.querySelectorAll('input, textarea, select').forEach((field) => {
      const fieldName = field.name || field.id;

      // Real-time validation on blur
      field.addEventListener('blur', () => {
        this.validateField(fieldName, field.value);
      });

      // Real-time validation on input (debounced)
      field.addEventListener('input', () => {
        clearTimeout(this.debounceTimer);
        this.debounceTimer = setTimeout(() => {
          this.validateField(fieldName, field.value);
        }, 300);
      });
    });

    // Check form validity on any change
    this.form.addEventListener('change', () => this.updateSubmitButton());
  }

  /**
   * Create ARIA live region for error announcements
   */
  createAriaLive() {
    const ariaLive = document.createElement('div');
    ariaLive.setAttribute('role', 'status');
    ariaLive.setAttribute('aria-live', 'polite');
    ariaLive.setAttribute('aria-atomic', 'true');
    ariaLive.style.position = 'absolute';
    ariaLive.style.left = '-10000px';
    this.form.appendChild(ariaLive);
    return ariaLive;
  }

  /**
   * Validate a single field
   */
  validateField(fieldName, value) {
    const fieldRules = this.rules[fieldName];
    if (!fieldRules) return true;

    const field = this.form.querySelector(`[name="${fieldName}"], #${fieldName}`);
    if (!field) return true;

    const errors = [];

    // Required validation
    if (fieldRules.required && !value.trim()) {
      errors.push(fieldRules.requiredMessage || 'Este campo é obrigatório');
    }

    // Type validation
    if (value && fieldRules.type) {
      switch (fieldRules.type) {
        case 'email':
          if (!this.isValidEmail(value)) {
            errors.push(fieldRules.typeMessage || 'E-mail inválido');
          }
          break;
        case 'url':
          if (!this.isValidUrl(value)) {
            errors.push(fieldRules.typeMessage || 'URL inválida');
          }
          break;
        case 'number':
          if (isNaN(value)) {
            errors.push(fieldRules.typeMessage || 'Deve ser um número');
          }
          break;
        case 'phone':
          if (!this.isValidPhone(value)) {
            errors.push(fieldRules.typeMessage || 'Telefone inválido');
          }
          break;
      }
    }

    // Min length validation
    if (value && fieldRules.minLength && value.length < fieldRules.minLength) {
      errors.push(
        fieldRules.minLengthMessage || `Mínimo ${fieldRules.minLength} caracteres`
      );
    }

    // Max length validation
    if (value && fieldRules.maxLength && value.length > fieldRules.maxLength) {
      errors.push(
        fieldRules.maxLengthMessage || `Máximo ${fieldRules.maxLength} caracteres`
      );
    }

    // Pattern validation
    if (value && fieldRules.pattern) {
      const regex = new RegExp(fieldRules.pattern);
      if (!regex.test(value)) {
        errors.push(fieldRules.patternMessage || 'Formato inválido');
      }
    }

    // Min value validation (for numbers)
    if (value && fieldRules.min !== undefined && Number(value) < fieldRules.min) {
      errors.push(fieldRules.minMessage || `Mínimo ${fieldRules.min}`);
    }

    // Max value validation (for numbers)
    if (value && fieldRules.max !== undefined && Number(value) > fieldRules.max) {
      errors.push(fieldRules.maxMessage || `Máximo ${fieldRules.max}`);
    }

    // Custom validation function
    if (fieldRules.custom && typeof fieldRules.custom === 'function') {
      const customError = fieldRules.custom(value);
      if (customError) {
        errors.push(customError);
      }
    }

    // Update field state
    this.updateFieldState(field, fieldName, errors);
    this.errors[fieldName] = errors;

    // Announce errors to screen readers
    if (errors.length > 0) {
      this.ariaLive.textContent = `${fieldName}: ${errors.join(', ')}`;
    }

    return errors.length === 0;
  }

  /**
   * Update field visual state
   */
  updateFieldState(field, fieldName, errors) {
    const messageElement = this.getOrCreateMessageElement(field, fieldName);

    // Remove previous state classes
    field.classList.remove('is-valid', 'is-invalid');
    messageElement.classList.remove('show', 'error', 'success', 'warning');

    if (errors.length > 0) {
      field.classList.add('is-invalid');
      messageElement.classList.add('show', 'error');
      messageElement.textContent = errors[0];
    } else if (field.value.trim() !== '') {
      field.classList.add('is-valid');
      messageElement.classList.add('show', 'success');
      messageElement.textContent = 'Validado';
    }
  }

  /**
   * Get or create validation message element
   */
  getOrCreateMessageElement(field, fieldName) {
    let messageElement = field.nextElementSibling;

    if (!messageElement || !messageElement.classList.contains('form-validation-message')) {
      messageElement = document.createElement('div');
      messageElement.className = 'form-validation-message';
      messageElement.setAttribute('role', 'alert');
      field.parentNode.insertBefore(messageElement, field.nextSibling);
    }

    return messageElement;
  }

  /**
   * Validate entire form
   */
  validateForm() {
    let isValid = true;

    this.form.querySelectorAll('input, textarea, select').forEach((field) => {
      const fieldName = field.name || field.id;
      if (!this.validateField(fieldName, field.value)) {
        isValid = false;
      }
    });

    return isValid;
  }

  /**
   * Check if form is valid
   */
  isFormValid() {
    for (const fieldName in this.rules) {
      if (this.errors[fieldName] && this.errors[fieldName].length > 0) {
        return false;
      }
    }
    return true;
  }

  /**
   * Update submit button state
   */
  updateSubmitButton() {
    if (!this.submitButton) return;

    if (this.isFormValid()) {
      this.submitButton.disabled = false;
    } else {
      this.submitButton.disabled = true;
    }
  }

  /**
   * Handle form submission
   */
  handleSubmit(e) {
    if (!this.validateForm()) {
      e.preventDefault();
      this.ariaLive.textContent = 'Por favor corrija os erros do formulário';
    }
  }

  /**
   * Email validation
   */
  isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  }

  /**
   * URL validation
   */
  isValidUrl(url) {
    try {
      new URL(url);
      return true;
    } catch (e) {
      return false;
    }
  }

  /**
   * Phone validation (simple: 10-11 digits)
   */
  isValidPhone(phone) {
    const phoneRegex = /^\d{10,11}$/;
    return phoneRegex.test(phone.replace(/\D/g, ''));
  }

  /**
   * Reset form
   */
  reset() {
    this.form.reset();
    this.errors = {};
    this.form.querySelectorAll('input, textarea, select').forEach((field) => {
      field.classList.remove('is-valid', 'is-invalid');
      const messageElement = field.nextElementSibling;
      if (messageElement && messageElement.classList.contains('form-validation-message')) {
        messageElement.classList.remove('show');
      }
    });
    this.updateSubmitButton();
  }

  /**
   * Clear errors
   */
  clearErrors() {
    this.errors = {};
    this.form.querySelectorAll('.form-validation-message').forEach((el) => {
      el.classList.remove('show');
    });
  }

  /**
   * Get all errors
   */
  getErrors() {
    return this.errors;
  }

  /**
   * Get form data as object
   */
  getFormData() {
    const formData = {};
    this.form.querySelectorAll('input, textarea, select').forEach((field) => {
      if (field.type === 'checkbox') {
        if (field.checked) {
          formData[field.name] = field.value;
        }
      } else if (field.type === 'radio') {
        if (field.checked) {
          formData[field.name] = field.value;
        }
      } else {
        formData[field.name || field.id] = field.value;
      }
    });
    return formData;
  }
}

// Auto-initialize validators on DOM ready
document.addEventListener('DOMContentLoaded', () => {
  window.FormValidator = FormValidator;
});

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = FormValidator;
}
