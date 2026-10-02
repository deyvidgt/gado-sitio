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

- Os dados ficam em **`gado_familia.xlsx`** (abas: Compras, Gastos, Vendas, Manejo, Visitas).
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
| `alertas_whatsapp.py` | Notificações via CallMeBot |
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
- **Invariantes (teste sempre que mexer em finanças):**
  1. `custo_vendidos + perdas + capital_imobilizado == total_custo` (nada aparece do nada);
  2. soma dos `custo_total` dos membros == `custo_vendidos` global;
  3. soma das `perdas` dos membros == `perdas` global.
  Se um cálculo novo quebrar qualquer uma, há bug. Rode o smoke test com os dados reais.
- O snapshot gravado na aba Vendas ao registrar/editar uma venda também usa a média
  móvel (`custo_medio_movel_venda`), ficando coerente com o dashboard. Os indicadores
  CMP/GPCab (`_build_*_timeline`, O(log n)) seguem existindo só como referência.

## Convenções

- Código e UI em **português**; comentários explicam o *porquê*, não o óbvio.
- Emojis aparecem em logs e na UI — garanta saída UTF-8 (já forçado em `config.py`).
- Datas no Excel em `dd/mm/aaaa`; leitura com `dayfirst=True`.
- Ao mexer em finanças, **rode um smoke test** com `gado_familia.xlsx` real (numa cópia)
  e confira a invariante contábil antes de concluir.

## Pendências conhecidas / melhorias sugeridas

- Form de Visitas tem campo `racao`/`sacos_racao` que a rota **não** salva (só sal e proteinado).
