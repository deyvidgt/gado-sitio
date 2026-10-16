# Fotos e histórico dos animais (Google Drive) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Linha do tempo de fotos por animal com brinco, com os arquivos na pasta do Google Drive da família, envio pelo celular (inclusive offline) e exibição privada pelo site.

**Architecture:** `drive.py` (cliente REST mínimo do Drive via `requests`, OAuth com refresh token) ← `fotos.py` (regras; aba `Fotos` do Excel) ← `routes_fotos.py` (API JSON + proxy de imagem com cache em disco). No navegador, `static/fila_fotos.js` reduz a foto, tenta enviar e, sem sinal, guarda no IndexedDB.

**Tech Stack:** Flask, pandas/openpyxl (via `db.py`), `requests`, Pillow (opcional, miniaturas), IndexedDB/canvas no navegador, pytest.

**Spec:** `docs/superpowers/specs/2026-10-16-fotos-animais-design.md`

## Global Constraints

- Código, UI, mensagens e comentários em **português**; comentários explicam o porquê.
- **Não** adicionar `google-api-python-client`; só `requests` (já em `requirements.txt`).
- Aba `Fotos`, colunas exatamente nesta ordem: `ID Foto, Animal, Data, Tipo, Legenda, Principal, Drive ID, Enviado Por, Enviado Em, ID Envio`.
- `ID Foto` = `F` + 5 dígitos (`F00001`); validar com `^F\d{5}$` antes de usar em caminho.
- Tipos: `Perfil`, `Evolução`, `Ocorrência` (padrão na UI: `Evolução`). `Principal` = `"Sim"` ou `""`.
- Datas `dd/mm/aaaa`; `Enviado Em` = `dd/mm/aaaa HH:MM` (hora de `_agora()`).
- Limite do upload: **8 MB**; redução no celular: lado maior **1600 px**, JPEG ~0,82; miniatura ~**400 px**.
- Token em `<DATA_DIR>/drive_token.json` com chaves `client_id, client_secret, refresh_token, pasta_raiz`. Pasta raiz padrão: `1hVTxC--URXg1j3rylOYyRt1nSuC_vbUt`.
- Escopo OAuth: `https://www.googleapis.com/auth/drive`; operar só dentro da pasta raiz.
- Cache em `<DATA_DIR>/cache_fotos/`, limite ~200 MB (apaga os menos acessados).
- Nome no Drive: `AAAA-MM-DD_F00042.jpg`; subpasta `A0003 - Amarelo 21`, achada por `appProperties.animal`.
- Sem `confirm()`/`alert()` no JS. Rotas que alteram: login + CSRF. `/api/fotos` responde **sempre JSON** (401 `login`, 403 `csrf`).
- Testes **nunca** chamam o Google: Drive falso injetado. Rodar `python -m pytest` antes de cada commit.

## Review Focus

1. **Duas abas abertas / reenvio após timeout** — o mesmo `id_envio` chegando duas vezes (ou após upload sem gravação no Excel) deve gerar uma só linha e um só arquivo → Task 2 `test_orfao_no_drive_e_reaproveitado`, `test_reenvio_nao_duplica`.
2. **Excluir a única/principal foto** — o animal fica sem principal ou a mais recente assume; nunca duas principais → Task 2 `test_excluir_principal_promove_proxima`.
3. **Drive caído no meio do envio** — o celular recebe `erro: "drive"` (status 502) e mantém a foto na fila; nada gravado no Excel → Task 3 `test_api_drive_fora_nao_grava`.
4. **`id_foto` malicioso na URL** (`../`, inexistente) — 404, nunca toca disco fora de `cache_fotos/` → Task 3 `test_rota_id_invalido_404`.
5. **Arquivo que não é imagem ou > 8 MB** — recusado com `erro: "invalida"` e mensagem clara → Task 2 `test_recusa_nao_imagem`, `test_recusa_grande`.

---

### Task 1: `drive.py` — cliente do Google Drive + aba `Fotos`

**Files:**
- Create: `drive.py`
- Modify: `config.py` (após `COLUNAS_ANIMAIS`, ~linha 166), `db.py:66-73` (`_SCHEMA_ABAS`) e o ramo de arquivo novo de `inicializar()` (~linha 212)
- Modify: `.gitignore` (adicionar `drive_token.json`, `client_secret*.json`, `cache_fotos/`)
- Test: `tests/test_fotos.py`

**Interfaces:**
- Produces:
  - `config.COLUNAS_FOTOS: list[str]`, `config.TIPOS_FOTO = ["Perfil", "Evolução", "Ocorrência"]`, `config.DRIVE_PASTA_PADRAO = "1hVTxC--URXg1j3rylOYyRt1nSuC_vbUt"`
  - `drive.DriveErro(Exception)`
  - `drive.token_path() -> str` (`os.path.join(db.DATA_DIR, "drive_token.json")`)
  - `drive.configurado() -> bool`
  - `class drive.Drive:` com `pasta_animal(id_animal: str, nome: str) -> str`, `enviar(pasta_id: str, nome: str, conteudo: bytes, mime: str, props: dict) -> str`, `achar_por_envio(id_envio: str) -> str | None`, `baixar(file_id: str) -> bytes`, `lixeira(file_id: str) -> None`, `testar() -> tuple[bool, str]`
  - `drive.cliente() -> Drive | None` (None se não configurado; instância reaproveitada)
  - `drive.definir_cliente(c) -> None` (para injetar o falso nos testes)
  - `tests/test_fotos.py: class DriveFalso` com a mesma interface de `Drive`, guardando arquivos num dict, com `falhar: bool` que faz todo método levantar `DriveErro`

- [ ] **Step 1: Write the failing tests** em `tests/test_fotos.py`
  - `test_aba_fotos_criada_com_colunas`: após `db.inicializar()`, `db.carregar_aba("Fotos").columns.tolist() == COLUNAS_FOTOS` (aba vazia → ler cabeçalho com openpyxl se o DataFrame vier vazio).
  - `test_drive_nao_configurado_sem_token`: sem `drive_token.json` em `db.DATA_DIR`, `drive.configurado() is False` e `drive.cliente() is None`.
  - `test_drive_renova_token_e_envia` (com `monkeypatch` em `requests.post`/`requests.get` e um token gravado em `tmp_path` via `monkeypatch.setattr(drive, "token_path", ...)`): `Drive().enviar(...)` faz POST para `https://oauth2.googleapis.com/token` uma única vez em duas chamadas seguidas e depois POST para `https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart` com `Authorization: Bearer <tok>`; resposta HTTP 500 vira `DriveErro`.
  - Define `DriveFalso` no topo do arquivo.

- [ ] **Step 2: Run** `python -m pytest tests/test_fotos.py -v` → FAIL (`ModuleNotFoundError: drive` / `KeyError: 'Fotos'`).

- [ ] **Step 3: Implement**
  - `config.py`: as três constantes acima. `db.py`: `"Fotos": COLUNAS_FOTOS` em `_SCHEMA_ABAS` e `wb.create_sheet("Fotos").append(COLUNAS_FOTOS)` no arquivo novo.
  - `drive.py`: access token em memória com validade (`expires_in` − 60 s). Busca de pasta: `q = "'<raiz>' in parents and mimeType='application/vnd.google-apps.folder' and appProperties has {key='animal' and value='A0003'} and trashed=false"`. Upload multipart com `parents=[pasta_id]` e `appProperties=props`. `achar_por_envio` usa `appProperties has {key='id_envio' and value='...'}`. `lixeira` = `PATCH files/<id>` com `{"trashed": true}`. `testar` = `GET files/<raiz>?fields=name` → `(True, "Drive conectado — pasta <nome>")`. `timeout=30` em toda chamada; `requests.RequestException` e status ≥ 400 → `DriveErro("Não foi possível falar com o Google Drive: ...")`.

- [ ] **Step 4: Run** `python -m pytest tests/test_fotos.py -v` → PASS; `python -m pytest` → tudo PASS.

- [ ] **Step 5: Commit** `git add config.py db.py drive.py .gitignore tests/test_fotos.py && git commit -m "Fotos: cliente do Google Drive e aba Fotos"`

---

### Task 2: `fotos.py` — regras de negócio

**Files:**
- Create: `fotos.py`
- Test: `tests/test_fotos.py`

**Interfaces:**
- Consumes: `drive.cliente()`, `drive.DriveErro`, `db.carregar_aba`, `db.salvar_linha`, `db.reescrever_aba`, `animais.carregar`, `animais.por_id`, `animais.fmt_brinco`, `extensions._agora`, `db.fazer_backup` + `extensions._limpar_backups_antigos` (backup antes de reescrever; não importar de `routes_animais`, para evitar import circular).
- Produces:
  - `fotos.FotoInvalida(ValueError)`
  - `fotos.carregar() -> pd.DataFrame`
  - `fotos.enviar(id_animal: str, conteudo: bytes, data: str | None, tipo: str, legenda: str, enviado_por: str, id_envio: str) -> dict` → `{"duplicada": bool, "id_foto": str}`; levanta `FotoInvalida` ou `drive.DriveErro`
  - `fotos.listar(id_animal: str) -> list[dict]` (chaves: `id_foto, data, tipo, legenda, principal: bool, enviado_por, enviado_em`)
  - `fotos.principais() -> dict[str, str]` (`{id_animal: id_foto}`)
  - `fotos.por_id(id_foto: str) -> dict | None` (inclui `drive_id`, `animal`)
  - `fotos.definir_principal(id_foto: str) -> None`
  - `fotos.editar(id_foto: str, tipo: str, legenda: str, data: str) -> None`
  - `fotos.excluir(id_foto: str) -> None`
  - `fotos.e_imagem(conteudo: bytes) -> str | None` (devolve o mime: `image/jpeg`, `image/png`, `image/webp`, `image/heic`)

- [ ] **Step 1: Write the failing tests** (fixture autouse: `drive.definir_cliente(DriveFalso())`, limpa a aba `Fotos` e os backups criados; usa um animal real ou cadastra um com `animais.cadastrar`)
  - `test_envio_grava_linha_na_ordem`: `enviar(...)` → linha com `Animal == id`, `Tipo == "Evolução"`, `ID Foto == "F00001"`, `Drive ID` = id do falso; arquivo no falso tem nome `AAAA-MM-DD_F00001.jpg` e `props["id_envio"]`.
  - `test_primeira_foto_vira_principal` e `test_segunda_nao_tira_a_principal` (como excluir a principal sempre promove outra, "não ter principal" só acontece com zero fotos — a regra do *Perfil* da spec fica coberta pela da 1ª foto).
  - `test_reenvio_nao_duplica`: mesmo `id_envio` duas vezes → 1 linha, 1 arquivo, 2ª retorna `duplicada=True`.
  - `test_orfao_no_drive_e_reaproveitado`: arquivo já no falso com `id_envio` X e sem linha → `enviar(id_envio=X)` grava a linha sem novo upload.
  - `test_recusa_nao_imagem` (`b"%PDF-1.4..."` → `FotoInvalida`), `test_recusa_grande` (8 MB + 1 byte → `FotoInvalida`), `test_recusa_animal_inexistente`, `test_recusa_tipo_invalido`.
  - `test_drive_fora_nao_grava`: `falso.falhar = True` → `DriveErro`, aba sem linha.
  - `test_definir_principal_unica`: duas fotos, `definir_principal(2ª)` → exatamente uma `Principal == "Sim"`.
  - `test_excluir_principal_promove_proxima`: três fotos com datas diferentes, exclui a principal → a de data mais recente vira principal; arquivo no falso marcado como lixeira.
  - `test_listar_mais_recente_primeiro`.

- [ ] **Step 2: Run** `python -m pytest tests/test_fotos.py -v` → FAIL (`ModuleNotFoundError: fotos`).

- [ ] **Step 3: Implement** `fotos.py` com as assinaturas acima.
  - Assinaturas de imagem: JPEG `FF D8 FF`; PNG `89 50 4E 47`; WebP `RIFF....WEBP`; HEIC `....ftypheic|heix|mif1` (bytes 4–12).
  - Próximo `ID Foto` = maior número existente + 1 (não reaproveita).
  - Ordem dentro de `enviar`: checa duplicada na aba → valida → `achar_por_envio` → (`pasta_animal` + `enviar`) → `salvar_linha("Fotos", [...])` → `_cache_invalidar()` não é necessário (aba fora do cache de dados).
  - `editar`/`definir_principal`/`excluir` usam `reescrever_aba("Fotos", df[COLUNAS_FOTOS])`; `excluir` faz backup antes e chama `lixeira` (falha do Drive na lixeira **não** impede remover a linha; registra no log).

- [ ] **Step 4: Run** `python -m pytest tests/test_fotos.py -v` → PASS; `python -m pytest` → PASS.

- [ ] **Step 5: Commit** `git add fotos.py tests/test_fotos.py && git commit -m "Fotos: regras de envio, principal, edicao e exclusao"`

---

### Task 3: `routes_fotos.py` — API e imagens com cache

**Files:**
- Create: `routes_fotos.py`
- Modify: `app.py` (após `from routes_animais import *`, linha ~50: `from routes_fotos import *  # noqa: F401, F403`)
- Test: `tests/test_fotos.py`

**Interfaces:**
- Consumes: Task 2 inteira; `extensions.app`, `login_required`, `_validar_csrf`.
- Produces (rotas):
  - `POST /api/fotos` (form multipart: `id_animal, foto, tipo, legenda, data, id_envio, csrf_token`) → 200 `{"ok": true, "duplicada": bool, "id_foto": str}`; 400 `{"ok": false, "erro": "invalida", "msg": str}`; 401 `login`; 403 `csrf`; 502 `{"ok": false, "erro": "drive", "msg": str}`; 503 `{"ok": false, "erro": "drive", "msg": "Fotos não configuradas"}` se `drive.cliente()` é None.
  - `GET /fotos/<id_foto>` e `GET /fotos/<id_foto>/mini` → `image/jpeg`, `Cache-Control: private, max-age=604800`; 404 se id fora de `^F\d{5}$` ou inexistente.
  - `POST /fotos/<id_foto>/principal`, `POST /fotos/<id_foto>/editar` (form `tipo, legenda, data`), `POST /fotos/<id_foto>/excluir` → redirect para `ficha_animal` do animal com `flash`.
  - `routes_fotos.cache_dir() -> str`, `routes_fotos.limpar_cache(limite_bytes: int = 200 * 1024 * 1024) -> None`

- [ ] **Step 1: Write the failing tests** (usar a fixture `cliente` do conftest + `csrf_token` na sessão)
  - `test_api_sem_login_401`, `test_api_sem_csrf_403` (JSON, sem redirect).
  - `test_api_envia_e_duplicada` (JPEG mínimo válido gerado com Pillow ou bytes `FFD8FF...`) → 200, `ok`; 2º POST mesmo `id_envio` → `duplicada: true`.
  - `test_api_drive_fora_nao_grava` → 502 `erro == "drive"`, aba vazia.
  - `test_api_nao_configurado_503`: `drive.definir_cliente(None)` e sem token → 503.
  - `test_rota_imagem_usa_cache`: 1º GET baixa do falso (contador de `baixar` = 1); 2º GET não baixa de novo; cabeçalho `Cache-Control` contém `private`.
  - `test_rota_id_invalido_404`: `/fotos/..%2Fx`, `/fotos/F99999`, `/fotos/abc/mini` → 404.
  - `test_limpar_cache_respeita_limite`: cria 3 arquivos de 1 KB com `atime` distintos, `limpar_cache(2048)` → sobra os 2 mais recentes.

- [ ] **Step 2: Run** `python -m pytest tests/test_fotos.py -v` → FAIL (404 nas rotas).

- [ ] **Step 3: Implement** `routes_fotos.py`
  - `/mini`: se `PIL` importar, gerar miniatura 400 px (`Image.thumbnail`, `ImageOps.exif_transpose`, salvar JPEG 80) no cache; senão servir a original.
  - Após gravar no cache, chamar `limpar_cache()`; ordenar por `os.path.getatime`.
  - `excluir` também remove `<id>.jpg` e `<id>_mini.jpg` do cache.
  - `MAX_CONTENT_LENGTH` não é global: checar `request.content_length` > 9 MB → 400 `invalida` antes de ler.

- [ ] **Step 4: Run** `python -m pytest -v` → tudo PASS.

- [ ] **Step 5: Commit** `git add routes_fotos.py app.py tests/test_fotos.py && git commit -m "Fotos: API de envio e imagens com cache"`

---

### Task 4: Telas — ficha, lista e fila offline no celular

**Files:**
- Create: `static/fila_fotos.js`
- Modify: `templates/ficha_animal.html`, `templates/animais.html`, `templates/base.html` (incluir `fila_fotos.js` junto de `fila_visitas.js`; selo "N fotos na fila"), `routes_animais.py:77-95` (`animais()` passa `fotos_principais=fotos.principais()`), `routes_animais.py:204-221` (`ficha_animal` passa `fotos=fotos.listar(id_)`, `fotos_ativas=drive.configurado()`, `TIPOS_FOTO`), `static/fila_visitas.js` (abrir o banco na **versão 2** criando o store `fotos` se faltar — os dois scripts devem usar a mesma função de upgrade), `sw.js` (`CACHE_VERSION = "gado-v5"`; não interceptar `/fotos/`)
- Test: `tests/test_paginas.py`

**Interfaces:**
- Consumes: rotas da Task 3; `fotos.listar`, `fotos.principais`, `drive.configurado`.
- Produces: `window.FilaFotos = { enviar(idAnimal: string, arquivos: FileList, campos: {tipo, legenda, data}): Promise<void>, pendentes(idAnimal?: string): Promise<Array<{id_envio, id_animal, blob, tipo, legenda, data}>> }`; evento `document` `"fotos:atualizadas"` após cada envio bem-sucedido.

- [ ] **Step 1: Write the failing tests** em `tests/test_paginas.py`
  - `test_ficha_com_fotos_mostra_miniaturas`: com `DriveFalso` e uma foto enviada, GET `/animais/<id>` → 200 e contém `/fotos/F00001/mini` e o texto `📷 Tirar foto`.
  - `test_ficha_sem_drive_mostra_aviso`: `definir_cliente(None)`, sem token → 200 e contém `Fotos não configuradas`.
  - `test_lista_animais_com_principal`: GET `/animais` contém `/fotos/F00001/mini`.

- [ ] **Step 2: Run** `python -m pytest tests/test_paginas.py -v` → FAIL.

- [ ] **Step 3: Implement**
  - Ficha: foto principal no topo; seção "📷 Fotos" agrupada por data com etiqueta do tipo, legenda e "por <Enviado Por>"; `<input type="file" accept="image/*" capture="environment" multiple>`; mini formulário (Tipo, Legenda com 🎤 de `voz_campos.js`, Data = hoje); visualizador em overlay com ⭐/✏️/🗑️, exclusão com confirmação em dois toques dentro do overlay; pendentes da fila aparecem com `URL.createObjectURL(blob)` e "⏳ aguardando sinal".
  - Lista: `<img class="mini-redonda" loading="lazy">` quando houver principal; senão a bolinha atual.
  - `fila_fotos.js`: espelhar a estrutura de `fila_visitas.js` (store `fotos`, keyPath `id_envio`, reenvio no load/`online`/60 s, `TEMPO_LIMITE_MS = 60000`). Reduzir com `createImageBitmap` + canvas (1600 px, `toBlob("image/jpeg", 0.82)`); se falhar, enviar o original. Tirar da fila só em `ok: true`; em 401/403/502/503/rede manter; em 400 `invalida` remover e mostrar a `msg`.

- [ ] **Step 4: Run** `python -m pytest -v` → PASS. Depois, verificação manual numa cópia dos dados (`GADO_DATA_DIR` temporário, sem token): `python app.py`, abrir uma ficha, enviar uma foto → o servidor responde 503 e a foto aparece como "⏳ aguardando sinal"; com o DevTools em modo offline, a foto também entra na fila. (O envio real é testado na Task 5, Step 7.)

- [ ] **Step 5: Commit** `git add static/fila_fotos.js static/fila_visitas.js templates/ sw.js routes_animais.py tests/test_paginas.py && git commit -m "Fotos: ficha com linha do tempo, miniatura na lista e envio offline"`

---

### Task 5: Configuração do Drive, alerta e documentação

**Files:**
- Create: `configurar_drive.py`, `docs/FOTOS_DRIVE.md`
- Modify: `routes_usuarios.py` (rota `POST /configuracoes/testar-drive`; passar `drive_status` para `configuracoes.html` em `configuracoes()` ~linha 95), `templates/configuracoes.html` (cartão "📷 Fotos" antes de "💾 Backup dos Dados", ~linha 496), `alertas_whatsapp.py:montar_itens` (item urgente `"drive:erro"`, repetir 1 dia, só se `drive.configurado()` e `testar()` falhar), `CLAUDE.md` (linhas na tabela de arquitetura para `drive.py`, `fotos.py`, `routes_fotos.py`, `fila_fotos.js`), `CHANGELOG.md` (v4.4), `config.py` (`VERSAO`)
- Test: `tests/test_fotos.py`

**Interfaces:**
- Consumes: `drive.configurado`, `drive.cliente().testar()`, `drive.token_path()`.
- Produces: `configurar_drive.py` CLI — `python configurar_drive.py [--client-secret client_secret.json] [--pasta <id>] [--saida <caminho>]`; grava o JSON com as 4 chaves e imprime o resultado de `testar()`.

- [ ] **Step 1: Write the failing tests**
  - `test_configuracoes_mostra_cartao_fotos`: GET `/configuracoes` contém `📷 Fotos` e `não configurado` (sem token).
  - `test_testar_drive_com_falso_ok`: com `DriveFalso` → POST `/configuracoes/testar-drive` (com CSRF) redireciona e o flash contém `Drive conectado`.
  - `test_alerta_drive_quebrado`: token presente + `DriveFalso(falhar=True)` → `montar_itens()` contém item com `chave == "drive:erro"` e `urgente`.

- [ ] **Step 2: Run** `python -m pytest tests/test_fotos.py -v` → FAIL.

- [ ] **Step 3: Implement**
  - `configurar_drive.py`: fluxo OAuth *loopback* só com `http.server` + `webbrowser` + `requests` (sem libs do Google): `redirect_uri=http://127.0.0.1:<porta livre>`, `access_type=offline`, `prompt=consent`, escopo de Global Constraints, troca o `code` em `https://oauth2.googleapis.com/token`. Avisar se o `refresh_token` não vier.
  - `docs/FOTOS_DRIVE.md`: passo a passo da spec §8 (Cloud Console → Drive API → consentimento *Externo* → **Publicar app / Em produção** → credencial "App para computador" → `configurar_drive.py` logado como `nilsondavid45@gmail.com` → enviar `drive_token.json` para `~/gado-dados/` → Configurações → Testar).
  - Cartão em Configurações: status (`drive.configurado()` e, só quando o botão for clicado, `testar()`), link para o doc.

- [ ] **Step 4: Run** `python -m pytest -v` → tudo PASS (incluindo `test_calculos.py`).

- [ ] **Step 5: Verificar o PythonAnywhere** — conferir na lista de sites liberados (https://www.pythonanywhere.com/whitelist/) que `oauth2.googleapis.com` e `www.googleapis.com` estão permitidos. Se não estiverem, **parar e avisar o usuário** (plano gratuito bloquearia o recurso).

- [ ] **Step 6: Commit** `git add configurar_drive.py docs/FOTOS_DRIVE.md routes_usuarios.py templates/configuracoes.html alertas_whatsapp.py CLAUDE.md CHANGELOG.md config.py tests/test_fotos.py && git commit -m "v4.4: fotos dos animais no Google Drive"`

- [ ] **Step 7: Teste ponta a ponta com o Drive real** (depois que o usuário fizer a configuração): numa cópia dos dados (`GADO_DATA_DIR=<pasta temporária>` com o `drive_token.json`), `python app.py`, enviar uma foto pela ficha, conferir a subpasta `A000X - <brinco>` no Drive, a miniatura na lista e a exclusão indo para a lixeira.
