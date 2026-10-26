# CLAUDE.md — Guia do Projeto

Orientações para o Claude Code (e humanos) trabalharem neste repositório.

## O que é

Sistema web de **gestão de gado** da família (Sítio Santo Antonio). App **Flask** em
português, com PWA, que controla compras, gastos, vendas, manejo e visitas ao sítio,
além de cálculos financeiros do rebanho e relatórios/PDF.

**Donos/membros:** `Mae` (Geane), `Deyvid`, `Nilson` — padrão de `config.py: MEMBROS_PADRAO`;
outro sítio define os seus em `"membros"` no `sitio_config.json` (só ao criar o sítio:
`db.inicializar` recusa arquivo com colunas de outros donos). Nunca escreva "Mae"/"terços"
fixo: use `MEMBROS`, `partes_iguais()` e `dividir_cotas(cab, *cotas)`. O CLI antigo
(`main.py`/`registros.py`) só funciona com os três padrão.

## Como rodar

```bash
# Desenvolvimento local (Windows/Linux)
python app.py            # sobe em http://localhost:5000 e abre o navegador

# Produção: wsgi.py (PythonAnywhere). Dados ficam FORA do repo (ver abaixo).
```

- **Senha padrão** de todos os usuários: `sitio2025` (hashes em `config.py`).
- `GADO_SECRET_KEY` e `GADO_DATA_DIR` são variáveis de ambiente opcionais.

## ⚠️ Dados / banco (LER ANTES DE MEXER)

- Os dados ficam em **`gado_familia.xlsx`** (abas: Compras, Gastos, Vendas, Manejo, Visitas, Animais, Fotos).
- Em produção o arquivo mora em **`~/gado-dados/`**, **fora do Git**, para o `git pull`
  nunca apagar dados. Resolução do caminho: `db.py: _resolver_data_dir()`
  (ordem: `GADO_DATA_DIR` → `~/gado-dados/` → pasta do .exe → pasta do script).
- **NUNCA** alterar/reordenar colunas existentes. Colunas novas vão **sempre no final**
  de `COLUNAS_*` em `config.py`; o `db.inicializar()` migra as abas existentes
  adicionando as colunas que faltam, sem tocar nos dados.
- `salvar_linha(aba, lista)` grava **posicionalmente** — a ordem da lista tem que bater
  com a ordem das colunas da aba.
- Ao testar algo que grava, **teste numa cópia** do `.xlsx` (ex.: `GADO_DATA_DIR=/tmp/...`),
  nunca no arquivo real.

## Vários sítios (v5.0)

- **Raiz** (`db.RAIZ`, ~/gado-dados/): `usuarios.json`, `secret_key.txt`,
  `login_bloqueios.json`, `sitios.json` — da família toda.
- **Pasta do sítio** (`db.DATA_DIR`, a raiz para o Santo Antonio, `sitios/<slug>/` para os
  outros): planilha, `sitio_config.json` (com `membros`), backups, fotos, Drive, filas.
- Cada pedido entra no sítio da sessão (conferido contra o acesso do login) no
  `before_request` de `extensions.py`, com uma trava: **um pedido por vez por processo**.
  Código novo que roda fora do pedido (call_on_close, thread) tem que guardar o slug e
  fazer `sitios.ativar(slug)` dentro de `extensions._trava_sitio` (ver
  `routes_visitas._enviar_avisos_depois`). Nunca `from db import DATA_DIR` no topo do módulo.
- Cache separado por pasta (`extensions._chave_cache`).
- **Admin** (`sitios.e_admin`): sem `sitios.json` todos; com ele, `"admins"` ou quem tem
  acesso ao 1º sítio. Rota que mexe em usuários/sítios chama `_so_admin()`; lista de
  pessoas para não-admin passa por `_usuarios_visiveis()` (só quem é do sítio atual).
- **Tasks** (backup, WhatsApp, resumo mensal) fazem `for slug in sitios.cada_sitio()` e
  mandam `sitio=slug` no `enviar_para_familia`; erro num sítio não para os outros.
- **Painel da Família** (`/familia`, `routes_dashboard.familia`): dentro do pedido entra
  em cada sítio (`sitios.ativar`) e volta ao do usuário no `finally` — o padrão para
  qualquer tela que precise ler mais de um sítio.

## Arquitetura

| Arquivo | Papel |
|---|---|
| `app.py` | Ponto de entrada; importa `extensions.app` e registra todas as rotas |
| `extensions.py` | App Flask, sessão, CSRF, cache de dados/resumo, helpers (`fmt_brl`, `fmt_data`, `parse_valor`) |
| `config.py` | Constantes: colunas das abas, tipos, cores, secret key. **Donos** (`MEMBROS`, nomes, emojis, cores, `LOGIN_MEMBRO`) vêm de `"membros"` no `sitio_config.json` (padrão: Geane/Deyvid/Nilson); as colunas por dono de Compras/Vendas são geradas deles (`colunas_compras`/`colunas_vendas`). `aplicar_membros` troca no lugar |
| `sitios.py` | Vários sítios (v5.0 fase 2): `<raiz>/sitios.json` (`sitios` → nome/pasta, `acesso` → login → slugs); `ativar(slug)` aponta `db.DATA_DIR`/`ARQUIVO_PATH` e os donos para o sítio. Sem o arquivo: um sítio só (a raiz) e todos entram |
| `pasta_dados.py` | `_resolver_data_dir()` (GADO_DATA_DIR → ~/gado-dados → .exe → script); separado do `db` porque o `config` precisa dele |
| `db.py` | Leitura/escrita/backup do Excel e **migração de colunas** |
| `calculos.py` | **Motor financeiro** (CMP, GPCab, CTCab, resultado por membro, resumo) |
| `routes_*.py` | Rotas por área (registros, visitas, relatórios, api, usuários, auth…) |
| `relatorios.py` / `exportar.py` | Geração de relatórios e exportação |
| `alertas_whatsapp.py` | Notificações via CallMeBot: Task diária só com urgentes (sem repetir), resumo semanal na segunda com "Na semana"; preferências por pessoa (`receber` em `usuarios.json`: urgentes/semanal/visita/eventos/mensal/valores); fila de avisos (`avisos_pendentes.json`) de visita e de Morte/Nascimento (`avisar_manejo`). Testes nunca enviam (fixture autouse no `conftest`) |
| `saude.py` | Calendário sanitário (Triângulo Mineiro): vacina por tipo, campanha de brucelose, vermifugação 5-7-9 — fonte única p/ painel, calendário e WhatsApp |
| `backup_automatico.py` | Backup diário (Task do PythonAnywhere) |
| `resumo_mensal.py` | Resumo do mês no WhatsApp no dia 1º (Task diária; `--teste` só mostra) |
| `insumos.py` | Estoque de Sal/Proteinado/Ração: sacos em estoque contados nas visitas + compras (Gastos: Produto/Qtd Sacos) → consumo e "acaba em" (painel e WhatsApp) |
| `animais.py` | Cadastro individual por brinco (aba `Animais`): cor por dono, nº 01–99 reaproveitado, ID `A0001` liga o histórico (`Brincos` em Manejo/Vendas = "Amarelo 21 #A0003"); baixa, brucelose por animal |
| `pesagem.py` | Peso por animal (v4.6): coluna `Pesos` da linha "Pesagem" do Manejo (`"Amarelo 21 #A0003: 320 kg"`; legado: peso na Descrição) → último peso, @, GMD; página `/animais/pesagem` |
| `comando_voz.py` | Comando de voz por regras: `analisar(texto)` → intenção; `montar(intenção, ctx)` confere nos dados. Rotas em `routes_animais.py` (`/voz`, `/api/voz/*`) |
| `static/voz_campos.js` | Prefill de formulário por `?prefill=1&campo=valor` e 🎤 de ditado nos campos de texto |
| `drive.py` | Cliente mínimo do Google Drive (só `requests`, OAuth com refresh token em `<dados>/drive_token.json`); só opera dentro da pasta raiz |
| `fotos.py` / `routes_fotos.py` | Fotos dos animais (v4.4): aba `Fotos` + arquivos no Drive; site faz proxy das imagens com cache em `<dados>/cache_fotos/`. `configurar_drive.py` autoriza uma vez (ver `docs/FOTOS_DRIVE.md`) |
| `routes_ajuda.py` / `templates/ajuda.html` | Aba ❓ Ajuda (v4.5): manual com passo a passo; prints no Drive (marca `ajuda=<nome>`, `c-` celular / `p-` computador), enviados por `subir_prints_ajuda.py`. Mudou uma tela? Atualize o texto e o print |
| `static/fila_fotos.js` | Foto offline: reduz no celular (1600 px), guarda no IndexedDB (mesmo banco das visitas, v2) e envia por `/api/fotos` |
| `static/fila_visitas.js` | Visita offline: guarda no celular (IndexedDB) e envia por `/api/visitas` quando há sinal; `ID Envio` evita duplicata |
| `tests/` | Testes automáticos (pytest) |
| `templates/` | Jinja2 (base.html + páginas); `static/` assets e PWA (`sw.js`, `manifest.json`) |

## Conceitos de cálculo (`calculos.py`)

- **Modelo vigente (v4.0): Média Móvel Perpétua** — `_simular_media_movel()` é a fonte
  da verdade para o **custo das vendas (COGS)**, o **capital imobilizado** e o
  **resultado por membro**. Cada venda sai pela média de custo (compra + gastos) do
  momento; gastos são diluídos só no rebanho vivo; gado comprado depois não paga
  despesa anterior. Dois pools (compra/gasto) preservam a divisão por venda.
- **CMP / GPCab / CTCab** — indicadores *acumulados* ainda exibidos (compra média,
  gastos/cab, soma). **Não** são mais a base do resultado; servem de referência.
- **Rateio de gastos entre donos:** por cabeça (não por % fixo) — cada dono arca
  proporcionalmente ao nº de cabeças que vendeu, pela média móvel.
- **Mortes/Perdas são perda separada (v4.0):** o custo da cabeça morta sai do rebanho
  como `perdas` (não infla os sobreviventes). Com "Perda De", a perda vai para o dono;
  senão é rateada em terços. `resultado_total` já desconta as perdas.
- **Nascimentos (v4.1):** entram a custo zero no rebanho (baixam a média). Com
  "Nascimento De", a cabeça vai para o estoque desse dono; senão é rateada em terços —
  o inverso de "Perda De". Não afeta valores, só o estoque por membro.
- **Animais com brinco (v4.3):** o cadastro NÃO entra nas contas (a cabeça já veio pela
  compra/nascimento). Só o atalho Nascimento grava no Manejo e a baixa por morte grava a
  Morte/Perda — nunca cadastre E registre a mesma cabeça duas vezes.
- **Invariantes (teste sempre que mexer em finanças):**
  1. `custo_vendidos + perdas + capital_imobilizado == total_custo` (nada aparece do nada);
  2. soma dos `custo_total` dos membros == `custo_vendidos` global;
  3. soma das `perdas` dos membros == `perdas` global.
  Se um cálculo novo quebrar qualquer uma, há bug. Rode o smoke test com os dados reais.
- **Comparativo anual** (`calcular_resultado_anual`): resultado do ano pela média móvel
  (receita − custo das vendidas − perdas); "caixa" é coluna separada. Soma dos anos ==
  `resultado_total`.
- **Cache** (`extensions._cache_dados`): resumo, membros e evolução ficam em cache até o
  `.xlsx` mudar no disco (`db.versao_arquivo`). Gravação sempre por `salvar_linha`/
  `reescrever_aba` (trava + save atômico) — nunca `wb.save` direto no arquivo de dados.
- O snapshot gravado na aba Vendas ao registrar/editar uma venda também usa a média
  móvel (`custo_medio_movel_venda`), ficando coerente com o dashboard. Os indicadores
  CMP/GPCab (`_build_*_timeline`, O(log n)) seguem existindo só como referência.

## Convenções

- Código e UI em **português**; comentários explicam o *porquê*, não o óbvio.
- Emojis aparecem em logs e na UI — garanta saída UTF-8 (já forçado em `config.py`).
- Datas no Excel em `dd/mm/aaaa`; leitura com `dayfirst=True`.
- Ao mexer em finanças, **rode um smoke test** com `gado_familia.xlsx` real (numa cópia)
  e confira a invariante contábil antes de concluir.

## Testes

```bash
pip install pytest
python -m pytest          # ~5 s; roda numa CÓPIA temporária dos dados
```

- `tests/conftest.py` copia `gado_familia.xlsx` (de `~/gado-dados/` ou da pasta do
  projeto) para uma pasta temporária e aponta `GADO_DATA_DIR` para ela — o arquivo
  real nunca é tocado.
- `test_calculos.py`: as 3 invariantes contábeis em cenários montados e nos dados reais.
- `test_paginas.py`: abre todas as páginas GET (nenhuma pode dar 500) e grava uma compra
  pelo formulário conferindo a ordem das colunas.
- `test_backup.py`: backup diário e limpeza usam a pasta de dados, não a do código.
- **Rode antes de todo `git push`.** Mexeu em finanças → os testes de invariante têm que passar.

## Changelog e specs

- `CHANGELOG.md` (Keep a Changelog, em português): toda mudança visível entra em
  **[Não lançado]**; ao fechar versão vira `## [x.y.z] — AAAA-MM-DD` no commit `vX.Y.Z: …`.
- Designs de mudanças maiores ficam em `docs/superpowers/specs/AAAA-MM-DD-<tema>-design.md`
  e o plano de implementação em `docs/superpowers/plans/AAAA-MM-DD-<tema>.md`.

**O que há em `docs/`:**

| Arquivo | O que é |
|---|---|
| `FOTOS_DRIVE.md` | Como autorizar o Google Drive (`configurar_drive.py`) e o que fazer quando o envio de fotos para |
| `superpowers/specs/2026-10-16-fotos-animais-design.md` | Design das fotos dos animais (v4.4, entregue) |
| `superpowers/plans/2026-10-16-fotos-animais.md` | Plano de implementação das fotos (v4.4, concluído) |
| `superpowers/specs/2026-10-22-whatsapp-notificacoes-design.md` | Design das notificações WhatsApp: preferências por pessoa, aviso de Morte/Nascimento, resumo semanal (entregue) |
| `superpowers/plans/2026-10-22-whatsapp-notificacoes.md` | Plano de implementação do WhatsApp (concluído) |
| `superpowers/specs/2026-10-25-varios-sitios-design.md` | Design de vários sítios (cada parente com o seu): donos por sítio, pasta por sítio, seletor, painel da família — entregue (fases 1–4) |
| `superpowers/plans/2026-10-25-varios-sitios-fase1.md` | Plano da fase 1 (donos configuráveis) — concluído |
| `superpowers/plans/2026-10-25-varios-sitios-fase2.md` | Plano da fase 2 (pasta por sítio, seletor, acesso) — concluído |
| `superpowers/plans/2026-10-25-varios-sitios-fase3.md` | Plano da fase 3 (admin, Tasks por sítio, tela de sítios) — concluído |
| `superpowers/plans/2026-10-25-varios-sitios-fase4.md` | Plano da fase 4 (painel da Família) — concluído |
| `client_secret_*.json` | Credencial OAuth do app do Drive — **fora do Git** (`.gitignore`), nunca commitar |

## Backup

- `backup_automatico.py` (Task diária no PythonAnywhere) grava em `~/gado-dados/backups/`
  como `backup_AAAAMMDD_HHMMSS.xlsx` — aparecem na página **Backups** do site para download.
- Site e script compartilham a mesma pasta e a mesma rotação (30 arquivos).
