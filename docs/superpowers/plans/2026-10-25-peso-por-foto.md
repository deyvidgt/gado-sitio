# Peso estimado por foto — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Estimar o peso pela foto de lado com referência, calibrado pelas pesagens de balança, sem misturar com o GMD.

**Architecture:** `peso_foto.py` (fórmula, validação, calibração, gravação no Manejo). A tela `templates/peso_foto.html` mede na foto (canvas, JS) e manda só os cm; o servidor recalcula e valida. `pesagem.todas` ganha `estimados`.

**Tech Stack:** Python 3 / Flask / pandas / pytest; JS puro (canvas).

**Spec:** `docs/superpowers/specs/2026-10-25-peso-por-foto-design.md`

## Global Constraints

- `FATOR_PERIMETRO = 2.6`; `CONST_SCHAEFFER = 10838`; comprimento 60–260 cm; profundidade 25–110 cm; referência 20–500 cm.
- Calibração: pares a ≤15 dias, mínimo 3, mediana, limite 0,7–1,3.
- Tipo no Manejo: `"Peso Estimado"`; `Pesos` guarda o bruto.
- Faixa mostrada: ±15% sem calibração, ±10% com.

## Review Focus

- **Estimativa não entra no GMD** → `pesagem.todas` sem ela. Teste `test_estimado_fora_do_gmd`.
- **Medidas absurdas mandadas direto ao servidor** → 400/flash, nada gravado. Teste `test_medidas_absurdas_recusadas`.
- **Poucos pares** → sem calibração (fator 1). Teste `test_calibracao_precisa_de_3_pares`.
- **Animal vendido/morto** → não estima. Teste `test_animal_nao_vivo`.
- **Outro sítio** → animal de outro sítio não existe aqui (já garantido pela pasta).

---

### Task 1: Cálculo, calibração e gravação

**Files:** Create `peso_foto.py`; Modify `pesagem.py` (`todas(df_man, estimados=False)`); Test `tests/test_peso_foto.py`.

**Interfaces:** `estimar_bruto(comp_cm, prof_cm) -> float`; `validar(comp_cm, prof_cm, ref_cm) -> tuple[float, float, float]` (ValueError); `fator_calibracao(df_man) -> tuple[float, int]`; `registrar(id_, comp_cm, prof_cm, ref_cm, data, responsavel) -> float` (bruto); `ultima_estimativa(id_, df_man) -> dict | None` (`kg`, `bruto`, `data`, `fator`, `n_pares`, `faixa_pct`).

- [x] Testes: `test_formula_schaeffer`, `test_medidas_absurdas_recusadas`, `test_calibracao_precisa_de_3_pares`, `test_calibracao_mediana_e_limite`, `test_estimado_fora_do_gmd`; implementar; PASS; commit.

### Task 2: Tela e ficha

**Files:** Create `templates/peso_foto.html`; Modify `routes_animais.py` (GET/POST `/animais/<id_>/peso-foto`), `templates/ficha_animal.html` (botão + linha "estimado por foto" no cartão Peso).

- [x] Testes: `test_pagina_peso_foto_abre`, `test_salvar_estimativa`, `test_animal_nao_vivo`, `test_ficha_mostra_estimativa`; implementar; PASS; commit.

### Task 3: Documentação

- [x] CHANGELOG, CLAUDE.md, Ajuda (passo a passo de como tirar a foto), spec entregue; PASS; commit.
