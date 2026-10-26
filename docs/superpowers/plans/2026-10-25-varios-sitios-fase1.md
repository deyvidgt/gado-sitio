# Vários sítios — Fase 1: donos configuráveis — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Os donos (sócios) do sítio passam a vir do `sitio_config.json` da pasta de dados; sem configuração, continuam Geane/Deyvid/Nilson e o Santo Antonio não muda em nada.

**Architecture:** `config.py` lê `membros` do `sitio_config.json` ao importar (pasta resolvida por `pasta_dados.py`, sem depender de `db`) e gera `MEMBROS`, nomes, emojis, cores, logins e as colunas por dono de Compras/Vendas. Os 15 módulos que fazem `from config import MEMBROS` continuam iguais; só os pontos com "Mae/Deyvid/Nilson" ou "terços" fixos são generalizados (partes iguais, resto para o último dono — igual ao "resto p/ Nilson" de hoje).

**Tech Stack:** Python 3 / Flask / pandas / openpyxl / pytest; Jinja.

**Spec:** `docs/superpowers/specs/2026-10-25-varios-sitios-design.md`

## Global Constraints

- Santo Antonio sem `membros` no `sitio_config.json`: colunas, nomes de campo do formulário (`qtd_mae`, `qtd_deyvid`, `qtd_nilson`) e todos os números **idênticos** aos de hoje.
- `membros` = lista de `{"chave", "nome", "emoji", "cor", "logins"}`; `chave` só letras sem espaço (vira nome de coluna `Qtd <chave>` e campo `qtd_<chave minúscula>`); de 2 a 8 donos; chaves e cores únicas; cor de `CORES_BRINCO`. Inválido → padrão + `logging.error`.
- Colunas por dono ficam na **mesma posição** de hoje em Compras/Vendas (o arquivo de um sítio novo nasce assim). Arquivo existente cujas colunas `Qtd <chave>` não batem com os donos configurados → `db.inicializar` levanta `RuntimeError` com mensagem clara (trocar donos só em sítio novo) — nunca grava desalinhado.
- Invariantes contábeis (CLAUDE.md) com 2, 3 e 4 donos.
- Testes nunca enviam WhatsApp e só gravam na cópia temporária.

## Review Focus

- **`sitio_config.json` sem `membros` ou com JSON quebrado** → padrão de 3. Teste em Task 1 (`test_config_invalida_usa_padrao`).
- **Donos configurados ≠ colunas do arquivo existente** → erro claro, nada gravado. Teste em Task 1 (`test_arquivo_com_outros_donos_recusa`).
- **Rateio com resto** (ex.: 10 cabeças em 4 donos) → 2/2/2/4, soma fecha. Teste em Task 2 (`test_partes_iguais_resto_no_ultimo`).
- **Venda de 4 donos com valor que não divide** → soma dos valores por dono == valor total. Teste em Task 3 (`test_venda_quatro_donos_grava_colunas`).
- **Login que não é de nenhum dono** (ex.: `nd`) → `_membro_logado` devolve "". Teste em Task 3 (`test_login_membro_configurado`).

---

### Task 1: Donos lidos da configuração

**Files:**
- Create: `pasta_dados.py` (move `_resolver_data_dir` de `db.py`; `db` reexporta o nome)
- Modify: `config.py`, `db.py` (`inicializar`)
- Test: `tests/test_membros.py`

**Interfaces:**
- Produces (em `config`): `MEMBROS_PADRAO: list[dict]`; `ler_membros(cfg: dict | None) -> list[dict]`; `colunas_compras(chaves: list[str]) -> list[str]`; `colunas_vendas(chaves: list[str]) -> list[str]`; `aplicar_membros(lista: list[dict]) -> None` (troca **no lugar** `MEMBROS`, `NOMES_MEMBROS`, `EMOJIS_MEMBROS`, `CORES_BRINCO_PADRAO`, `LOGIN_MEMBRO`, `COLUNAS_COMPRAS`, `COLUNAS_VENDAS`, para quem importou por nome ver a troca); `LOGIN_MEMBRO: dict[str, str]` (login minúsculo → chave).
- Test fixture (em `tests/conftest.py`): `membros_teste(n)` → aplica `n` donos `A`,`B`,`C`,`D`… e restaura o padrão no fim.

- [ ] Testes: `test_padrao_igual_ao_de_hoje` (colunas de Compras/Vendas == as listas literais de hoje); `test_quatro_donos_gera_colunas` (`Qtd D` logo depois de `Qtd C`; `Resultado D (R$)` antes de `CMP no momento (R$)`); `test_config_invalida_usa_padrao` (chave com espaço, cor repetida, 1 dono, 9 donos); `test_arquivo_com_outros_donos_recusa`.
- [ ] Rodar e ver falhar; implementar; `python -m pytest -q` PASS; commit `Fase 1: donos do sitio lidos do sitio_config.json`.

### Task 2: Contas em partes iguais

**Files:** Modify `calculos.py` (`dividir_cotas`, `calcular_estoque_por_membro`, `_ratear_perda_tercos`); Test `tests/test_membros.py`.

**Interfaces:** `dividir_cotas(cabecas: int, *cotas: int) -> tuple[int, ...]` com `len(MEMBROS)` itens (cotas faltando = 0; os chamadores atuais com 3 posicionais continuam valendo).

- [ ] Testes: `test_partes_iguais_resto_no_ultimo`; `test_invariantes_com_n_donos` parametrizado em 2, 3, 4 (cenário com compra, gasto, venda com cotas, venda sem cotas, morte com e sem "Perda De", nascimento sem dono) usando `checar_invariantes` de `test_calculos.py`; existentes de `dividir_cotas` seguem passando.
- [ ] Implementar; PASS; smoke: `foto_numeros.py` nos dados reais igual ao de antes; commit `Fase 1: rateio em partes iguais para qualquer numero de donos`.

### Task 3: Gravação, telas, voz e WhatsApp

**Files:** Modify `routes_registros.py` (`gravar_compra`, `editar_compra`, `_salvar_venda`, listas), `templates/form_compra.html`, `templates/lista.html`, `exportar.py`, `routes_importar_exportar.py`, `comando_voz.py` (`_DONOS` gerado dos nomes/logins + apelidos atuais; cotas do form; "entre os três"), `alertas_whatsapp.py` e `routes_animais._membro_logado` (usam `config.LOGIN_MEMBRO`), `extensions.py`/`routes_usuarios.py` (`donos` padrão = nomes unidos por " · "), textos "os três" → "todos os donos" em `form_manejo.html`, `ajuda.html`.

- [ ] Testes: `test_venda_quatro_donos_grava_colunas` (arquivo novo em pasta temporária com 4 donos; POST de compra e venda; linhas lidas por nome batem); `test_paginas_com_quatro_donos` (páginas GET principais sem 500); `test_login_membro_configurado`.
- [ ] Implementar; PASS; commit `Fase 1: formularios, voz e WhatsApp com os donos do sitio`.

### Task 4: Documentação

- [ ] CHANGELOG [Não lançado] (donos configuráveis; "Planejado: peso estimado por foto/fita"), CLAUDE.md (`pasta_dados.py`, `membros` no `sitio_config.json`, regra "trocar donos só em sítio novo"), spec com fase 1 entregue. PASS; commit `Docs: fase 1 dos varios sitios`.
