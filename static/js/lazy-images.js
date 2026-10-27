/**
 * Lazy Loading de Imagens v5.7
 * Usa Intersection Observer para carregar imagens conforme ficam visíveis
 *
 * Uso:
 * <img loading="lazy" data-src="URL" alt="desc" class="lazy-img">
 * ou
 * <img loading="lazy" src="placeholder.svg" data-src="URL" alt="desc">
 *
 * Fallback automático: imagens com loading="lazy" nativa em browsers modernos
 */

(function () {
  'use strict';

  // Detectar suporte a Intersection Observer
  if (!('IntersectionObserver' in window)) {
    console.warn('Intersection Observer não suportado. Carregando todas as imagens.');
    loadAllImages();
    return;
  }

  /**
   * Carregar todas as imagens (fallback para browsers antigos)
   */
  function loadAllImages() {
    const imgs = document.querySelectorAll('img[data-src]');
    imgs.forEach(img => {
      if (img.dataset.src) {
        img.src = img.dataset.src;
        img.removeAttribute('data-src');
      }
    });
  }

  /**
   * Carregar uma imagem individual
   * @param {HTMLImageElement} img
   */
  function loadImage(img) {
    if (!img.dataset.src) return;

    const src = img.dataset.src;
    const newImg = new Image();

    newImg.onload = () => {
      img.src = src;
      img.classList.add('lazy-loaded');
      img.removeAttribute('data-src');
      observer.unobserve(img);
    };

    newImg.onerror = () => {
      img.classList.add('lazy-error');
      console.warn(`Erro ao carregar imagem: ${src}`);
      observer.unobserve(img);
    };

    newImg.src = src;
  }

  /**
   * Intersection Observer: carregar quando ficar visível
   */
  const options = {
    root: null,
    rootMargin: '50px', // Carregar 50px antes de ficar visível
    threshold: 0,
  };

  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        loadImage(entry.target);
      }
    });
  }, options);

  /**
   * Observar todas as imagens com data-src
   */
  function initLazyLoad() {
    const imgs = document.querySelectorAll('img[data-src]');
    imgs.forEach((img) => {
      observer.observe(img);
    });

    // Se houver imagens adicionadas dinamicamente, observar também
    observeDynamicImages();
  }

  /**
   * Observar adição de imagens dinâmicas (ex.: fetch)
   */
  function observeDynamicImages() {
    const mutationObserver = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        mutation.addedNodes.forEach((node) => {
          if (node.nodeType === 1) { // Element node
            // Procurar imagens dentro do nó adicionado
            const imgs = node.querySelectorAll?.('img[data-src]');
            if (imgs) {
              imgs.forEach((img) => {
                observer.observe(img);
              });
            }
            // Se o nó em si é uma imagem
            if (node.tagName === 'IMG' && node.dataset.src) {
              observer.observe(node);
            }
          }
        });
      });
    });

    mutationObserver.observe(document.body, {
      childList: true,
      subtree: true,
    });
  }

  /**
   * Recarregar uma imagem específica (ex.: após erro de conexão)
   * @param {HTMLImageElement} img
   */
  window.reloadLazyImage = function (img) {
    if (!img || !img.dataset.src) return;
    img.classList.remove('lazy-error');
    observer.observe(img);
  };

  /**
   * Forçar carregamento de todas as imagens lazy
   */
  window.loadAllLazyImages = function () {
    const imgs = document.querySelectorAll('img[data-src]');
    imgs.forEach((img) => {
      loadImage(img);
    });
  };

  // Inicializar quando o DOM estiver pronto
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initLazyLoad);
  } else {
    initLazyLoad();
  }

  // Expor função de carregamento para uso em scripts inline
  window.lazyLoadInit = initLazyLoad;
})();

/**
 * CSS correspondente (adicionar a design-tokens.css ou arquivo separado):
 *
 * img[data-src] {
 *   background: var(--color-neutral-200);
 *   animation: shimmer 2s infinite;
 * }
 *
 * img.lazy-loaded {
 *   animation: fadeIn 0.3s ease-in;
 * }
 *
 * img.lazy-error {
 *   opacity: 0.5;
 *   filter: grayscale(1);
 * }
 *
 * @keyframes shimmer {
 *   0% { background: var(--color-neutral-200); }
 *   50% { background: var(--color-neutral-300); }
 *   100% { background: var(--color-neutral-200); }
 * }
 *
 * @keyframes fadeIn {
 *   from { opacity: 0; }
 *   to { opacity: 1; }
 * }
 */
