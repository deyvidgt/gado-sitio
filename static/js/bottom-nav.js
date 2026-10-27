/**
 * Bottom Navigation — v5.7 Sprint 3
 * Sticky bottom nav with 5 tabs, badges, and swipe support
 */

class BottomNav {
  constructor() {
    this.nav = document.getElementById('bottom-nav');
    if (!this.nav) return;

    this.items = this.nav.querySelectorAll('.nav-item');
    this.badges = {
      tarefas: document.getElementById('badge-tarefas'),
      alertas: document.getElementById('badge-alertas')
    };

    this.swipeStartX = 0;
    this.swipeCurrentX = 0;

    this.init();
  }

  init() {
    // Update active state on page load
    this.updateActiveState();

    // Click handling for tab navigation
    this.items.forEach(item => {
      item.addEventListener('click', (e) => {
        // Only prevent default if href is same as current location
        const href = item.getAttribute('href');
        if (href && href !== location.pathname && href !== location.href) {
          this.setActive(item);
        }
      });
    });

    // Swipe detection for mobile
    this.initSwipe();

    // Load badge counts
    this.loadBadgeCounts();

    // Poll for badge updates every 30 seconds
    setInterval(() => this.loadBadgeCounts(), 30000);

    // Adjust body padding for fixed nav
    this.adjustBodyPadding();

    // Adjust on window resize
    window.addEventListener('resize', () => this.adjustBodyPadding());
  }

  /**
   * Update active state based on current page URL
   */
  updateActiveState() {
    const current = location.pathname;
    let found = false;

    this.items.forEach(item => {
      const href = item.getAttribute('href') || '';
      // Match exact path or partial match for nested routes
      if (href === current || current.startsWith(href + '/') || (href === '/' && current === '/')) {
        this.setActive(item);
        found = true;
      } else {
        item.classList.remove('active');
      }
    });

    // Fallback: if no exact match, try endpoint matching
    if (!found && this.items.length > 0) {
      const endpoint = document.body.getAttribute('data-endpoint') || 'painel';
      const item = this.nav.querySelector(`[data-route="${endpoint}"]`);
      if (item) this.setActive(item);
    }
  }

  /**
   * Set active state on a navigation item
   */
  setActive(item) {
    this.items.forEach(i => i.classList.remove('active'));
    item.classList.add('active');
  }

  /**
   * Initialize swipe detection for left/right navigation
   */
  initSwipe() {
    this.nav.addEventListener('touchstart', (e) => {
      this.swipeStartX = e.touches[0].clientX;
    }, { passive: true });

    this.nav.addEventListener('touchmove', (e) => {
      this.swipeCurrentX = e.touches[0].clientX;
    }, { passive: true });

    this.nav.addEventListener('touchend', () => {
      const diff = this.swipeStartX - this.swipeCurrentX;
      const threshold = 50; // pixels

      if (Math.abs(diff) > threshold) {
        if (diff > 0) {
          // Swipe left = next tab
          this.focusNextTab();
        } else {
          // Swipe right = prev tab
          this.focusPrevTab();
        }
      }

      this.swipeStartX = 0;
      this.swipeCurrentX = 0;
    }, { passive: true });
  }

  /**
   * Move focus to next tab (left swipe)
   */
  focusNextTab() {
    const activeIndex = Array.from(this.items).findIndex(item =>
      item.classList.contains('active')
    );

    if (activeIndex < this.items.length - 1) {
      const nextItem = this.items[activeIndex + 1];
      this.setActive(nextItem);
      // Navigate after brief delay for visual feedback
      setTimeout(() => {
        window.location.href = nextItem.getAttribute('href');
      }, 150);
    }
  }

  /**
   * Move focus to previous tab (right swipe)
   */
  focusPrevTab() {
    const activeIndex = Array.from(this.items).findIndex(item =>
      item.classList.contains('active')
    );

    if (activeIndex > 0) {
      const prevItem = this.items[activeIndex - 1];
      this.setActive(prevItem);
      // Navigate after brief delay for visual feedback
      setTimeout(() => {
        window.location.href = prevItem.getAttribute('href');
      }, 150);
    }
  }

  /**
   * Load badge counts from API
   */
  loadBadgeCounts() {
    // Tarefas pendentes
    if (this.badges.tarefas) {
      fetch('/api/tarefas/pendentes-count')
        .then(r => {
          if (!r.ok) throw new Error(`HTTP ${r.status}`);
          return r.json();
        })
        .then(data => {
          if (data && data.count > 0) {
            this.badges.tarefas.textContent = data.count > 99 ? '99+' : data.count;
            this.badges.tarefas.style.display = 'flex';
          } else {
            this.badges.tarefas.style.display = 'none';
          }
        })
        .catch(err => {
          // Silently fail — API may not exist or user not authenticated
          console.debug('Badge tarefas:', err.message);
        });
    }

    // Alertas urgentes
    if (this.badges.alertas) {
      fetch('/api/alertas/count')
        .then(r => {
          if (!r.ok) throw new Error(`HTTP ${r.status}`);
          return r.json();
        })
        .then(data => {
          if (data && data.count > 0) {
            this.badges.alertas.textContent = data.count > 99 ? '99+' : data.count;
            this.badges.alertas.style.display = 'flex';
          } else {
            this.badges.alertas.style.display = 'none';
          }
        })
        .catch(err => {
          // Silently fail — API may not exist or user not authenticated
          console.debug('Badge alertas:', err.message);
        });
    }
  }

  /**
   * Adjust body padding to prevent content hiding behind fixed nav
   */
  adjustBodyPadding() {
    const navHeight = this.nav ? this.nav.offsetHeight : 0;
    document.body.style.paddingBottom = navHeight + 'px';
  }

  /**
   * Public API: Update a badge from external modules
   * Usage: BottomNav.updateBadge('tarefas', 5)
   */
  static updateBadge(badgeId, count) {
    const badge = document.getElementById(`badge-${badgeId}`);
    if (badge) {
      if (count > 0) {
        badge.textContent = count > 99 ? '99+' : count;
        badge.style.display = 'flex';
      } else {
        badge.style.display = 'none';
      }
    }
  }

  /**
   * Public API: Set active tab programmatically
   * Usage: BottomNav.setActiveTab('tarefas')
   */
  static setActiveTab(route) {
    const item = document.querySelector(`[data-route="${route}"]`);
    if (item && window.bottomNav) {
      window.bottomNav.setActive(item);
    }
  }
}

// Auto-initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
  window.bottomNav = new BottomNav();
});
