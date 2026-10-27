/**
 * Dark Mode Toggle (v5.7)
 * - Suporta prefers-color-scheme
 * - Permite toggle manual
 * - Persiste preferência em localStorage
 */

class DarkMode {
  constructor() {
    this.key = 'theme-preference';
    this.systemPreference = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    this.userPreference = localStorage.getItem(this.key);
    this.currentTheme = this.userPreference || this.systemPreference;
    
    this.init();
  }

  init() {
    // Aplicar tema ao carregar
    this.applyTheme(this.currentTheme);
    
    // Criar botão toggle
    this.createToggleButton();
    
    // Ouvir mudanças de preferência do sistema
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
      if (!this.userPreference) {
        this.applyTheme(e.matches ? 'dark' : 'light');
      }
    });
  }

  applyTheme(theme) {
    this.currentTheme = theme;
    
    if (theme === 'dark') {
      document.documentElement.setAttribute('data-theme', 'dark');
    } else {
      document.documentElement.removeAttribute('data-theme');
    }
    
    this.updateToggleButton();
  }

  toggle() {
    const newTheme = this.currentTheme === 'dark' ? 'light' : 'dark';
    this.userPreference = newTheme;
    localStorage.setItem(this.key, newTheme);
    this.applyTheme(newTheme);
  }

  createToggleButton() {
    // Verificar se já existe
    if (document.querySelector('.dark-mode-toggle')) return;
    
    const button = document.createElement('button');
    button.className = 'dark-mode-toggle';
    button.setAttribute('aria-label', 'Toggle dark mode');
    button.setAttribute('title', 'Dark mode');
    button.innerHTML = this.currentTheme === 'dark' ? '☀️' : '🌙';
    
    button.addEventListener('click', () => {
      this.toggle();
    });
    
    document.body.appendChild(button);
  }

  updateToggleButton() {
    const button = document.querySelector('.dark-mode-toggle');
    if (button) {
      button.innerHTML = this.currentTheme === 'dark' ? '☀️' : '🌙';
    }
  }
}

// Inicializar
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    new DarkMode();
  });
} else {
  new DarkMode();
}

