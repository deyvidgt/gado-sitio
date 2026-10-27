# Sprint 3: Bottom Navigation — Plan

**Status:** 🔄 In Progress  
**Date:** 2026-10-27  
**Duration:** 1–2 days  
**Goal:** Sticky bottom navigation with 5 icons, notification badges, and tab switching  

---

## 📋 Objective

Implement a mobile-first **sticky bottom navigation bar** that:
- Shows 5 action icons (🏠 🗓️ 📊 💬 👤)
- Displays notification badges (red with count)
- Allows swipe-left/right for tab switching
- Maintains active state across page loads
- Responsive: full-width mobile, condensed tablet+

---

## 🎯 Deliverables

### 1. CSS Component: `.bottom-nav`

**File:** `static/design-tokens.css` (expand existing)

```css
.bottom-nav {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  height: 60px;
  display: flex;
  justify-content: space-around;
  align-items: center;
  background: var(--surface);
  border-top: 1px solid var(--border);
  box-shadow: var(--shadow-lg);
  z-index: 999;
  touch-action: manipulation;
}

.nav-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  height: 100%;
  position: relative;
  text-decoration: none;
  color: var(--text-2);
  font-size: 12px;
  transition: all 0.2s;
  cursor: pointer;
}

.nav-item:hover {
  background: var(--bg-2);
  color: var(--text);
}

.nav-item.active {
  color: var(--accent, #2c5aa0);
  border-bottom: 3px solid var(--accent, #2c5aa0);
}

.nav-item .icon {
  font-size: 24px;
  margin-bottom: 2px;
}

.nav-item .label {
  font-size: 11px;
  line-height: 1.2;
  text-align: center;
  max-width: 40px;
}

.nav-badge {
  position: absolute;
  top: -8px;
  right: 8px;
  background: var(--color-danger-main, #e74c3c);
  color: white;
  border-radius: 50%;
  min-width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: bold;
  border: 2px solid var(--surface);
}

@media (max-width: 768px) {
  .bottom-nav {
    height: 56px;
  }

  .nav-item .icon {
    font-size: 22px;
  }

  .nav-item .label {
    font-size: 10px;
  }
}

@media (max-width: 480px) {
  .bottom-nav {
    height: 52px;
  }

  .nav-item .icon {
    font-size: 20px;
    margin-bottom: 1px;
  }

  .nav-item .label {
    display: none;
  }

  .nav-badge {
    right: 4px;
    min-width: 18px;
    height: 18px;
    font-size: 10px;
  }
}
```

### 2. HTML Template Block

**File:** `templates/base.html`

Add before `</body>`:

```html
<!-- Bottom Navigation (v5.7 Sprint 3) -->
<nav class="bottom-nav" id="bottom-nav">
  <a href="{{ url_for('painel') }}" class="nav-item {% if request.endpoint == 'painel' %}active{% endif %}" data-route="painel">
    <div class="icon">🏠</div>
    <div class="label">Painel</div>
  </a>

  <a href="{{ url_for('tarefas') }}" class="nav-item {% if request.endpoint == 'tarefas' %}active{% endif %}" data-route="tarefas">
    <div class="icon">🗓️</div>
    <div class="label">Agenda</div>
    <div class="nav-badge" id="badge-tarefas" style="display:none;">0</div>
  </a>

  <a href="{{ url_for('relatorios') }}" class="nav-item {% if request.endpoint == 'relatorios' %}active{% endif %}" data-route="relatorios">
    <div class="icon">📊</div>
    <div class="label">Relatórios</div>
  </a>

  <a href="{{ url_for('central_alertas') }}" class="nav-item {% if request.endpoint == 'central_alertas' %}active{% endif %}" data-route="central_alertas">
    <div class="icon">🔔</div>
    <div class="label">Alertas</div>
    <div class="nav-badge" id="badge-alertas" style="display:none;">0</div>
  </a>

  <a href="{{ url_for('configuracoes') }}" class="nav-item {% if request.endpoint == 'configuracoes' %}active{% endif %}" data-route="configuracoes">
    <div class="icon">👤</div>
    <div class="label">Perfil</div>
  </a>
</nav>
```

### 3. JavaScript: Bottom Nav Logic

**File:** `static/js/bottom-nav.js` (new, ~150 lines)

```javascript
class BottomNav {
  constructor() {
    this.nav = document.getElementById('bottom-nav');
    if (!this.nav) return;

    this.items = this.nav.querySelectorAll('.nav-item');
    this.badges = {
      tarefas: document.getElementById('badge-tarefas'),
      alertas: document.getElementById('badge-alertas')
    };

    this.init();
  }

  init() {
    // Update active state on page load
    this.updateActiveState();

    // Click handling
    this.items.forEach(item => {
      item.addEventListener('click', (e) => {
        if (e.currentTarget.href && e.currentTarget.href !== location.href) {
          this.setActive(e.currentTarget);
        }
      });
    });

    // Swipe detection for mobile
    this.initSwipe();

    // Load badge counts
    this.loadBadgeCounts();

    // Smooth body padding to account for fixed nav
    this.adjustBodyPadding();
  }

  updateActiveState() {
    const current = location.pathname;
    this.items.forEach(item => {
      const href = new URL(item.href).pathname;
      if (href === current) {
        this.setActive(item);
      } else {
        item.classList.remove('active');
      }
    });
  }

  setActive(item) {
    this.items.forEach(i => i.classList.remove('active'));
    item.classList.add('active');
  }

  initSwipe() {
    let startX = 0;
    let currentX = 0;

    this.nav.addEventListener('touchstart', (e) => {
      startX = e.touches[0].clientX;
    });

    this.nav.addEventListener('touchmove', (e) => {
      currentX = e.touches[0].clientX;
    });

    this.nav.addEventListener('touchend', () => {
      const diff = startX - currentX;
      if (Math.abs(diff) > 50) {
        // Swipe left = next tab
        if (diff > 0) this.focusNextTab();
        // Swipe right = prev tab
        if (diff < 0) this.focusPrevTab();
      }
    });
  }

  focusNextTab() {
    const activeIndex = Array.from(this.items).findIndex(item =>
      item.classList.contains('active')
    );
    if (activeIndex < this.items.length - 1) {
      this.items[activeIndex + 1].click();
    }
  }

  focusPrevTab() {
    const activeIndex = Array.from(this.items).findIndex(item =>
      item.classList.contains('active')
    );
    if (activeIndex > 0) {
      this.items[activeIndex - 1].click();
    }
  }

  loadBadgeCounts() {
    // Tarefas pendentes
    fetch('/api/tarefas/pendentes-count')
      .then(r => r.json())
      .then(data => {
        if (data.count > 0) {
          this.badges.tarefas.textContent = data.count;
          this.badges.tarefas.style.display = 'flex';
        }
      })
      .catch(() => {}); // Silently fail

    // Alertas
    fetch('/api/alertas/count')
      .then(r => r.json())
      .then(data => {
        if (data.count > 0) {
          this.badges.alertas.textContent = data.count;
          this.badges.alertas.style.display = 'flex';
        }
      })
      .catch(() => {}); // Silently fail
  }

  adjustBodyPadding() {
    // Add padding-bottom to body so content doesn't hide behind nav
    const navHeight = this.nav.offsetHeight;
    document.body.style.paddingBottom = navHeight + 'px';
  }

  // Public API for updating badges from other modules
  static updateBadge(badgeId, count) {
    const badge = document.getElementById(`badge-${badgeId}`);
    if (badge) {
      if (count > 0) {
        badge.textContent = count;
        badge.style.display = 'flex';
      } else {
        badge.style.display = 'none';
      }
    }
  }
}

// Auto-init on DOM ready
document.addEventListener('DOMContentLoaded', () => {
  window.bottomNav = new BottomNav();
});
```

### 4. API Endpoints (Backend)

**File:** `routes_dashboard.py` (add)

```python
@app.route('/api/tarefas/pendentes-count')
@login_required
def api_tarefas_pendentes_count():
    """Retorna número de tarefas pendentes para badge"""
    import tarefas
    pend = tarefas.pendentes()
    return jsonify({'count': len(pend.get('atrasadas', []))})

@app.route('/api/alertas/count')
@login_required
def api_alertas_count():
    """Retorna número de alertas para badge"""
    import alertas as A
    alts = A.todos()
    urgentes = [a for a in alts if a.get('urgencia') == 'urgente']
    return jsonify({'count': len(urgentes)})
```

---

## 📅 Implementation Phases

### Phase 1: CSS & HTML (Day 1, Morning)
- [ ] Expand `design-tokens.css` with `.bottom-nav` + `.nav-item` + `.nav-badge`
- [ ] Add bottom-nav template block to `templates/base.html`
- [ ] Add padding-bottom to body to prevent content hiding
- [ ] Test responsiveness: mobile (480px), tablet (768px), desktop (1024px)
- [ ] **Commit:** "Sprint 3 Phase 1: Bottom navigation CSS + HTML"

### Phase 2: JavaScript Logic (Day 1, Afternoon)
- [ ] Create `static/js/bottom-nav.js` with BottomNav class
- [ ] Implement active state management
- [ ] Implement swipe detection (left/right)
- [ ] Register script in `templates/base.html`
- [ ] Test: Click tabs, swipe on mobile
- [ ] **Commit:** "Sprint 3 Phase 2: Bottom nav JavaScript + swipe"

### Phase 3: Badge System (Day 1–2, Morning)
- [ ] Add API endpoints for badge counts (/api/tarefas/pendentes-count, /api/alertas/count)
- [ ] Implement badge loading in BottomNav.loadBadgeCounts()
- [ ] Add `.nav-badge` styling with red circle + count
- [ ] Test: Create pending task → badge updates
- [ ] **Commit:** "Sprint 3 Phase 3: Notification badges + API"

### Phase 4: Testing & Polish (Day 2, Afternoon)
- [ ] Test all 5 tabs navigation
- [ ] Test swipe left/right on mobile
- [ ] Test badge updates
- [ ] Test dark mode
- [ ] Test offline (should still show nav with no badges)
- [ ] Test WCAG A (focus management, keyboard nav)
- [ ] **Commit:** "Sprint 3 Complete: Bottom navigation production ready"

---

## 🧪 Test Cases

| Test | Steps | Expected | Status |
|------|-------|----------|--------|
| **Tab Click** | Click each icon | Navigates + active state | |
| **Swipe Left** | Mobile: swipe left | Next tab focused | |
| **Swipe Right** | Mobile: swipe right | Prev tab focused | |
| **Badge Count** | Create task → check badge | Shows count, disappears when 0 | |
| **Mobile (480px)** | Toggle device → check nav | Icons only, no labels | |
| **Tablet (768px)** | 768px width → check nav | Icons + labels | |
| **Dark Mode** | Toggle theme → check nav | Colors adapt | |
| **Keyboard** | Tab + Enter | Tab navigation works | |
| **Offline** | Mark offline → check nav | Nav visible, no badge API calls fail | |
| **Persistence** | Reload page → check active | Active state maintained | |

---

## 📊 Definition of Done

- [ ] CSS: `.bottom-nav`, `.nav-item`, `.nav-badge` styled
- [ ] HTML: 5 nav items in template
- [ ] JavaScript: Active state, swipe, badge loading
- [ ] API: 2 endpoints for badge counts
- [ ] Tests: All 10 test cases pass
- [ ] Docs: Updated CHANGELOG.md
- [ ] Commit: 4 atomic commits (Phase 1–4)
- [ ] Branch: Pushed to origin/sprint-3-bottom-nav
- [ ] Review: Ready for merge to develop

---

## 🔗 Dependencies

- Sprint 2 (v5.7.0) must be deployed ✅
- Design tokens (`design-tokens.css`) available ✅
- Dark mode CSS variables available ✅
- Mobile responsive classes available ✅

---

## 📚 Reference

- File: `docs/V57_SPRINTS_PROGRESS.md` (original plan)
- Component: `.card-status` in `design-tokens.css` (pattern reference)
- API pattern: `/api/animais/*` in `routes_animais.py`
- Badge: `.nav-badge` (new component)

---

## 🎯 Success Criteria

✅ Bottom nav visible on all pages  
✅ 5 tabs functional with navigation  
✅ Swipe detection works on mobile  
✅ Badges show/hide correctly  
✅ Responsive: mobile (icons only), tablet+ (icons + labels)  
✅ Dark mode supported  
✅ WCAG A accessible  
✅ Zero breaking changes  
✅ All tests passing  

---

**Next:** Proceed to Phase 1 implementation

Co-Authored-By: Claude Code <noreply@anthropic.com>
