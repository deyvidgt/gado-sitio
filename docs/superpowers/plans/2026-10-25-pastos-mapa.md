# Pastos com mapa — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Pastos desenhados no mapa, com área, onde o gado está, dias e lotação.

**Architecture:** `pastos.py` (aba `Pastos`, área esférica, movimentação no Manejo, situação de cada pasto); `routes_pastos.py` + `templates/pastos.html` (Leaflet + Leaflet.draw via cdnjs).

**Tech Stack:** Python 3 / Flask / pandas / pytest; Leaflet 1.9.4, Leaflet.draw 1.0.4 (cdnjs).

**Spec:** `docs/superpowers/specs/2026-10-25-pastos-mapa-design.md`

## Global Constraints

- `COLUNAS_PASTOS = ["ID", "Nome", "Área (ha)", "Contorno", "Cor", "Ativo", "Observações", "Criado Por"]`; `COLUNAS_MANEJO` + `"Pasto"` no fim.
- `UA_KG = 450`. Área: raio da Terra 6 378 137 m, polígono GeoJSON (lon, lat); 0,01 a 100 000 ha.
- Nome 1–40 letras, único entre os ativos. Contorno: 3 a 500 pontos, lon/lat válidos.
- Tipo da movimentação: `"Movimentação de Pasto"` (já existe em `TIPOS_MANEJO`).

## Review Focus

- **Contorno forjado** (texto que não é polígono, lat 200) → recusado. Teste `test_contorno_invalido`.
- **Rebanho todo depois de um animal movido** → o animal volta com o rebanho. Teste `test_rebanho_todo_mais_recente_vence`.
- **Animal vendido** → sai da contagem do pasto. Teste `test_vendido_sai_do_pasto`.
- **Pasto excluído** → some do mapa; animais nele ficam "sem pasto". Teste `test_excluir_pasto`.
- **Sem peso nenhum** → UA pelo padrão 450 kg, marcado como estimado. Teste `test_ua_sem_peso`.

---

### Task 1: `pastos.py`

**Interfaces:** `area_ha(geojson: dict) -> float`; `carregar() -> DataFrame`; `criar(nome, contorno_json, criado_por="") -> str`; `editar(id_, nome=None, contorno_json=None)`; `excluir(id_)`; `mover(pasto_id, data, refs: list[str] | None, qtd: int, responsavel="")` (refs None = rebanho todo); `situacao(df_pastos, df_animais, df_man, estoque, peso_medio) -> dict[id, {cab, ua, ua_ha, dias, estimado}]` + chave `None` (sem pasto).

- [x] Testes: `test_area_quadrado_de_1km`, `test_contorno_invalido`, `test_criar_e_nome_repetido`, `test_mover_e_situacao`, `test_rebanho_todo_mais_recente_vence`, `test_vendido_sai_do_pasto`, `test_excluir_pasto`, `test_ua_sem_peso`; implementar; PASS; commit.

### Task 2: Telas

**Files:** Create `routes_pastos.py`, `templates/pastos.html`; Modify `app.py` (importar rotas), `templates/base.html` (menu 🗺️ Pastos).

- [x] Testes: `test_pagina_pastos_abre`, `test_criar_pela_tela`, `test_mover_pela_tela`, `test_mover_brinco_errado`; teste no navegador (desenhar, salvar, ver rótulo); PASS; commit.

### Task 3: Documentação

- [x] CHANGELOG, CLAUDE.md, Ajuda, spec entregue; PASS; commit.
