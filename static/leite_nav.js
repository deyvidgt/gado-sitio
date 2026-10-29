(() => {
  const nav = document.querySelector('[data-leite-back]');
  if (!nav || window.innerWidth > 768 || !window.PointerEvent) return;

  const hint = document.querySelector('[data-leite-swipe-hint]');
  const edge = 24;
  const threshold = 72;
  let startX = 0;
  let startY = 0;
  let tracking = false;
  let eligible = false;
  let dirtyForms = [];

  const isInteractive = (target) => {
    if (!(target instanceof Element)) return true;
    if (target.closest('input, textarea, select, button, a, [contenteditable="true"], [data-map], .leaflet-container')) return true;
    const scrollable = target.closest('[style*="overflow-x"], [data-horizontal-scroll]');
    return Boolean(scrollable && scrollable.scrollWidth > scrollable.clientWidth);
  };

  const captureFormState = () => {
    dirtyForms = Array.from(document.querySelectorAll('form')).map((form) => ({
      form,
      values: Array.from(form.elements).map((field) => field.type === 'checkbox' || field.type === 'radio' ? field.checked : field.value)
    }));
  };

  const hasDirtyForm = () => dirtyForms.some(({form, values}) =>
    Array.from(form.elements).some((field, index) => {
      const value = field.type === 'checkbox' || field.type === 'radio' ? field.checked : field.value;
      return value !== values[index];
    })
  );

  const showHint = (visible) => {
    if (!hint) return;
    hint.hidden = !visible;
  };

  captureFormState();

  document.addEventListener('pointerdown', (event) => {
    if (event.pointerType === 'mouse' || window.innerWidth > 768 || event.clientX > edge || isInteractive(event.target)) return;
    startX = event.clientX;
    startY = event.clientY;
    tracking = true;
    eligible = false;
  }, {passive: true});

  document.addEventListener('pointermove', (event) => {
    if (!tracking) return;
    const dx = event.clientX - startX;
    const dy = Math.abs(event.clientY - startY);
    if (dx < 0 || dy > Math.abs(dx)) {
      tracking = false;
      showHint(false);
      return;
    }
    eligible = dx >= threshold && !hasDirtyForm();
    showHint(eligible);
  }, {passive: true});

  document.addEventListener('pointerup', (event) => {
    if (!tracking) return;
    const valid = eligible && event.clientX - startX >= threshold && !hasDirtyForm();
    tracking = false;
    eligible = false;
    showHint(false);
    if (valid) window.location.href = nav.dataset.leiteBackUrl;
  }, {passive: true});

  document.addEventListener('pointercancel', () => {
    tracking = false;
    eligible = false;
    showHint(false);
  }, {passive: true});
})();
