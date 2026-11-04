#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
routes_api.py — Sítio Santo Antonio
APIs JSON: fluxo, membros, chuvas, cotações, última visita,
           calendário de manejo, histórico de arroba, WhatsApp.
"""
import os, threading
from flask import request, session, jsonify, send_file
import pandas as pd
from datetime import datetime, timedelta
from db import carregar_aba
from calculos import (
    calcular_fluxo_caixa, calcular_todos_membros,
    calcular_resumo_financeiro, calcular_evolucao_rebanho,
)
from config import MEMBROS, NOMES_MEMBROS, ALERTAS_SAUDE
from busca import buscar_global
from extensions import (
    app, _agora, login_required,
    _get_dados_cache, _get_dados_busca_cache, _get_resumo_cache, _get_membros_cache, _get_evolucao_cache,
    _safe, fmt_brl, fmt_data, _carregar_usuarios, _salvar_usuarios,
    BASE_DIR,
)

#  APIs
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/fluxo")
@login_required
def api_fluxo():
    dados = _get_dados_cache()
    df = calcular_fluxo_caixa(dados["Compras"], dados["Gastos"], dados["Vendas"])
    if df.empty:
        return jsonify({"labels": [], "entradas": [], "saidas": [], "saldo": []})
    return jsonify({"labels":   [str(p) for p in df["AnoMes"]],
                    "entradas": [round(_safe(v), 2) for v in df["Entradas"]],
                    "saidas":   [round(abs(_safe(v)), 2) for v in df["Saidas"]],
                    "saldo":    [round(_safe(v), 2) for v in df["Saldo Acumulado"]]})

@app.route("/api/membros")
@login_required
def api_membros():
    mbr = _get_membros_cache()
    return jsonify({"nomes":      [NOMES_MEMBROS[m] for m in MEMBROS],
                    "receitas":   [round(mbr[m]["receita"],    2) for m in MEMBROS],
                    "custos":     [round(mbr[m]["custo_total"], 2) for m in MEMBROS],
                    "resultados": [round(mbr[m]["resultado"],  2) for m in MEMBROS]})


@app.route("/api/rebanho")
@login_required
def api_rebanho():
    """Evolução mensal do rebanho: entradas, saídas, cabeças e custo médio/cab."""
    meses = _get_evolucao_cache()
    return jsonify({
        "labels":    [m["label"] for m in meses],
        "entradas":  [m["entradas"] for m in meses],
        "saidas":    [m["saidas"] for m in meses],
        "cabecas":   [m["cabecas"] for m in meses],
        "custo_cab": [m["custo_cab"] for m in meses],
    })


# ── API: Chuvas mensais ───────────────────────────────────────────────────────

@app.route("/api/chuvas")
@login_required
def api_chuvas():
    """
    Retorna média, total e contagem de registros de chuva por mês,
    calculados a partir das visitas registradas.

    Resposta:
      labels      — lista de "YYYY-MM" (strings)
      totais      — mm acumulados no mês
      medias      — média por visita que choveu
      visitas     — total de visitas no mês
      visitas_com_chuva — visitas em que choveu
      meses       — lista de objetos completos para a tabela
    """
    df = carregar_aba("Visitas")
    if df.empty or "Data" not in df.columns:
        return jsonify({"labels": [], "totais": [], "medias": [],
                        "visitas": [], "visitas_com_chuva": [], "meses": []})

    df = df[df["Data"].notna()].copy()
    df["AnoMes"] = df["Data"].dt.to_period("M")

    # Chuva mm: tratar valores nulos / zero como "não choveu"
    df["mm"] = pd.to_numeric(df.get("Chuva mm", 0), errors="coerce").fillna(0)
    df["choveu_flag"] = df.get("Choveu", "Não").apply(
        lambda v: str(v).strip().lower() in ("sim", "yes", "1", "true")
    )

    meses_dados = []
    for periodo, grp in df.groupby("AnoMes"):
        total_vis   = len(grp)
        vis_chuva   = int(grp["choveu_flag"].sum())
        total_mm    = float(grp.loc[grp["choveu_flag"], "mm"].sum())
        media_mm    = round(total_mm / vis_chuva, 1) if vis_chuva > 0 else 0.0
        meses_dados.append({
            "periodo":           str(periodo),
            "label":             periodo.strftime("%b/%Y"),
            "total_mm":          round(total_mm, 1),
            "media_mm":          media_mm,
            "visitas":           total_vis,
            "visitas_com_chuva": vis_chuva,
            "dias_sem_chuva":    total_vis - vis_chuva,
        })

    meses_dados.sort(key=lambda x: x["periodo"])

    return jsonify({
        "labels":             [m["label"]             for m in meses_dados],
        "totais":             [m["total_mm"]          for m in meses_dados],
        "medias":             [m["media_mm"]          for m in meses_dados],
        "visitas":            [m["visitas"]           for m in meses_dados],
        "visitas_com_chuva":  [m["visitas_com_chuva"] for m in meses_dados],
        "meses":              meses_dados,
    })


@app.route("/api/cotacao-scot")
@login_required
def api_cotacao_scot():
    try:
        import requests, re
        from bs4 import BeautifulSoup
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9",
        }
        r = requests.get("https://www.scotconsultoria.com.br/cotacoes/novilha/",
                         headers=headers, timeout=12)
        soup = BeautifulSoup(r.text, "html.parser")
        cotacoes = []
        regioes_alvo = ["triângulo", "triangulo", "uberlândia", "uberaba", "patos de minas"]
        for table in soup.find_all("table"):
            for row_t in table.find_all("tr")[1:]:
                cols = row_t.find_all(["td", "th"])
                if not cols:
                    continue
                regiao = cols[0].get_text(strip=True)
                if any(k in regiao.lower() for k in regioes_alvo):
                    preco_str = " ".join(c.get_text(strip=True) for c in cols[1:3])
                    nums = re.findall(r"\d{2,3}[.,]\d{2}", preco_str)
                    preco = float(nums[0].replace(",", ".")) if nums else None
                    cotacoes.append({"regiao": regiao, "preco": preco, "raw": preco_str})
        return jsonify({"ok": True, "cotacoes": cotacoes,
                        "atualizado": _agora().strftime("%d/%m/%Y %H:%M"),
                        "fonte": "Scot Consultoria"})
    except Exception as e:
        msg = str(e)
        if any(k in msg for k in ("ProxyError", "Max retries", "ConnectionError",
                                   "Tunnel connection", "403 Forbidden", "timeout")):
            msg = ("Servidor sem acesso direto à internet (proxy bloqueado). "
                   "Acesse a cotação pelo link abaixo.")
        return jsonify({"ok": False, "erro": msg})


def _historico_preco_arroba(dados, dias=30):
    """Extrai histórico de preço/@ das vendas (últimos N dias)."""
    from datetime import timedelta, date as date_type
    hoje = date_type.today()
    inicio = hoje - timedelta(days=dias)

    df_v = dados.get("Vendas")
    if df_v is None or df_v.empty:
        return {}

    precos = {}
    for _, row in df_v.iterrows():
        try:
            data = pd.to_datetime(row.get("Data"), dayfirst=True, errors="coerce")
            if pd.isna(data) or data.date() < inicio:
                continue
            preco_arr = float(str(row.get("Preço /@ (R$)", "") or 0).replace(",", "."))
            if preco_arr > 0:
                data_str = data.strftime("%Y-%m-%d")
                if data_str not in precos or preco_arr > precos[data_str]:
                    precos[data_str] = preco_arr
        except Exception:
            pass

    return dict(sorted(precos.items()))


@app.route("/api/cotacao-hoje")
@login_required
def api_cotacao_hoje():
    """Retorna preço/@ atual + histórico 30 dias."""
    try:
        dados = _get_dados_cache()
        historico = _historico_preco_arroba(dados, dias=30)

        # Tenta Scot, se falhar tenta IMEA, se falhar usa média histórica
        preco_atual = None
        fonte = "Histórico"

        try:
            import requests, re
            from bs4 import BeautifulSoup
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "pt-BR,pt;q=0.9",
            }
            r = requests.get("https://www.scotconsultoria.com.br/cotacoes/novilha/",
                           headers=headers, timeout=5)
            soup = BeautifulSoup(r.text, "html.parser")
            for table in soup.find_all("table"):
                for row_t in table.find_all("tr")[1:]:
                    cols = row_t.find_all(["td", "th"])
                    if not cols:
                        continue
                    regiao = cols[0].get_text(strip=True)
                    if "triângulo" in regiao.lower() or "uberlândia" in regiao.lower():
                        preco_str = " ".join(c.get_text(strip=True) for c in cols[1:3])
                        nums = re.findall(r"\d{2,3}[.,]\d{2}", preco_str)
                        if nums:
                            preco_atual = float(nums[0].replace(",", "."))
                            fonte = "Scot Consultoria"
                            break
                if preco_atual:
                    break
        except Exception:
            pass

        # Fallback: média dos últimos 7 dias
        if not preco_atual and historico:
            ultimos_7 = sorted(historico.items())[-7:]
            preco_atual = sum(p for _, p in ultimos_7) / len(ultimos_7) if ultimos_7 else None

        return jsonify({
            "ok": True,
            "preco_atual": preco_atual,
            "fonte": fonte,
            "atualizado": _agora().strftime("%d/%m/%Y %H:%M"),
            "historico": historico,
            "datas": list(historico.keys()),
            "precos": list(historico.values()),
        })
    except Exception as e:
        return jsonify({"ok": False, "erro": str(e)}), 500


_IMEA_URL = "https://www.imea.com.br/imea-site/indicador-boi"
_IMEA_INDICADORES = [
    {"emoji": "🐮", "nome": "Novilha 18M 255kg 8,5@", "kg": 255, "arrobas": 8.5,
     "chaves": [["NOVILHA", "255"], ["NOVILHA", "18M", "8,5"], ["NOVILHA", "NELORE", "18"]]},
    {"emoji": "🐄", "nome": "Bezerra 12M 180kg 6@",   "kg": 180, "arrobas": 6.0,
     "chaves": [["BEZERRA", "180", "6"], ["BEZERRA", "12M", "180"], ["BEZERRA", "NELORE", "12"]]},
    {"emoji": "🐄", "nome": "Bezerra 8M 150kg 5@",    "kg": 150, "arrobas": 5.0,
     "chaves": [["BEZERRA", "150", "5"], ["BEZERRA", "8M", "150"], ["BEZERRA", "165"]]},
]
# O IMEA publica uma vez por dia: buscar de novo a cada clique só abria outro
# Chromium (~30 s e muita memória no PythonAnywhere). Sucesso fica 3 h em cache;
# falha, 5 min (para não martelar o site, mas tentar de novo logo).
_IMEA_TTL_OK, _IMEA_TTL_ERRO = 3 * 3600, 300
_imea_lock = threading.Lock()
_imea_cache: dict = {}   # {"ts", "ttl", "precos", "debug", "erro", "atualizado"}


def _precos_imea() -> dict:
    """Preços do IMEA (com cache). Só um Chromium por vez: quem chega enquanto
    outro busca espera e reaproveita o resultado."""
    import time
    def _valido():
        c = _imea_cache
        return c and time.time() - c["ts"] < c["ttl"]
    if _valido():
        return _imea_cache
    with _imea_lock:
        if _valido():
            return _imea_cache
        precos, erro, debug = [None] * len(_IMEA_INDICADORES), None, ""
        try:
            html, debug = _fetch_imea_inline()
        except Exception as e:
            html, erro, debug = "", f"Não foi possível abrir o navegador: {e}", str(e)
        if not erro and not html:
            erro = "O IMEA não respondeu."
        if html:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")
            texto = soup.get_text(" ", strip=True).upper()
            if not any(k in texto for k in ["NOVILHA", "BEZERRA", "NELORE"]):
                erro = "Página renderizou mas sem dados. Verifique imea.com.br/imea-site/indicador-boi"
            else:
                for i, ind in enumerate(_IMEA_INDICADORES):
                    for chave in ind["chaves"]:
                        achado = _buscar_indicador_imea(soup, chave)
                        if achado and achado.get("preco"):
                            precos[i] = achado
                            break
                if not any(precos):
                    erro = f"Nenhum indicador encontrado. Debug: {debug}"
        _imea_cache.clear()
        _imea_cache.update({
            "ts": time.time(), "ttl": _IMEA_TTL_ERRO if erro else _IMEA_TTL_OK,
            "precos": precos, "erro": erro, "debug": debug,
            "atualizado": _agora().strftime("%d/%m/%Y %H:%M"),
        })
        return _imea_cache


@app.route("/api/cotacao-imea")
@login_required
def api_cotacao_imea():
    r_fin = _get_resumo_cache()
    break_even = round(r_fin["break_even"], 2)
    ctcab      = round(r_fin["ctcab"],      2)

    def _erro(msg, debug=""):
        return jsonify({"ok": False, "cotacoes": [],
                        "break_even": break_even, "ctcab": ctcab,
                        "erro": msg, "debug": debug})

    try:
        import playwright  # noqa
    except ImportError:
        return _erro("Playwright não instalado. Execute: pip install playwright && python -m playwright install chromium")

    res = _precos_imea()
    if res["erro"] and not any(res["precos"]):
        return _erro(res["erro"], res["debug"])

    # Comparação com o break-even é refeita a cada pedido (os dados mudam;
    # só os preços do IMEA vêm do cache).
    cotacoes = []
    for ind, achado in zip(_IMEA_INDICADORES, res["precos"]):
        base = {"emoji": ind["emoji"], "nome": ind["nome"], "kg": ind["kg"], "arrobas": ind["arrobas"]}
        if achado:
            pc = achado["preco"]
            arrs = ind["arrobas"]
            vs = round(pc - break_even, 2)
            cotacoes.append({**base,
                "regiao": achado.get("regiao", "Sudeste"),
                "preco_cab": round(pc, 2),
                "preco_arroba": round(pc / arrs, 2) if arrs else 0.0,
                "variacao": achado.get("variacao"),
                "lucra": pc >= break_even,
                "vs_breakeven": vs,
                "vs_breakeven_pct": round(vs / break_even * 100, 1) if break_even else 0.0,
            })
        else:
            cotacoes.append({**base,
                "regiao": "Sudeste", "preco_cab": None, "preco_arroba": None,
                "variacao": None, "lucra": None, "vs_breakeven": None, "vs_breakeven_pct": None,
            })

    return jsonify({
        "ok": True, "cotacoes": cotacoes,
        "break_even": break_even, "ctcab": ctcab,
        "fonte": "IMEA", "url": _IMEA_URL,
        "atualizado": res["atualizado"],
        "referencia": "Região: Sudeste | Fonte: IMEA",
        "debug": res["debug"],
        "erro": None,
    })


def _fetch_imea_inline():
    """Abre a página do IMEA num Chromium headless e devolve (html, log).

    Nunca instala o Chromium aqui: antes, sem o navegador, a própria requisição
    rodava `playwright install` (até 3 min com a página travada e o worker preso).
    A instalação é feita uma vez, no console: python -m playwright install chromium
    """
    from playwright.sync_api import sync_playwright, TimeoutError as PwTimeout
    log = []

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"])
        except Exception as e:
            if "executable" in str(e).lower():
                raise RuntimeError("Chromium não instalado no servidor. No console, rode: "
                                   "python -m playwright install chromium") from None
            raise
        ctx = browser.new_context(locale="pt-BR", timezone_id="America/Sao_Paulo")
        page = ctx.new_page()
        try:
            page.goto(_IMEA_URL, wait_until="domcontentloaded", timeout=25000)
            for sel in ["table", "mat-table", "tbody tr"]:
                try:
                    page.wait_for_selector(sel, timeout=8000)
                    log.append(f"sel:{sel}")
                    break
                except PwTimeout:
                    continue
            page.wait_for_timeout(1500)
            html = page.content()
            log.append(f"{len(html)}chars")
        except Exception as e:
            html = ""
            log.append(f"err:{e}")
        finally:
            browser.close()

    return html, " | ".join(log)


def _parse_preco_imea(texto):
    import re
    m = re.search(r"\d{1,3}(?:\.\d{3})*,\d{2}", texto)
    if m:
        return float(m.group().replace(".", "").replace(",", "."))
    m = re.search(r"\d{3,6}\.\d{2}", texto)
    return float(m.group()) if m else None

def _parse_var_imea(texto):
    import re
    m = re.search(r"([+-]?\d{1,3}[.,]\d{1,2})%?", texto)
    return float(m.group(1).replace(",", ".")) if m else None

def _buscar_indicador_imea(soup, palavras_chave):
    REGIOES = ["sudeste", "são paulo", "sao paulo", "minas gerais", "minas", "mg",
               "goiás", "goias", "espírito santo", "rio de janeiro", "centro-sul"]
    candidatos = [el for el in soup.find_all(string=True)
                  if all(p.upper() in str(el).upper() for p in palavras_chave)]
    for cand in candidatos:
        container = cand.parent
        tabela = None
        for _ in range(14):
            if container is None:
                break
            tabela = container.find(["table", "mat-table"])
            if tabela:
                break
            container = container.parent
        if tabela is None:
            continue
        linhas = tabela.find_all(["tr", "mat-row"]) or tabela.find_all(attrs={"role": "row"})
        if not linhas:
            continue
        preco_col, var_col = 1, 2
        hdr = linhas[0].find_all(["th", "td", "mat-header-cell"])
        for i, c in enumerate(hdr):
            t = c.get_text(strip=True).lower()
            if any(k in t for k in ["r$", "preço", "preco", "cab", "@"]):
                preco_col = i
            elif any(k in t for k in ["varia", "%"]):
                var_col = i
        melhor = None
        score_max = -1
        for tr in linhas[1:]:
            cells = tr.find_all(["td", "th", "mat-cell"])
            if not cells:
                continue
            reg = cells[0].get_text(strip=True).lower()
            score = 10 if "sudeste" in reg else (5 if any(s in reg for s in REGIOES) else 0)
            if score > score_max:
                score_max = score
                melhor = cells
        if melhor is None:
            for tr in linhas[1:]:
                cells = tr.find_all(["td", "th", "mat-cell"])
                if cells and len(cells) >= 2:
                    melhor = cells
                    break
        if melhor is None:
            continue
        preco_txt = melhor[preco_col].get_text(strip=True) if preco_col < len(melhor) else ""
        var_txt   = melhor[var_col].get_text(strip=True)   if var_col   < len(melhor) else ""
        preco = _parse_preco_imea(preco_txt)
        if preco:
            return {"titulo": str(cand).strip(), "regiao": melhor[0].get_text(strip=True),
                    "preco": preco, "variacao": _parse_var_imea(var_txt)}
    return None


@app.route("/api/ultima-visita")
@login_required
def api_ultima_visita():
    df = carregar_aba("Visitas")
    if df.empty:
        return jsonify({"ok": False, "msg": "Nenhuma visita registrada."})
    df_sorted = df.sort_values("Data", ascending=False, na_position="last")
    row = df_sorted.iloc[0]
    def _str(v):
        return "" if (v is None or (isinstance(v, float) and pd.isna(v))) else str(v)
    return jsonify({
        "ok": True,
        "data":           fmt_data(row.get("Data")),
        "responsavel":    _str(row.get("Responsável")),
        "gado_contado":   int(_safe(row.get("Gado Contado"))),
        "gado_esperado":  int(_safe(row.get("Gado Esperado"))),
        "gado_faltando":  int(_safe(row.get("Gado Faltando"))),
        "sal":            _str(row.get("Sal/Ração")),
        "proteinado":     _str(row.get("Proteinado")),
        "grama":          _str(row.get("Grama/Pastagem")),
        "corrego":        _str(row.get("Córrego/Água")),
        "choveu":         _str(row.get("Choveu")),
        "chuva_mm":       _safe(row.get("Chuva mm"), 0.0),
        "sugestoes":      _str(row.get("Sugestões")),
    })


@app.route("/api/busca")
@login_required
def api_busca():
    """Busca rápida global: GET /api/busca?q=termo&tipo=animal"""
    q = request.args.get("q", "").strip()[:80]
    tipo = request.args.get("tipo", "").strip() or None
    import modulos
    resultados = buscar_global(q, tipo, dados=_get_dados_busca_cache(),
                               modulos=modulos.estado_sitio())
    return jsonify({"resultados": resultados})


# ══════════════════════════════════════════════════════════════════════════════
