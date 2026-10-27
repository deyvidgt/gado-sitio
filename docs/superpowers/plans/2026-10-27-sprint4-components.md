# Sprint 4: Component Library — Plan

**Status:** 🔄 In Progress  
**Date:** 2026-10-27  
**Duration:** 1–2 days  
**Goal:** Build reusable UI component library (Modal, Toast, Accordion, Confirm, Form Validation)

---

## 📋 Objective

Create a **production-ready component library** with 5 essential UI patterns that work across the entire app:

1. **Modal** — Dialog boxes with focus trap and ESC to close
2. **Toast** — Auto-dismissing notifications (success, error, warning, info)
3. **Accordion** — Expand/collapse sections with animation
4. **Confirm Modal** — Destructive action confirmation (delete, logout, etc.)
5. **Form Validation** — Real-time field validation with error messages

All components are:
- ♿ **Accessible** (WCAG 2.1 AA)
- 🎨 **Themeable** (dark mode included)
- 📱 **Mobile-first** (responsive, touch-friendly)
- ⚡ **Performant** (no dependencies, vanilla JS)
- 🧪 **Tested** (comprehensive test suite)

---

## 🎯 Deliverables

### 1. Modal Component

**File:** `static/css/components/modal.css` (new, ~150 lines)

```css
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: none;
  z-index: 1000;
  animation: fade-in 0.2s ease;
}

.modal-overlay.active {
  display: flex;
  align-items: center;
  justify-content: center;
}

.modal {
  background: var(--surface);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-xl);
  max-width: 500px;
  width: 90%;
  max-height: 90vh;
  overflow-y: auto;
  animation: slide-up 0.3s ease;
}

.modal-header {
  padding: var(--spacing-lg);
  border-bottom: 1px solid var(--border);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.modal-title {
  font-size: var(--font-lg);
  font-weight: bold;
}

.modal-close {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: var(--text-2);
}

.modal-body {
  padding: var(--spacing-lg);
}

.modal-footer {
  padding: var(--spacing-lg);
  border-top: 1px solid var(--border);
  display: flex;
  gap: var(--spacing-md);
  justify-content: flex-end;
}

@keyframes fade-in {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes slide-up {
  from { transform: translateY(20px); opacity: 0; }
  to { transform: translateY(0); opacity: 1; }
}
```

**File:** `static/js/components/modal.js` (new, ~120 lines)

```javascript
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

    this.create();
  }

  create() {
    // Create overlay
    this.overlay = document.createElement('div');
    this.overlay.className = 'modal-overlay';
    this.overlay.addEventListener('click', (e) => {
      if (e.target === this.overlay) this.close();
    });

    // Create modal
    this.modal = document.createElement('div');
    this.modal.className = 'modal';
    this.modal.setAttribute('role', 'dialog');
    this.modal.setAttribute('aria-modal', 'true');

    // Header
    const header = document.createElement('div');
    header.className = 'modal-header';
    header.innerHTML = `<h2 class="modal-title">${this.title}</h2>
      <button class="modal-close" aria-label="Fechar">&times;</button>`;
    header.querySelector('.modal-close').addEventListener('click', () => this.close());

    // Body
    const body = document.createElement('div');
    body.className = 'modal-body';
    body.innerHTML = this.content;

    // Footer with buttons
    let footer = '';
    if (this.buttons.length > 0) {
      footer = '<div class="modal-footer">';
      this.buttons.forEach(btn => {
        footer += `<button class="btn btn-${btn.type || 'outline'}" data-action="${btn.action}">
          ${btn.label}
        </button>`;
      });
      footer += '</div>';
    }

    this.modal.appendChild(header);
    this.modal.appendChild(body);
    if (footer) {
      const footerEl = document.createElement('div');
      footerEl.innerHTML = footer;
      this.modal.appendChild(footerEl.firstElementChild);

      // Attach button listeners
      this.modal.querySelectorAll('[data-action]').forEach(btn => {
        btn.addEventListener('click', (e) => {
          const action = e.target.getAttribute('data-action');
          const btnConfig = this.buttons.find(b => b.action === action);
          if (btnConfig?.onClick) btnConfig.onClick();
          if (btnConfig?.closeOnClick !== false) this.close();
        });
      });
    }

    this.overlay.appendChild(this.modal);
    document.body.appendChild(this.overlay);

    // Focus trap
    if (this.focusTrap) {
      this.setupFocusTrap();
    }

    // ESC to close
    this.handleEsc = (e) => {
      if (e.key === 'Escape') this.close();
    };
  }

  setupFocusTrap() {
    const focusableElements = this.modal.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );

    if (focusableElements.length === 0) return;

    const firstElement = focusableElements[0];
    const lastElement = focusableElements[focusableElements.length - 1];

    this.handleTab = (e) => {
      if (e.key !== 'Tab') return;

      if (e.shiftKey) {
        if (document.activeElement === firstElement) {
          lastElement.focus();
          e.preventDefault();
        }
      } else {
        if (document.activeElement === lastElement) {
          firstElement.focus();
          e.preventDefault();
        }
      }
    };

    this.modal.addEventListener('keydown', this.handleTab);
    firstElement.focus();
  }

  open() {
    this.previousFocus = document.activeElement;
    this.overlay.classList.add('active');
    document.addEventListener('keydown', this.handleEsc);
    document.body.style.overflow = 'hidden';
  }

  close() {
    this.overlay.classList.remove('active');
    document.removeEventListener('keydown', this.handleEsc);
    document.body.style.overflow = '';

    setTimeout(() => {
      if (this.onClose) this.onClose();
      this.overlay.remove();
      if (this.previousFocus) this.previousFocus.focus();
    }, 300);
  }

  static confirm(title, message, onConfirm) {
    const modal = new Modal({
      title,
      content: `<p>${message}</p>`,
      buttons: [
        { label: 'Cancelar', action: 'cancel', type: 'outline' },
        { label: 'Confirmar', action: 'confirm', type: 'primary', onClick: onConfirm }
      ]
    });
    modal.open();
    return modal;
  }
}
```

### 2. Toast Component

**File:** `static/js/components/toast.js` (new, ~100 lines)

```javascript
class Toast {
  static queue = [];
  static isShowing = false;

  static show(message, type = 'info', duration = 4000) {
    const toast = new Toast(message, type, duration);
    this.queue.push(toast);
    if (!this.isShowing) {
      this.showNext();
    }
  }

  constructor(message, type = 'info', duration = 4000) {
    this.message = message;
    this.type = type; // info, success, warning, error
    this.duration = duration;
    this.element = null;

    this.create();
  }

  create() {
    this.element = document.createElement('div');
    this.element.className = `toast toast-${this.type}`;
    this.element.setAttribute('role', 'status');
    this.element.setAttribute('aria-live', 'polite');
    this.element.innerHTML = this.message;

    document.body.appendChild(this.element);
    setTimeout(() => this.element.classList.add('visible'), 10);
  }

  dismiss() {
    this.element.classList.remove('visible');
    setTimeout(() => {
      this.element.remove();
      Toast.isShowing = false;
      Toast.showNext();
    }, 300);
  }

  static showNext() {
    if (this.queue.length === 0) return;

    const toast = this.queue.shift();
    Toast.isShowing = true;

    setTimeout(() => {
      toast.dismiss();
    }, toast.duration);
  }

  static success(msg, duration) {
    this.show(msg, 'success', duration);
  }

  static error(msg, duration) {
    this.show(msg, 'error', duration);
  }

  static warning(msg, duration) {
    this.show(msg, 'warning', duration);
  }

  static info(msg, duration) {
    this.show(msg, 'info', duration);
  }
}
```

**File:** `static/css/components/toast.css` (new, ~80 lines)

### 3. Accordion Component

**File:** `static/js/components/accordion.js` (new, ~110 lines)

### 4. Confirm Modal

**File:** Usage pattern from Modal class (no new file)

```javascript
// Usage
Modal.confirm(
  'Excluir pasto?',
  'Esta ação é irreversível.',
  () => {
    console.log('Confirmar exclusão');
    Toast.success('Pasto excluído com sucesso');
  }
);
```

### 5. Form Validation

**File:** `static/js/components/form-validator.js` (new, ~150 lines)

---

## 📅 Implementation Phases

### Phase 1: Modal Component (Day 1, Morning)
- [ ] Create CSS (`modal.css`)
- [ ] Create JavaScript class (`modal.js`)
- [ ] Add to design-tokens.css
- [ ] Test: open, close, focus trap, ESC key, static confirm method
- [ ] **Commit:** "Sprint 4 Phase 1: Modal component"

### Phase 2: Toast Component (Day 1, Afternoon)
- [ ] Create CSS (`toast.css`)
- [ ] Create JavaScript queue system (`toast.js`)
- [ ] Test: show/hide, queue, duration, types (success/error/warning/info)
- [ ] **Commit:** "Sprint 4 Phase 2: Toast notification system"

### Phase 3: Accordion & Form Validation (Day 2, Morning)
- [ ] Create accordion JavaScript (`accordion.js`)
- [ ] Create form validator (`form-validator.js`)
- [ ] Add CSS for both
- [ ] Test: expand/collapse, form validation
- [ ] **Commit:** "Sprint 4 Phase 3: Accordion + Form Validation"

### Phase 4: Tests & Integration (Day 2, Afternoon)
- [ ] Write 40+ tests (8 per component)
- [ ] Integrate Modal into delete forms
- [ ] Integrate Toast into success/error flows
- [ ] Test all dark mode
- [ ] **Commit:** "Sprint 4 Complete: Component library with tests"

---

## 🧪 Test Coverage

| Component | Tests |
|-----------|-------|
| Modal | 8 tests (open, close, buttons, focus trap, ESC, confirm) |
| Toast | 8 tests (show, queue, dismiss, types, duration) |
| Accordion | 8 tests (expand, collapse, single/multi) |
| Form Validator | 8 tests (validation rules, errors, submit) |
| Confirm Pattern | 4 tests (confirm flow, cancel) |
| Integration | 6 tests (dark mode, responsive, keyboard) |
| **Total** | **42 tests** |

---

## 📊 Definition of Done

- [ ] CSS: All 5 components styled (dark mode included)
- [ ] JavaScript: All classes implemented with public APIs
- [ ] HTML: Integration examples in comments
- [ ] Tests: 42 tests passing
- [ ] Docs: CHANGELOG.md updated
- [ ] Commits: 4 atomic commits (Phase 1–4)
- [ ] Branch: Pushed to origin/sprint-4-components
- [ ] Review: Ready for merge to develop

---

## 🎯 Success Criteria

✅ Modal: open/close with focus management, ESC key, static confirm  
✅ Toast: queue system, auto-dismiss, 4 types  
✅ Accordion: expand/collapse with smooth animation  
✅ Form Validation: real-time, error messages  
✅ Confirm Pattern: destructive action protection  
✅ Dark mode: 100% component coverage  
✅ Accessibility: WCAG 2.1 AA (focus, ARIA labels)  
✅ Tests: 42 passing, 0 failures  
✅ Zero breaking changes  

---

## 📁 Files to Create

```
static/css/components/
  ├─ modal.css           (150 lines)
  ├─ toast.css           (80 lines)
  ├─ accordion.css       (100 lines)
  └─ form-validator.css  (70 lines)

static/js/components/
  ├─ modal.js            (120 lines)
  ├─ toast.js            (100 lines)
  ├─ accordion.js        (110 lines)
  └─ form-validator.js   (150 lines)

tests/
  └─ test_v57_sprint4_components.py (500 lines)
```

**Total:** 1,380 lines of new code + tests

---

## 🚀 After Sprint 4

v5.7 will be **100% COMPLETE** with:
- ✅ Sprint 1: Mobile Refinements
- ✅ Sprint 2: Design System + Performance
- ✅ Sprint 3: Bottom Navigation
- ✅ Sprint 4: Component Library

**Ready for v5.8 roadmap** (Push notifications, Alerts enhancements, etc.)

---

**Next:** Proceed to Phase 1 (Modal component)

Co-Authored-By: Claude Code <noreply@anthropic.com>
