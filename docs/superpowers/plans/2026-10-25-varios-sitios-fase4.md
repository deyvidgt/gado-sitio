# Vários sítios — Fase 4: painel da Família — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Uma página "👨‍👩‍👧 Família" mostra, lado a lado e somados, os números de todos os sítios.

**Architecture:** Rota `/familia` em `routes_dashboard.py`: dentro do pedido (trava já pega), entra em cada sítio com `sitios.ativar`, lê `_get_resumo_cache()` (cache por pasta) e volta ao sítio do usuário no fim. Só leitura.

**Tech Stack:** Python 3 / Flask / pytest; Jinja.

**Spec:** `docs/superpowers/specs/2026-10-25-varios-sitios-design.md` (Decisões: todos da família veem os sítios somados)

## Global Constraints

- Qualquer login com acesso a ≥1 sítio vê todos os sítios no painel (decisão de 2026-10-25); sem acesso a nenhum → 403 (já é do `before_request`).
- Campos por sítio: nome, donos, `estoque`, `capital_imobilizado`, `total_vend`, `perdas`, `resultado_total`; total = soma.
- Link no menu só quando há 2+ sítios.
- Erro ao ler um sítio → linha "não deu para ler" e os outros aparecem; total sem ele, com aviso.
- No fim do pedido o sítio ativo e os donos voltam aos do usuário.

## Review Focus

- **Painel aberto por quem só tem o Santo Antonio** → vê os dois, e a próxima página continua no Santo Antonio. Teste `test_familia_soma_e_volta_ao_sitio`.
- **Um sítio com planilha quebrada** → página abre. Teste `test_familia_sitio_com_erro`.
- **Um sítio só** → sem link no menu; a página funciona. Teste `test_familia_um_sitio`.

---

### Task 1: Painel da Família

**Files:** Modify `routes_dashboard.py` (rota `familia`), `extensions.py` (`varios_sitios` no context processor), `templates/base.html` (link); Create `templates/familia.html`; Test `tests/test_sitios.py`.

- [ ] Testes acima; implementar; PASS; commit `Fase 4: painel da familia somando os sitios`.

### Task 2: Documentação

- [ ] CHANGELOG, CLAUDE.md, Ajuda, spec (fases 1–4 entregues); PASS; commit `Docs: fase 4 dos varios sitios`.
