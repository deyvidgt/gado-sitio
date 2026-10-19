# CLAUDE.md — Guia do Projeto

Orientações para o Claude Code (e humanos) trabalharem neste repositório.

## O que é

Sistema web de **gestão de gado** da família (Sítio Santo Antonio). App **Flask** em
português, com PWA, que controla compras, gastos, vendas, manejo e visitas ao sítio,
além de cálculos financeiros do rebanho e relatórios/PDF.

**Donos/membros:** `Mae` (Geane), `Deyvid`, `Nilson` — ver `config.py: MEMBROS`.

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

## Arquitetura

| Arquivo | Papel |
|---|---|
| `app.py` | Ponto de entrada; importa `extensions.app` e registra todas as rotas |
| `extensions.py` | App Flask, sessão, CSRF, cache de dados/resumo, helpers (`fmt_brl`, `fmt_data`, `parse_valor`) |
| `config.py` | Constantes: membros, colunas das abas, tipos, cores, secret key |
| `db.py` | Leitura/escrita/backup do Excel e **migração de colunas** |
| `calculos.py` | **Motor financeiro** (CMP, GPCab, CTCab, resultado por membro, resumo) |
| `routes_*.py` | Rotas por área (registros, visitas, relatórios, api, usuários, auth…) |
| `relatorios.py` / `exportar.py` | Geração de relatórios e exportação |
| `alertas_whatsapp.py` | Notificações via CallMeBot: Task diária só com urgentes (sem repetir), resumo semanal na segunda; fila de avisos de visita (`avisos_pendentes.json`) |
| `saude.py` | Calendário sanitário (Triângulo Mineiro): vacina por tipo, campanha de brucelose, vermifugação 5-7-9 — fonte única p/ painel, calendário e WhatsApp |
| `backup_automatico.py` | Backup diário (Task do PythonAnywhere) |
| `resumo_mensal.py` | Resumo do mês no WhatsApp no dia 1º (Task diária; `--teste` só mostra) |
| `insumos.py` | Estoque de Sal/Proteinado/Ração: sacos em estoque contados nas visitas + compras (Gastos: Produto/Qtd Sacos) → consumo e "acaba em" (painel e WhatsApp) |
| `animais.py` | Cadastro individual por brinco (aba `Animais`): cor por dono, nº 01–99 reaproveitado, ID `A0001` liga o histórico (`Brincos` em Manejo/Vendas = "Amarelo 21 #A0003"); baixa, brucelose por animal |
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

## Backup

- `backup_automatico.py` (Task diária no PythonAnywhere) grava em `~/gado-dados/backups/`
  como `backup_AAAAMMDD_HHMMSS.xlsx` — aparecem na página **Backups** do site para download.
- Site e script compartilham a mesma pasta e a mesma rotação (30 arquivos).
