# Vários sítios — Fase 2: pasta por sítio, seletor e acesso — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cada sítio tem a sua pasta de dados; o usuário só entra nos sítios que pode, e troca de sítio num seletor no topo.

**Architecture:** `sitios.py` lê `<raiz>/sitios.json` e `ativar(slug)` aponta `db.DATA_DIR`/`db.ARQUIVO_PATH` para a pasta do sítio e aplica os donos dela (`config.aplicar_membros`). Um `before_request` pega uma trava do processo e ativa o sítio da sessão; o `teardown_request` solta. Assim os globais de hoje continuam valendo, um pedido por vez por processo. Arquivos da família (usuários, chave de sessão, bloqueios de login, `sitios.json`) ficam na raiz (`db.RAIZ`); o resto, por sítio.

**Tech Stack:** Python 3 / Flask / pytest; Jinja.

**Spec:** `docs/superpowers/specs/2026-10-25-varios-sitios-design.md`

## Global Constraints

- Sem `sitios.json`: um sítio só (`santo-antonio`, pasta = raiz) e todo usuário tem acesso — nada muda para quem usa hoje.
- `sitios.json` = `{"sitios": {slug: {"nome": str, "pasta": "sitios/<slug>"}}, "acesso": {login: [slug, …]}}`; o Santo Antonio é `{"pasta": ""}`. Com o arquivo, login que não está em `acesso` não entra em sítio nenhum (403).
- `slug` = `[a-z0-9-]{1,40}`; a pasta resolvida tem que ficar dentro da raiz.
- O sítio vem da sessão, mas é sempre conferido contra o acesso do usuário (sessão forjada não abre sítio alheio).
- Aviso de WhatsApp de um sítio só vai para quem tem acesso a ele.
- Cache (`extensions._cache`) separado por pasta.
- Tasks (backup, WhatsApp diário, resumo mensal) continuam só na raiz — são da fase 3.

## Review Focus

- **Sessão com `sitio` forjado** → usa o 1º sítio permitido. Teste em Task 2 (`test_sessao_forjada_nao_abre_sitio_alheio`).
- **Slug com `../`** → recusado. Teste em Task 1 (`test_slug_invalido`).
- **Aviso enviado depois da resposta** (call_on_close), quando outro pedido já trocou de sítio → usa o sítio em que foi guardado. Teste em Task 3 (`test_aviso_so_para_quem_tem_acesso`).
- **Mesmo cache nos dois sítios** → nome/estoque de um aparecendo no outro. Teste em Task 2 (`test_trocar_sitio_mostra_outros_dados`).
- **Exceção no meio do pedido** → a trava é solta (teardown). Teste em Task 2 (`test_erro_no_pedido_solta_a_trava`).

---

### Task 1: `sitios.py` e arquivos da raiz

**Files:** Create `sitios.py`; Modify `db.py` (`RAIZ`, `usar_pasta(pasta)`), `extensions.py` (`_usuarios_path`, `_chave_secreta`), `routes_usuarios.py` (`_usuarios_path`; `DATA_DIR` lido na hora), `routes_auth.py` (bloqueios na raiz), `alertas_whatsapp.py` (`carregar_usuarios` na raiz), `exportar.py`/`routes_importar_exportar.py` (`db.DATA_DIR` na hora); Test `tests/test_sitios.py`.

**Interfaces:** `sitios.PADRAO = "santo-antonio"`; `carregar() -> dict`; `pasta(slug) -> str` (ValueError se inválido/desconhecido); `sitios_do_usuario(login) -> list[str]`; `tem_acesso(login, slug) -> bool`; `nome(slug) -> str`; `ativar(slug) -> None`; `atual() -> str`.

- [x] Testes `test_sem_sitios_json_um_sitio_so`, `test_slug_invalido`, `test_acesso_por_login`, `test_ativar_troca_pasta_e_donos`; falhar; implementar; PASS; commit `Fase 2: sitios.json, pasta por sitio e arquivos da familia na raiz`.

### Task 2: Pedido dentro do sítio + seletor

**Files:** Modify `extensions.py` (`before_request`/`teardown_request` com trava; cache por pasta; context processor `sitios_menu`), `routes_auth.py` (rota `POST /sitio/trocar`), `templates/base.html` (seletor quando há 2+ sítios).

- [x] Testes `test_trocar_sitio_mostra_outros_dados`, `test_sem_acesso_nao_troca`, `test_sessao_forjada_nao_abre_sitio_alheio`, `test_usuario_sem_sitio_403`, `test_erro_no_pedido_solta_a_trava`; implementar; PASS; commit `Fase 2: cada pedido entra no sitio do usuario; seletor no topo`.

### Task 3: WhatsApp por sítio

**Files:** Modify `alertas_whatsapp.py` (item da fila guarda `sitio`; `enviar_para_familia(..., sitio=None)` filtra por `tem_acesso`), `routes_visitas._enviar_avisos_depois` (envia dentro da trava, no sítio guardado).

- [x] Teste `test_aviso_so_para_quem_tem_acesso`; implementar; PASS; commit `Fase 2: avisos do WhatsApp so para quem e do sitio`.

### Task 4: Documentação

- [x] CHANGELOG, CLAUDE.md (`sitios.py`, `sitios.json`, o que fica na raiz × no sítio, "um pedido por vez por processo"), spec (fase 2 entregue); PASS; commit `Docs: fase 2 dos varios sitios`.
