/**
 * Gestos para Mobile (v5.7)
 * - Swipe left/right: navegar entre abas
 * - Long-press: menu de contexto
 * - Scroll up/down: mostrar/esconder bottom-actions
 */

class Gestures {
  constructor() {
    this.startX = 0;
    this.startY = 0;
    this.startTime = 0;
    this.longPressTimer = null;
    this.lastScrollY = 0;
    this.isScrolling = false;
    
    this.init();
  }

  init() {
    this.initDrawer();
    this.initSwipe();
    this.initLongPress();
    this.initScrollBehavior();
  }

  // ── Drawer Menu Toggle ──────────────────────────────────────────────────

  initDrawer() {
    const toggle = document.querySelector('.drawer-toggle');
    const overlay = document.querySelector('.drawer-overlay');
    const menu = document.querySelector('.drawer-menu');

    if (!toggle || !overlay || !menu) return;

    toggle.addEventListener('click', () => this.toggleDrawer(menu, overlay));
    overlay.addEventListener('click', () => this.closeDrawer(menu, overlay));

    // Swipe para fechar drawer
    document.addEventListener('touchstart', (e) => {
      this.startX = e.touches[0].clientX;
    });

    document.addEventListener('touchend', (e) => {
      const endX = e.changedTouches[0].clientX;
      if (this.startX > 100 && endX < 50 && menu.classList.contains('active')) {
        this.closeDrawer(menu, overlay);
      }
    });
  }

  toggleDrawer(menu, overlay) {
    menu.classList.toggle('active');
    overlay.classList.toggle('active');
  }

  closeDrawer(menu, overlay) {
    menu.classList.remove('active');
    overlay.classList.remove('active');
  }

  // ── Swipe para Abas ────────────────────────────────────────────────────

  initSwipe() {
    const tabsContainer = document.querySelector('.tabs-sticky');
    if (!tabsContainer) return;

    document.addEventListener('touchstart', (e) => {
      this.startX = e.touches[0].clientX;
      this.startTime = Date.now();
    });

    document.addEventListener('touchend', (e) => {
      const endX = e.changedTouches[0].clientX;
      const duration = Date.now() - this.startTime;
      const distance = this.startX - endX;

      // Swipe rápido (< 300ms) e distância > 50px
      if (duration < 300 && Math.abs(distance) > 50) {
        this.handleTabSwipe(distance > 0 ? 'next' : 'prev');
      }
    });
  }

  handleTabSwipe(direction) {
    const activeTab = document.querySelector('.tabs-sticky button.active');
    if (!activeTab) return;

    const allTabs = Array.from(document.querySelectorAll('.tabs-sticky button'));
    const currentIndex = allTabs.indexOf(activeTab);
    let nextIndex;

    if (direction === 'next') {
      nextIndex = (currentIndex + 1) % allTabs.length;
    } else {
      nextIndex = (currentIndex - 1 + allTabs.length) % allTabs.length;
    }

    allTabs[nextIndex].click();
  }

  // ── Long-press para Menu ───────────────────────────────────────────────

  initLongPress() {
    document.addEventListener('touchstart', (e) => {
      if (e.target.hasAttribute('data-long-press')) {
        this.startTime = Date.now();
        this.longPressTimer = setTimeout(() => {
          this.showContextMenu(e.target, e.touches[0]);
        }, 500); // 500ms para long-press
      }
    });

    document.addEventListener('touchend', () => {
      if (this.longPressTimer) {
        clearTimeout(this.longPressTimer);
      }
    });

    document.addEventListener('touchmove', () => {
      if (this.longPressTimer) {
        clearTimeout(this.longPressTimer);
      }
    });

    // Fechar menu ao clicar fora
    document.addEventListener('click', (e) => {
      if (!e.target.closest('.long-press-menu')) {
        document.querySelectorAll('.long-press-menu.visible').forEach(m => {
          m.classList.remove('visible');
        });
      }
    });
  }

  showContextMenu(element, touch) {
    const menuId = element.getAttribute('data-long-press');
    const menu = document.getElementById(menuId);

    if (!menu) return;

    menu.classList.add('visible');
    menu.style.top = (touch.clientY - 10) + 'px';
    menu.style.left = (touch.clientX - 75) + 'px'; // Centralizar no dedo
  }

  // ── Scroll Behavior (mostrar/esconder bottom-actions) ──────────────────

  initScrollBehavior() {
    const bottomActions = document.querySelector('.bottom-actions');
    if (!bottomActions) return;

    let ticking = false;

    window.addEventListener('scroll', () => {
      if (!ticking) {
        window.requestAnimationFrame(() => {
          this.handleScroll(bottomActions);
          ticking = false;
        });
        ticking = true;
      }
    });

    // Mostrar ao toque na tela
    document.addEventListener('touchstart', () => {
      bottomActions.classList.add('visible');
    });
  }

  handleScroll(bottomActions) {
    const currentScrollY = window.scrollY;
    const isScrollingDown = currentScrollY > this.lastScrollY;

    if (isScrollingDown && currentScrollY > 100) {
      // Scrollando para baixo → esconder bottom-actions
      bottomActions.classList.remove('visible');
    } else {
      // Scrollando para cima → mostrar bottom-actions
      bottomActions.classList.add('visible');
    }

    this.lastScrollY = currentScrollY;
  }
}

// Inicializar quando DOM estiver pronto
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    new Gestures();
  });
} else {
  new Gestures();
}

