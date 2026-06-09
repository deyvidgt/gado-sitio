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
    calcular_resumo_financeiro,
)
from config import MEMBROS, NOMES_MEMBROS, ALERTAS_SAUDE
from extensions import (
    app, _agora, login_required,
    _get_dados_cache, _get_resumo_cache,
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
    dados = _get_dados_cache()
    mbr = calcular_todos_membros(dados["Vendas"], dados["Compras"], dados["Gastos"], dados["Manejo"])
    return jsonify({"nomes":      [NOMES_MEMBROS[m] for m in MEMBROS],
                    "receitas":   [round(mbr[m]["receita"],    2) for m in MEMBROS],
                    "custos":     [round(mbr[m]["custo_total"], 2) for m in MEMBROS],
                    "resultados": [round(mbr[m]["resultado"],  2) for m in MEMBROS]})


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


@app.route("/api/cotacao-imea")
@login_required
def api_cotacao_imea():
    dados = _get_dados_cache()
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

    INDICADORES = [
        {"emoji": "🐮", "nome": "Novilha 18M 255kg 8,5@", "kg": 255, "arrobas": 8.5,
         "chaves": [["NOVILHA", "255"], ["NOVILHA", "18M", "8,5"], ["NOVILHA", "NELORE", "18"]]},
        {"emoji": "🐄", "nome": "Bezerra 12M 180kg 6@",   "kg": 180, "arrobas": 6.0,
         "chaves": [["BEZERRA", "180", "6"], ["BEZERRA", "12M", "180"], ["BEZERRA", "NELORE", "12"]]},
        {"emoji": "🐄", "nome": "Bezerra 8M 150kg 5@",    "kg": 150, "arrobas": 5.0,
         "chaves": [["BEZERRA", "150", "5"], ["BEZERRA", "8M", "150"], ["BEZERRA", "165"]]},
    ]

    try:
        from _imea_playwright import fetch_imea, buscar_indicador
        html, debug_log = fetch_imea()
    except ImportError:
        # fallback inline
        html, debug_log = _fetch_imea_inline()

    if not html:
        return _erro("Playwright não retornou HTML.", debug_log)

    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    texto = soup.get_text(" ", strip=True).upper()
    if not any(k in texto for k in ["NOVILHA", "BEZERRA", "NELORE"]):
        return _erro("Página renderizou mas sem dados. Verifique imea.com.br/imea-site/indicador-boi", debug_log)

    cotacoes = []
    for ind in INDICADORES:
        achado = None
        for chave in ind["chaves"]:
            achado = _buscar_indicador_imea(soup, chave)
            if achado:
                break
        if achado and achado.get("preco"):
            pc = achado["preco"]
            arrs = ind["arrobas"]
            vs = round(pc - break_even, 2)
            cotacoes.append({
                "emoji": ind["emoji"], "nome": ind["nome"],
                "kg": ind["kg"], "arrobas": arrs,
                "regiao": achado.get("regiao", "Sudeste"),
                "preco_cab": round(pc, 2),
                "preco_arroba": round(pc / arrs, 2) if arrs else 0.0,
                "variacao": achado.get("variacao"),
                "lucra": pc >= break_even,
                "vs_breakeven": vs,
                "vs_breakeven_pct": round(vs / break_even * 100, 1) if break_even else 0.0,
            })
        else:
            cotacoes.append({
                "emoji": ind["emoji"], "nome": ind["nome"],
                "kg": ind["kg"], "arrobas": ind["arrobas"],
                "regiao": "Sudeste", "preco_cab": None, "preco_arroba": None,
                "variacao": None, "lucra": None, "vs_breakeven": None, "vs_breakeven_pct": None,
            })

    algum_ok = any(c["preco_cab"] is not None for c in cotacoes)
    return jsonify({
        "ok": algum_ok, "cotacoes": cotacoes,
        "break_even": break_even, "ctcab": ctcab,
        "fonte": "IMEA", "url": "https://www.imea.com.br/imea-site/indicador-boi",
        "atualizado": _agora().strftime("%d/%m/%Y %H:%M"),
        "referencia": "Região: Sudeste | Fonte: IMEA",
        "debug": debug_log,
        "erro": None if algum_ok else f"Nenhum indicador encontrado. Debug: {debug_log}",
    })


def _fetch_imea_inline():
    """Playwright inline (sem módulo separado)."""
    import subprocess
    from playwright.sync_api import sync_playwright, TimeoutError as PwTimeout
    log = []
    URL = "https://www.imea.com.br/imea-site/indicador-boi"

    def _launch(p):
        try:
            return p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"])
        except Exception as e:
            if "executable" in str(e).lower():
                subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"],
                               capture_output=True, timeout=180)
                return p.chromium.launch(headless=True, args=["--no-sandbox"])
            raise

    with sync_playwright() as p:
        browser = _launch(p)
        ctx = browser.new_context(locale="pt-BR", timezone_id="America/Sao_Paulo")
        page = ctx.new_page()
        try:
            page.goto(URL, wait_until="networkidle", timeout=40000)
            for sel in ["table", "mat-table", "tbody tr"]:
                try:
                    page.wait_for_selector(sel, timeout=8000)
                    log.append(f"sel:{sel}")
                    break
                except PwTimeout:
                    continue
            page.wait_for_timeout(2500)
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
        "gado_contado":   int(row.get("Gado Contado") or 0),
        "gado_esperado":  int(row.get("Gado Esperado") or 0),
        "gado_faltando":  int(row.get("Gado Faltando") or 0),
        "sal":            _str(row.get("Sal/Ração")),
        "proteinado":     _str(row.get("Proteinado")),
        "grama":          _str(row.get("Grama/Pastagem")),
        "corrego":        _str(row.get("Córrego/Água")),
        "choveu":         _str(row.get("Choveu")),
        "chuva_mm":       float(row.get("Chuva mm") or 0),
        "sugestoes":      _str(row.get("Sugestões")),
    })


# ══════════════════════════════════════════════════════════════════════════════
