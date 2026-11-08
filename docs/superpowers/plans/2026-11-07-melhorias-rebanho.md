# Melhorias do Rebanho Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement Ponto de Abate, proactive IA alerts, intelligent input management, robust offline mode, and visual animal identification.

**Architecture:** Refactor existing modules (`ponto_corte.py`, `ia_modelos.py`, `insumos.py`) and centralize new logic in `routes_ia.py`. Improve JS sync layers for PWA.

**Tech Stack:** Python, Flask, Pandas, Scikit-learn, JavaScript (PWA).

**Spec:** `docs/superpowers/specs/2026-11-07-melhorias-rebanho-design.md`

## Global Constraints
- Keep CSS in `templates/base.html`.
- Use atomic `db` operations (trava + save).
- Maintain Portuguese UI and logging.

## Review Focus
1. IA model failure/timeout during dashboard load. (Task 1)
2. Inaccurate stock calculation leading to fake urgent alerts. (Task 3)
3. Data corruption in offline sync. (Task 4)
4. Ponto de Abate calculation edge cases (e.g., animal with no weight history). (Task 2)
5. Performance degradation on dashboard with too many concurrent alerts. (Task 1)

---

### Task 1: Estrutura Central de IA e Alertas

**Files:**
- Create: `routes_ia.py`
- Modify: `ia_modelos.py`
- Test: `tests/test_ia_integration.py`

**Interfaces:**
- Consumes: `ia_modelos.py` (inferência)
- Produces: `routes_ia.py` (API de alertas proativos)

- [ ] **Step 1: Create `routes_ia.py` to aggregate predictions**
- [ ] **Step 2: Add prediction endpoint for dashboard integration**
- [ ] **Step 3: Test dashboard alert aggregation**
- [ ] **Step 4: Commit**

### Task 2: Ponto de Abate Preditivo

**Files:**
- Modify: `ponto_corte.py`
- Modify: `templates/ponto_corte.html`
- Test: `tests/test_ponto_corte_relatorios.py`

**Interfaces:**
- Consumes: `calculos.py` (pesos e custos)
- Produces: `ponto_corte.py` (cálculos refinados)

- [ ] **Step 1: Update calculation logic in `ponto_corte.py`**
- [ ] **Step 2: Update UI template**
- [ ] **Step 3: Verify with tests**
- [ ] **Step 4: Commit**

### Task 3: Gestão de Insumos Inteligente

**Files:**
- Modify: `insumos.py`
- Modify: `routes_insumos.py`
- Test: `tests/test_insumos_estoque.py`

**Interfaces:**
- Consumes: `db.py` (dados), `gastos.py` (histórico)
- Produces: `insumos.py` (projeção de dias restantes)

- [ ] **Step 1: Implement projection logic in `insumos.py`**
- [ ] **Step 2: Integrate into alerts/dashboard**
- [ ] **Step 3: Validate consumption math**
- [ ] **Step 4: Commit**

### Task 4: Modo Campo (PWA) e Fotos

**Files:**
- Modify: `static/fila_visitas.js`, `static/fila_fotos.js`
- Modify: `fotos.py`
- Test: `tests/test_fotos.py`

**Interfaces:**
- Consumes: `fotos.py`
- Produces: `fila_visitas.js` (sync robusto)

- [ ] **Step 1: Improve sync reliability in `fila_visitas.js`**
- [ ] **Step 2: Ensure photo linkage in `fotos.py`**
- [ ] **Step 3: Verification**
- [ ] **Step 4: Commit**
