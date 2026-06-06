#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema de Gestão de Gado — Sítio Santo Antonio
v3.3 — melhorias de segurança, cache, CSRF e chuvas mensais
"""

import sys, os, tempfile, hashlib, time, threading
from functools import wraps
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
    BUNDLE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    BUNDLE_DIR = BASE_DIR

sys.path.insert(0, BUNDLE_DIR)

from flask import (Flask, render_template, request, redirect, url_for,
                   jsonify, flash, send_file, session, abort)
import pandas as pd
from datetime import datetime, timedelta
try:
    from zoneinfo import ZoneInfo
    _TZ_BR = ZoneInfo("America/Sao_Paulo")
except ImportError:
    _TZ_BR = None  # Python < 3.9 — fallback para horário local

def _agora():
    """Retorna datetime atual no fuso de Brasília (ou local como fallback)."""
    if _TZ_BR:
        return datetime.now(_TZ_BR).replace(tzinfo=None)
    return _agora()

from db import (carregar_todas, carregar_aba, salvar_linha,
                reescrever_aba, inicializar, fazer_backup)
from calculos import (
    calcular_estoque, calcular_resumo_financeiro, calcular_todos_membros,
    calcular_fluxo_caixa, calcular_cmp_ate_data, calcular_gpcab_ate_data,
    calcular_cmp, calcular_gpcab, calcular_estoque_por_membro,
    calcular_indicadores_extras, calcular_gasto_por_tipo, calcular_evolucao_cmp,
)
from config import (
    TIPOS_GASTO, TIPOS_MANEJO, MEMBROS, NOMES_MEMBROS, EMOJIS_MEMBROS,
    USUARIOS, SESSAO_MINUTOS, OPCOES_VISITA, SECRET_KEY,
    MAX_TENTATIVAS_LOGIN, CACHE_RESUMO_TTL,
)
from exportar import exportar_relatorio_excel

app = Flask(__name__,
            template_folder=os.path.join(BUNDLE_DIR, "templates"),
            static_folder=os.path.join(BUNDLE_DIR, "static"))

# ── Secret key vem do config (que lê variável de ambiente) ───────────────────
app.secret_key = SECRET_KEY
app.jinja_env.globals["enumerate"] = enumerate

@app.before_request
def _renovar_sessao():
    session.permanent = True
    app.permanent_session_lifetime = timedelta(minutes=SESSAO_MINUTOS)


# ══════════════════════════════════════════════════════════════════════════════
#  CACHE DO RESUMO FINANCEIRO
#  Evita recalcular tudo do zero a cada request.
#  Invalidado automaticamente após qualquer escrita (salvar_linha / reescrever_aba).
# ══════════════════════════════════════════════════════════════════════════════

_cache_lock = threading.Lock()
_cache: dict = {}          # { "resumo": (timestamp, valor), "dados": (timestamp, valor) }

def _cache_invalidar():
    with _cache_lock:
        _cache.clear()

def _cache_get(chave):
    with _cache_lock:
        entry = _cache.get(chave)
        if entry and (time.time() - entry[0]) < CACHE_RESUMO_TTL:
            return entry[1]
    return None

def _cache_set(chave, valor):
    with _cache_lock:
        _cache[chave] = (time.time(), valor)

def _get_dados_cache():
    dados = _cache_get("dados")
    if dados is None:
        dados = carregar_todas()
        _cache_set("dados", dados)
    return dados

def _get_resumo_cache():
    r = _cache_get("resumo")
    if r is None:
        dados = _get_dados_cache()
        r = calcular_resumo_financeiro(
            dados["Compras"], dados["Gastos"], dados["Vendas"], dados["Manejo"]
        )
        _cache_set("resumo", r)
    return r

# Monkey-patch: invalidar cache em toda escrita
_orig_salvar = salvar_linha
def _salvar_e_invalidar(aba, linha):
    _orig_salvar(aba, linha)
    _cache_invalidar()

_orig_reescrever = reescrever_aba
def _reescrever_e_invalidar(aba, df):
    _orig_reescrever(aba, df)
    _cache_invalidar()

import db as _db_mod
_db_mod.salvar_linha = _salvar_e_invalidar
_db_mod.reescrever_aba = _reescrever_e_invalidar

# Redirecionar imports locais para versões com cache
salvar_linha = _salvar_e_invalidar
reescrever_aba = _reescrever_e_invalidar


# ══════════════════════════════════════════════════════════════════════════════
#  CSRF — proteção simples sem dependência externa
# ══════════════════════════════════════════════════════════════════════════════

import secrets as _secrets

def _gerar_csrf():
    if "csrf_token" not in session:
        session["csrf_token"] = _secrets.token_hex(32)
    return session["csrf_token"]

def _validar_csrf():
    token_form = request.form.get("csrf_token", "")
    token_sess = session.get("csrf_token", "")
    if not token_form or not token_sess or token_form != token_sess:
        abort(403)

# Injetar csrf_token em todos os templates automaticamente
@app.context_processor
def _inject_csrf():
    return {"csrf_token": _gerar_csrf()}


# ══════════════════════════════════════════════════════════════════════════════
#  AUTENTICAÇÃO — bcrypt com fallback SHA-256 legado
# ══════════════════════════════════════════════════════════════════════════════

def _sha256(senha: str) -> str:
    return hashlib.sha256(senha.strip().encode()).hexdigest()

def _bcrypt_disponivel() -> bool:
    try:
        import bcrypt  # noqa
        return True
    except ImportError:
        return False

def _hash_bcrypt(senha: str) -> str:
    import bcrypt
    return bcrypt.hashpw(senha.strip().encode(), bcrypt.gensalt(rounds=12)).decode()

def _verificar_hash(senha: str, stored: str) -> bool:
    """
    Aceita hashes bcrypt ($2b$...) e SHA-256 legados (hex de 64 chars).
    Retorna (válido: bool, deve_migrar: bool).
    """
    if stored.startswith("$2b$") or stored.startswith("$2a$"):
        if _bcrypt_disponivel():
            import bcrypt
            return bcrypt.checkpw(senha.strip().encode(), stored.encode())
        return False
    # SHA-256 legado
    return _sha256(senha) == stored

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logado"):
            return redirect(url_for("login", next=request.path))
        return f(*args, **kwargs)
    return decorated

@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("logado"):
        return redirect(url_for("dashboard"))

    erro = None
    usuario_digitado = ""

    if request.method == "POST":
        _validar_csrf()
        usuario = request.form.get("usuario", "").strip().lower()
        senha   = request.form.get("senha",   "").strip()
        usuario_digitado = usuario

        tentativas = session.get("tentativas_login", 0)
        usuarios_db = _carregar_usuarios()

        if tentativas >= MAX_TENTATIVAS_LOGIN:
            erro = "Muitas tentativas. Feche e abra o programa para desbloquear."
        elif usuario in usuarios_db and _verificar_hash(senha, usuarios_db[usuario]["hash"]):
            # ✅ Login OK — migrar SHA-256 → bcrypt se possível
            if _bcrypt_disponivel():
                stored = usuarios_db[usuario]["hash"]
                if not (stored.startswith("$2b$") or stored.startswith("$2a$")):
                    dados = usuarios_db
                    dados[usuario]["hash"] = _hash_bcrypt(senha)
                    _salvar_usuarios(dados)
            session.clear()
            session["logado"]  = True
            session["usuario"] = usuario
            _gerar_csrf()   # novo token após login
            next_url = request.args.get("next") or url_for("dashboard")
            return redirect(next_url)
        else:
            session["tentativas_login"] = tentativas + 1
            restantes = MAX_TENTATIVAS_LOGIN - session["tentativas_login"]
            if restantes <= 0:
                erro = "Acesso bloqueado. Feche e abra o programa para tentar novamente."
            elif usuario and usuario not in usuarios_db:
                erro = f"Usuário '{usuario}' não encontrado."
            else:
                erro = "Usuário ou senha incorretos."

    tentativas_restantes = MAX_TENTATIVAS_LOGIN - session.get("tentativas_login", 0)
    return render_template("login.html", erro=erro,
                           usuario_digitado=usuario_digitado,
                           tentativas_restantes=tentativas_restantes)

@app.route("/logout", methods=["POST"])
def logout():
    _validar_csrf()
    usuario = session.get("usuario", "")
    session.clear()
    flash(f"Até logo, {usuario.capitalize()}! 👋", "success")
    return redirect(url_for("login"))

@app.route("/favicon.ico")
def favicon():
    from flask import send_from_directory
    static = os.path.join(BUNDLE_DIR, "static")
    if os.path.exists(os.path.join(static, "favicon.ico")):
        return send_from_directory(static, "favicon.ico")
    return "", 204


# ── Filtros de template ───────────────────────────────────────────────────────

@app.template_filter("brl")
def fmt_brl(v):
    try:
        return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "—"

@app.template_filter("pct")
def fmt_pct(v):
    try:
        f = float(v)
        return f"{'+'if f>0 else ''}{f:.1f}%"
    except Exception:
        return "—"

@app.template_filter("data_br")
def fmt_data(v):
    if isinstance(v, pd.Timestamp) and pd.notna(v):
        return v.strftime("%d/%m/%Y")
    return str(v) if v else "—"

def _safe(v, fallback=0):
    try:
        f = float(v)
        return f if f == f else fallback
    except Exception:
        return fallback

def parse_valor(s):
    try:
        s = str(s).strip().replace("R$", "").replace(" ", "").replace("\xa0", "")
        if not s or s in ("0", "0.0", "0,0"):
            return 0.0
        if "," in s and "." in s:
            s = s.replace(".", "").replace(",", ".")
        elif "," in s:
            s = s.replace(",", ".")
        else:
            partes = s.split(".")
            if len(partes) == 2 and len(partes[1]) == 3:
                s = s.replace(".", "")
            elif len(partes) > 2:
                if len(partes[-1]) <= 2:
                    s = "".join(partes[:-1]) + "." + partes[-1]
                else:
                    s = s.replace(".", "")
        return float(s)
    except Exception:
        return 0.0

def _limpar_backups_antigos(max_backups: int = 15):
    from db import DATA_DIR
    backup_dir = os.path.join(DATA_DIR, "backups")
    if not os.path.exists(backup_dir):
        return
    arquivos = sorted(
        [os.path.join(backup_dir, f) for f in os.listdir(backup_dir) if f.endswith(".xlsx")],
        key=os.path.getmtime
    )
    while len(arquivos) > max_backups:
        try:
            os.remove(arquivos.pop(0))
        except OSError:
            break

def _gerar_alertas(dados):
    from config import ALERTAS_SAUDE
    alertas = []
    hoje = _agora()
    df_man = dados["Manejo"]
    for tipo, dias in ALERTAS_SAUDE.items():
        df_t = df_man[df_man["Tipo"] == tipo] if not df_man.empty else pd.DataFrame()
        if df_t.empty:
            alertas.append({"nivel": "warning", "msg": f"Nenhum registro de {tipo}."})
            continue
        ultima = df_t["Data"].dropna().max()
        if pd.isna(ultima):
            continue
        d = (hoje - ultima.to_pydatetime()).days
        if d > dias:
            alertas.append({"nivel": "danger",
                             "msg": f"{tipo} atrasada! Última: {ultima.strftime('%d/%m/%Y')} ({d} dias)"})
    r_fin = _get_resumo_cache()
    if r_fin["resultado_realizado"] < 0:
        alertas.append({"nivel": "danger", "msg": f"Resultado negativo: {fmt_brl(r_fin['resultado_realizado'])}"})
    if r_fin["estoque"] > 0:
        alertas.append({"nivel": "info", "msg": f"Break-even do estoque: {fmt_brl(r_fin['break_even'])}/cabeça"})
    return alertas

def _calc_anual(dados):
    result = []
    anos = set()
    for df in dados.values():
        if not df.empty and "Data" in df.columns:
            anos |= set(df["Data"].dropna().dt.year.astype(int))
    for ano in sorted(anos):
        def soma(df, col="Valor Total (R$)", _ano=ano):
            if df.empty or "Data" not in df.columns:
                return 0
            mask = df["Data"].notna() & (df["Data"].dt.year == _ano)
            return float(df.loc[mask, col].sum()) if col in df.columns else 0
        tc = soma(dados["Compras"])
        tg = soma(dados["Gastos"])
        tv = soma(dados["Vendas"])
        custo = tc + tg
        lucro = tv - custo
        result.append({
            "ano": int(ano), "compras": tc, "gastos": tg, "custo": custo,
            "vendas": tv, "lucro": lucro,
            "roi": round(lucro / custo * 100, 1) if custo > 0 else 0,
            "positivo": lucro >= 0,
        })
    return result

def _salvar_venda(f, dados, idx=None):
    data    = f.get("data", _agora().strftime("%d/%m/%Y"))
    cabecas = int(f.get("cabecas", 0) or 0)
    valor   = parse_valor(f.get("valor", 0))
    arroba  = parse_valor(f.get("arroba") or "0")
    desc    = f.get("descricao", "").strip()

    if cabecas <= 0:
        cabecas = 1
    if valor < 0:
        valor = 0.0

    qtd_mae    = int(f.get("qtd_mae",    0) or 0)
    qtd_deyvid = int(f.get("qtd_deyvid", 0) or 0)
    qtd_nilson = int(f.get("qtd_nilson", 0) or 0)
    soma = qtd_mae + qtd_deyvid + qtd_nilson
    if soma == 0:
        base = cabecas // 3
        qtd_mae    = base
        qtd_deyvid = base
        qtd_nilson = cabecas - base * 2
    elif soma != cabecas:
        fator = cabecas / soma
        qtd_mae    = round(qtd_mae    * fator)
        qtd_deyvid = round(qtd_deyvid * fator)
        qtd_nilson = cabecas - qtd_mae - qtd_deyvid

    val_cab    = round(valor / cabecas, 2) if cabecas > 0 else 0
    val_mae    = round(valor * qtd_mae    / cabecas, 2) if cabecas > 0 else 0
    val_deyvid = round(valor * qtd_deyvid / cabecas, 2) if cabecas > 0 else 0
    val_nilson = round(valor - val_mae - val_deyvid, 2)

    try:
        data_ts = pd.Timestamp(datetime.strptime(data, "%d/%m/%Y"))
    except Exception:
        try:
            data_ts = pd.Timestamp(datetime.strptime(data, "%Y-%m-%d"))
        except Exception:
            data_ts = pd.Timestamp.now()

    cmp_v   = calcular_cmp_ate_data(dados["Compras"], data_ts)
    gpcab_v = calcular_gpcab_ate_data(
        dados["Gastos"], data_ts,
        dados["Compras"], dados["Vendas"], dados["Manejo"]
    )
    ctcab_v = round(cmp_v + gpcab_v, 2)

    c_mae    = round(qtd_mae    * ctcab_v, 2)
    c_deyvid = round(qtd_deyvid * ctcab_v, 2)
    c_nilson = round(qtd_nilson * ctcab_v, 2)

    linha = [data, cabecas, valor, val_cab, arroba,
             qtd_mae, qtd_deyvid, qtd_nilson,
             val_mae, val_deyvid, val_nilson,
             c_mae, c_deyvid, c_nilson,
             round(val_mae - c_mae, 2), round(val_deyvid - c_deyvid, 2), round(val_nilson - c_nilson, 2),
             ctcab_v, desc]

    cols = ["Data", "Qtd Cabeças", "Valor Total (R$)", "Valor/Cabeça (R$)", "Valor Arroba (R$)",
            "Qtd Mae", "Qtd Deyvid", "Qtd Nilson",
            "Valor Mae (R$)", "Valor Deyvid (R$)", "Valor Nilson (R$)",
            "Custo Mae (R$)", "Custo Deyvid (R$)", "Custo Nilson (R$)",
            "Resultado Mae (R$)", "Resultado Deyvid (R$)", "Resultado Nilson (R$)",
            "CMP no momento (R$)", "Descrição"]

    if idx is None:
        salvar_linha("Vendas", linha)
    else:
        df = carregar_aba("Vendas")
        for i, col in enumerate(cols):
            if col in df.columns:
                df.at[idx, col] = linha[i]
        if "Data" in df.columns:
            df.at[idx, "Data"] = pd.to_datetime(data, dayfirst=True, errors="coerce")
        reescrever_aba("Vendas", df)


# ══════════════════════════════════════════════════════════════════════════════
#  DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/")
@login_required
def dashboard():
    dados = _get_dados_cache()
    r = _get_resumo_cache()
    membros_r      = calcular_todos_membros(dados["Vendas"], dados["Compras"], dados["Gastos"], dados["Manejo"])
    estoque_membro = calcular_estoque_por_membro(dados["Compras"], dados["Vendas"], dados["Manejo"])
    recentes = []
    for _, row in dados["Compras"].tail(3).iterrows():
        ts = row.get("Data")
        recentes.append({"tipo": "Compra", "cor": "compra", "data": fmt_data(ts),
                          "_ts": ts if pd.notna(ts) else pd.Timestamp.min,
                          "desc": row.get("Descrição", ""), "val": fmt_brl(row.get("Valor Total (R$)", 0))})
    for _, row in dados["Gastos"].tail(2).iterrows():
        ts = row.get("Data")
        recentes.append({"tipo": "Gasto", "cor": "gasto", "data": fmt_data(ts),
                          "_ts": ts if pd.notna(ts) else pd.Timestamp.min,
                          "desc": row.get("Descrição", ""), "val": fmt_brl(row.get("Valor Total (R$)", 0))})
    for _, row in dados["Vendas"].tail(3).iterrows():
        ts = row.get("Data")
        recentes.append({"tipo": "Venda", "cor": "venda", "data": fmt_data(ts),
                          "_ts": ts if pd.notna(ts) else pd.Timestamp.min,
                          "desc": row.get("Descrição", ""), "val": fmt_brl(row.get("Valor Total (R$)", 0))})
    recentes.sort(key=lambda x: x["_ts"], reverse=True)
    for rec in recentes:
        rec.pop("_ts", None)
    return render_template("dashboard.html", r=r, membros=membros_r,
                           estoque_membro=estoque_membro, recentes=recentes[:6],
                           alertas=_gerar_alertas(dados),
                           NOMES=NOMES_MEMBROS, EMOJIS=EMOJIS_MEMBROS, MEMBROS=MEMBROS)


# ══════════════════════════════════════════════════════════════════════════════
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
#  APIs — CALENDÁRIO DE MANEJO / WHATSAPP / HISTÓRICO DE ARROBA
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/calendario-manejo")
@login_required
def api_calendario_manejo():
    """
    Retorna próximas intervenções previstas + eventos históricos para o
    calendário visual de manejo do dashboard.
    """
    from config import ALERTAS_SAUDE
    dados  = _get_dados_cache()
    df_man = dados["Manejo"]
    hoje   = _agora()

    proximas = []
    for tipo, intervalo_dias in ALERTAS_SAUDE.items():
        ultima_data   = None
        dias_passados = None
        if not df_man.empty and "Tipo" in df_man.columns:
            df_t = df_man[df_man["Tipo"] == tipo]
            if not df_t.empty:
                ultima_ts = df_t["Data"].dropna().max()
                if pd.notna(ultima_ts):
                    ultima_data   = ultima_ts.strftime("%d/%m/%Y")
                    dias_passados = (hoje - ultima_ts.to_pydatetime()).days

        if ultima_data and dias_passados is not None:
            dias_restantes = intervalo_dias - dias_passados
            data_prevista  = (hoje + timedelta(days=max(0, dias_restantes))).strftime("%Y-%m-%d")
            status = ("atrasado" if dias_passados > intervalo_dias else
                      "urgente"  if dias_restantes <= 14 else
                      "proximo"  if dias_restantes <= 30 else "ok")
        else:
            data_prevista  = hoje.strftime("%Y-%m-%d")
            dias_restantes = 0
            status         = "sem_registro"

        proximas.append({
            "tipo":            tipo,
            "intervalo_dias":  intervalo_dias,
            "ultima_data":     ultima_data,
            "dias_passados":   dias_passados,
            "dias_restantes":  dias_restantes,
            "data_prevista":   data_prevista,
            "status":          status,
        })

    eventos = []
    if not df_man.empty:
        for _, row in df_man.iterrows():
            data_ev = row.get("Data")
            if pd.isna(data_ev):
                continue
            eventos.append({
                "data":    data_ev.strftime("%Y-%m-%d"),
                "tipo":    str(row.get("Tipo", "")    or ""),
                "cabecas": int(row.get("Qtd Cabeças", 0) or 0),
                "desc":    str(row.get("Descrição", "")  or ""),
                "resp":    str(row.get("Responsável", "") or ""),
            })

    return jsonify({
        "proximas": proximas,
        "eventos":  eventos,
        "hoje":     hoje.strftime("%Y-%m-%d"),
    })


@app.route("/api/historico-arroba")
@login_required
def api_historico_arroba():
    """
    Histórico de preços de arroba registrados nas vendas, com média móvel
    e indicador de tendência para o gráfico do dashboard.
    """
    dados = _get_dados_cache()
    df_v  = dados["Vendas"]

    if df_v.empty:
        return jsonify({"labels": [], "precos": [], "medias": [], "total": 0})

    df = df_v[
        df_v["Data"].notna() &
        df_v["Valor Arroba (R$)"].notna() &
        (df_v["Valor Arroba (R$)"] > 0)
    ].copy()

    if df.empty:
        return jsonify({"labels": [], "precos": [], "medias": [], "total": 0})

    df      = df.sort_values("Data")
    precos  = [round(float(v), 2) for v in df["Valor Arroba (R$)"].tolist()]
    labels  = df["Data"].dt.strftime("%d/%m/%Y").tolist()

    # Média móvel de 3 pontos
    medias = []
    for i in range(len(precos)):
        inicio = max(0, i - 1)
        fim    = min(len(precos), i + 2)
        medias.append(round(sum(precos[inicio:fim]) / (fim - inicio), 2))

    # Tendência: segunda metade vs primeira metade
    metade = len(precos) // 2
    if metade > 0:
        m_ini = sum(precos[:metade]) / metade
        m_fim = sum(precos[metade:]) / (len(precos) - metade)
        tendencia = ("alta"   if m_fim > m_ini * 1.02 else
                     "baixa"  if m_fim < m_ini * 0.98 else "estavel")
    else:
        tendencia = "estavel"

    return jsonify({
        "labels":    labels,
        "precos":    precos,
        "medias":    medias,
        "total":     len(precos),
        "min":       round(min(precos), 2),
        "max":       round(max(precos), 2),
        "medio":     round(sum(precos) / len(precos), 2),
        "ultimo":    precos[-1],
        "tendencia": tendencia,
    })


@app.route("/api/config-whatsapp", methods=["GET", "POST"])
@login_required
def api_config_whatsapp():
    """GET → config salva (sem expor apikey). POST → salva telefone + apikey."""
    usuarios = _carregar_usuarios()
    usuario  = session["usuario"]

    if request.method == "GET":
        cfg = usuarios.get(usuario, {}).get("whatsapp", {})
        return jsonify({
            "telefone":          cfg.get("telefone", ""),
            "apikey_configurada": bool(cfg.get("apikey")),
            "alertas_ativos":    cfg.get("alertas_ativos", True),
        })

    data     = request.get_json(silent=True) or {}
    telefone = str(data.get("telefone", "")).strip()
    apikey   = str(data.get("apikey",   "")).strip()
    alertas  = bool(data.get("alertas_ativos", True))

    if usuario not in usuarios:
        usuarios[usuario] = {}
    usuarios[usuario]["whatsapp"] = {
        "telefone": telefone,
        "apikey":   apikey,
        "alertas_ativos": alertas,
    }
    _salvar_usuarios(usuarios)
    return jsonify({"ok": True})


@app.route("/api/enviar-lembrete-whatsapp", methods=["POST"])
@login_required
def api_enviar_lembrete_whatsapp():
    """Envia mensagem via CallMeBot (gratuito). Body: {telefone, apikey, msg}"""
    import urllib.request, urllib.parse
    data     = request.get_json(silent=True) or {}
    telefone = str(data.get("telefone", "")).strip().replace(" ", "").replace("+", "")
    apikey   = str(data.get("apikey",   "")).strip()
    msg      = str(data.get("msg",      "")).strip()

    if not telefone or not apikey or not msg:
        return jsonify({"ok": False, "erro": "Campos obrigatórios: telefone, apikey, msg"})

    url = (
        "https://api.callmebot.com/whatsapp.php"
        f"?phone={urllib.parse.quote(telefone)}"
        f"&text={urllib.parse.quote(msg)}"
        f"&apikey={urllib.parse.quote(apikey)}"
    )
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            body = resp.read().decode("utf-8", errors="ignore")
        ok = "message queued" in body.lower() or resp.status == 200
        return jsonify({"ok": ok, "resposta": body[:300]})
    except Exception as e:
        return jsonify({"ok": False, "erro": str(e)})


@app.route("/sw.js")
def service_worker():
    """Service worker servido da raiz para scope completo."""
    from flask import make_response
    try:
        resp = make_response(send_file(os.path.join(BASE_DIR, "sw.js")))
        resp.headers["Content-Type"]            = "application/javascript"
        resp.headers["Cache-Control"]           = "no-cache, no-store, must-revalidate"
        resp.headers["Service-Worker-Allowed"]  = "/"
        return resp
    except Exception:
        return "", 404


@app.route("/manifest.json")
def manifest():
    """Manifesto PWA."""
    try:
        return send_file(os.path.join(BASE_DIR, "manifest.json"),
                         mimetype="application/manifest+json")
    except Exception:
        return "", 404


# ══════════════════════════════════════════════════════════════════════════════
#  COMPRAS
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/compras")
@login_required
def compras():
    dados = _get_dados_cache()
    df = dados["Compras"]
    ordem = request.args.get("ordem", "desc")
    if not df.empty and "Data" in df.columns:
        df = df.sort_values("Data", ascending=(ordem == "asc"), na_position="last")
    rows = []
    for real_idx, row in (df.iterrows() if not df.empty else []):
        d = row.to_dict()
        d["Data"] = fmt_data(d.get("Data"))
        d["_idx"] = int(real_idx)
        rows.append(d)
    return render_template("lista.html", titulo="Compras 🛒", secao="compras", aba="Compras",
                           colunas=["Data","Qtd Cabeças","Valor Total (R$)","Valor/Cabeça (R$)",
                                    "Qtd Mae","Qtd Deyvid","Qtd Nilson","Descrição","Registrado Por"],
                           rows=rows, ordem=ordem)

@app.route("/compras/nova", methods=["GET", "POST"])
@login_required
def nova_compra():
    dados = _get_dados_cache()
    cmp_atual = calcular_cmp(dados["Compras"])
    if request.method == "POST":
        _validar_csrf()
        f = request.form
        data    = f.get("data", _agora().strftime("%d/%m/%Y"))
        cabecas = int(f.get("cabecas", 0) or 0)
        valor   = parse_valor(f.get("valor", 0))
        desc    = f.get("descricao", "").strip()
        membro  = f.get("membro", "")
        if cabecas <= 0:
            flash("Informe ao menos 1 cabeça.", "error")
            return redirect(url_for("nova_compra"))
        qtd_mae    = int(f.get("qtd_mae",    0) or 0)
        qtd_deyvid = int(f.get("qtd_deyvid", 0) or 0)
        qtd_nilson = int(f.get("qtd_nilson", 0) or 0)
        soma = qtd_mae + qtd_deyvid + qtd_nilson
        if soma == 0:
            base = cabecas // 3
            qtd_mae = qtd_deyvid = base
            qtd_nilson = cabecas - base * 2
        elif soma != cabecas:
            fator = cabecas / soma
            qtd_mae    = round(qtd_mae    * fator)
            qtd_deyvid = round(qtd_deyvid * fator)
            qtd_nilson = cabecas - qtd_mae - qtd_deyvid
        val_cab = round(valor / cabecas, 2) if cabecas > 0 else 0
        salvar_linha("Compras", [data, cabecas, valor, val_cab, qtd_mae, qtd_deyvid, qtd_nilson, desc, membro])
        flash(f"Compra registrada! {cabecas} cabeças por {fmt_brl(valor)}", "success")
        return redirect(url_for("compras"))
    return render_template("form_compra.html", modo="nova", cmp_atual=cmp_atual,
                           row=None, idx=None, MEMBROS=MEMBROS, NOMES=NOMES_MEMBROS,
                           hoje=_agora().strftime("%Y-%m-%d"))

@app.route("/compras/editar/<int:idx>", methods=["GET", "POST"])
@login_required
def editar_compra(idx):
    df = carregar_aba("Compras")
    if df.empty or idx >= len(df):
        flash("Registro não encontrado.", "error")
        return redirect(url_for("compras"))
    if request.method == "POST":
        _validar_csrf()
        f = request.form
        data    = f.get("data", "")
        cabecas = int(f.get("cabecas", 0) or 0)
        valor   = parse_valor(f.get("valor", 0))
        desc    = f.get("descricao", "").strip()
        membro  = f.get("membro", "")
        if cabecas <= 0:
            flash("Informe ao menos 1 cabeça.", "error")
            return redirect(url_for("editar_compra", idx=idx))
        qtd_mae    = int(f.get("qtd_mae",    0) or 0)
        qtd_deyvid = int(f.get("qtd_deyvid", 0) or 0)
        qtd_nilson = int(f.get("qtd_nilson", 0) or 0)
        soma = qtd_mae + qtd_deyvid + qtd_nilson
        if soma == 0:
            base = cabecas // 3
            qtd_mae = qtd_deyvid = base
            qtd_nilson = cabecas - base * 2
        elif soma != cabecas:
            fator = cabecas / soma
            qtd_mae    = round(qtd_mae    * fator)
            qtd_deyvid = round(qtd_deyvid * fator)
            qtd_nilson = cabecas - qtd_mae - qtd_deyvid
        val_cab = round(valor / cabecas, 2) if cabecas > 0 else 0
        fazer_backup()
        _limpar_backups_antigos()
        updates = {"Data": pd.to_datetime(data, dayfirst=True, errors="coerce"),
                   "Qtd Cabeças": cabecas, "Valor Total (R$)": valor,
                   "Valor/Cabeça (R$)": val_cab, "Qtd Mae": qtd_mae,
                   "Qtd Deyvid": qtd_deyvid, "Qtd Nilson": qtd_nilson,
                   "Descrição": desc, "Registrado Por": membro}
        for col, val in updates.items():
            if col in df.columns:
                df.at[idx, col] = val
            else:
                df[col] = None; df.at[idx, col] = val
        reescrever_aba("Compras", df)
        flash("Compra atualizada!", "success")
        return redirect(url_for("compras"))
    row = df.iloc[idx].to_dict()
    row["Data"] = fmt_data(row.get("Data"))
    row["data_input"] = df.iloc[idx]["Data"].strftime("%Y-%m-%d") if pd.notna(df.iloc[idx]["Data"]) else ""
    # Fix: coluna correta para o template
    row["Qtd Geane"] = row.get("Qtd Mae", 0)
    return render_template("form_compra.html", modo="editar", row=row, idx=idx,
                           cmp_atual=calcular_cmp(df), MEMBROS=MEMBROS, NOMES=NOMES_MEMBROS,
                           hoje=_agora().strftime("%Y-%m-%d"))


# ══════════════════════════════════════════════════════════════════════════════
#  GASTOS
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/gastos")
@login_required
def gastos():
    dados = _get_dados_cache()
    df = dados["Gastos"]
    ordem = request.args.get("ordem", "desc")
    if not df.empty and "Data" in df.columns:
        df = df.sort_values("Data", ascending=(ordem == "asc"), na_position="last")
    rows = []
    for real_idx, row in (df.iterrows() if not df.empty else []):
        d = row.to_dict()
        d["Data"] = fmt_data(d.get("Data"))
        d["_idx"] = int(real_idx)
        rows.append(d)
    return render_template("lista.html", titulo="Gastos 💸", secao="gastos", aba="Gastos",
                           colunas=["Data","Tipo","Descrição","Valor Total (R$)",
                                    "Qtd Cabeças","Valor/Cabeça (R$)","Registrado Por"],
                           rows=rows, ordem=ordem)

@app.route("/gastos/novo", methods=["GET", "POST"])
@login_required
def novo_gasto():
    dados = _get_dados_cache()
    estoque = calcular_estoque(dados["Compras"], dados["Vendas"], dados["Manejo"])
    gpcab   = calcular_gpcab(dados["Gastos"], dados["Compras"], dados["Vendas"], dados["Manejo"])
    if request.method == "POST":
        _validar_csrf()
        f = request.form
        data   = f.get("data", _agora().strftime("%d/%m/%Y"))
        tipo   = f.get("tipo", "")
        desc   = f.get("descricao", "").strip()
        valor  = parse_valor(f.get("valor", 0))
        cab    = int(f.get("cabecas", estoque) or estoque)
        membro = f.get("membro", "")
        if cab <= 0:
            cab = max(1, estoque)
        v_cab = round(valor / cab, 4) if cab > 0 else 0
        salvar_linha("Gastos", [data, tipo, desc, valor, cab, v_cab, membro])
        flash(f"Gasto registrado! {fmt_brl(valor)} ({tipo})", "success")
        return redirect(url_for("gastos"))
    return render_template("form_gasto.html", estoque=estoque, gpcab=gpcab,
                           TIPOS=TIPOS_GASTO, MEMBROS=MEMBROS, NOMES=NOMES_MEMBROS,
                           hoje=_agora().strftime("%Y-%m-%d"))

@app.route("/gastos/editar/<int:idx>", methods=["GET", "POST"])
@login_required
def editar_gasto(idx):
    dados   = _get_dados_cache()
    df      = carregar_aba("Gastos")
    estoque = calcular_estoque(dados["Compras"], dados["Vendas"], dados["Manejo"])
    gpcab   = calcular_gpcab(dados["Gastos"], dados["Compras"], dados["Vendas"], dados["Manejo"])
    if df.empty or idx >= len(df):
        flash("Registro não encontrado.", "error")
        return redirect(url_for("gastos"))
    if request.method == "POST":
        _validar_csrf()
        f      = request.form
        data   = f.get("data", "")
        tipo   = f.get("tipo", "")
        desc   = f.get("descricao", "").strip()
        valor  = parse_valor(f.get("valor", 0))
        cab    = int(f.get("cabecas", estoque) or estoque)
        membro = f.get("membro", "")
        if cab <= 0:
            cab = max(1, estoque)
        v_cab = round(valor / cab, 4) if cab > 0 else 0
        fazer_backup()
        _limpar_backups_antigos()
        updates = {"Data": pd.to_datetime(data, dayfirst=True, errors="coerce"),
                   "Tipo": tipo, "Descrição": desc,
                   "Valor Total (R$)": valor, "Qtd Cabeças": cab,
                   "Valor/Cabeça (R$)": v_cab, "Registrado Por": membro}
        for col, val in updates.items():
            if col in df.columns:
                df.at[idx, col] = val
            else:
                df[col] = None; df.at[idx, col] = val
        reescrever_aba("Gastos", df)
        flash("Gasto atualizado!", "success")
        return redirect(url_for("gastos"))
    row = df.iloc[idx].to_dict()
    row["Data"] = fmt_data(row.get("Data"))
    row["data_input"] = df.iloc[idx]["Data"].strftime("%Y-%m-%d") if pd.notna(df.iloc[idx].get("Data")) else ""
    return render_template("form_gasto.html", modo="editar", row=row, idx=idx,
                           estoque=estoque, gpcab=gpcab,
                           TIPOS=TIPOS_GASTO, MEMBROS=MEMBROS, NOMES=NOMES_MEMBROS,
                           hoje=_agora().strftime("%Y-%m-%d"))


# ══════════════════════════════════════════════════════════════════════════════
#  VENDAS
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/vendas")
@login_required
def vendas():
    dados = _get_dados_cache()
    df = dados["Vendas"]
    ordem = request.args.get("ordem", "desc")
    if not df.empty and "Data" in df.columns:
        df = df.sort_values("Data", ascending=(ordem == "asc"), na_position="last")
    rows = []
    for real_idx, row in (df.iterrows() if not df.empty else []):
        d = row.to_dict()
        d["Data"] = fmt_data(d.get("Data"))
        d["_idx"] = int(real_idx)
        rows.append(d)
    return render_template("lista.html", titulo="Vendas 🤝", secao="vendas", aba="Vendas",
                           colunas=["Data","Qtd Cabeças","Valor Total (R$)","Valor/Cabeça (R$)",
                                    "Valor Arroba (R$)","Qtd Mae","Qtd Deyvid","Qtd Nilson",
                                    "Valor Mae (R$)","Valor Deyvid (R$)","Valor Nilson (R$)","Descrição"],
                           rows=rows, ordem=ordem)

@app.route("/vendas/nova", methods=["GET", "POST"])
@login_required
def nova_venda():
    dados = _get_dados_cache()
    r_fin = _get_resumo_cache()
    if request.method == "POST":
        _validar_csrf()
        cabecas = int(request.form.get("cabecas", 0) or 0)
        if cabecas <= 0:
            flash("Informe ao menos 1 cabeça.", "error")
            return redirect(url_for("nova_venda"))
        _salvar_venda(request.form, dados)
        flash("Venda registrada!", "success")
        return redirect(url_for("vendas"))
    return render_template("form_venda.html", modo="nova", row=None, idx=None, r_fin=r_fin,
                           MEMBROS=MEMBROS, NOMES=NOMES_MEMBROS,
                           hoje=_agora().strftime("%Y-%m-%d"))

@app.route("/vendas/editar/<int:idx>", methods=["GET", "POST"])
@login_required
def editar_venda(idx):
    dados = _get_dados_cache()
    df    = carregar_aba("Vendas")
    if df.empty or idx >= len(df):
        flash("Registro não encontrado.", "error")
        return redirect(url_for("vendas"))
    r_fin = _get_resumo_cache()
    if request.method == "POST":
        _validar_csrf()
        fazer_backup()
        _limpar_backups_antigos()
        _salvar_venda(request.form, dados, idx=idx)
        flash("Venda atualizada!", "success")
        return redirect(url_for("vendas"))
    row = df.iloc[idx].to_dict()
    row["Data"] = fmt_data(row.get("Data"))
    row["data_input"] = df.iloc[idx]["Data"].strftime("%Y-%m-%d") if pd.notna(df.iloc[idx]["Data"]) else ""
    return render_template("form_venda.html", modo="editar", row=row, idx=idx, r_fin=r_fin,
                           MEMBROS=MEMBROS, NOMES=NOMES_MEMBROS,
                           hoje=_agora().strftime("%Y-%m-%d"))


# ══════════════════════════════════════════════════════════════════════════════
#  MANEJO
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/manejo")
@login_required
def manejo():
    dados = _get_dados_cache()
    df = dados["Manejo"]
    rows = []
    for real_idx, row in (df.iterrows() if not df.empty else []):
        d = row.to_dict()
        d["Data"] = fmt_data(d.get("Data"))
        d["_idx"] = int(real_idx)
        rows.append(d)
    return render_template("lista.html", titulo="Manejo 🩺", secao="manejo", aba="Manejo",
                           colunas=["Data","Tipo","Qtd Cabeças","Descrição","Responsável"],
                           rows=rows)

@app.route("/manejo/novo", methods=["GET", "POST"])
@login_required
def novo_manejo():
    dados   = _get_dados_cache()
    estoque = calcular_estoque(dados["Compras"], dados["Vendas"], dados["Manejo"])
    if request.method == "POST":
        _validar_csrf()
        f = request.form
        salvar_linha("Manejo", [f.get("data"), f.get("tipo"), int(f.get("cabecas", 0) or 0),
                                f.get("descricao", "").strip(), f.get("responsavel", "")])
        flash(f"Manejo registrado! ({f.get('tipo')})", "success")
        return redirect(url_for("manejo"))
    return render_template("form_manejo.html", estoque=estoque, TIPOS=TIPOS_MANEJO,
                           MEMBROS=MEMBROS, NOMES=NOMES_MEMBROS,
                           hoje=_agora().strftime("%Y-%m-%d"))


# ══════════════════════════════════════════════════════════════════════════════
#  RELATÓRIOS
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/relatorios")
@login_required
def relatorios():
    dados = _get_dados_cache()
    r_fin = _get_resumo_cache()
    mbr   = calcular_todos_membros(dados["Vendas"], dados["Compras"], dados["Gastos"], dados["Manejo"])
    gastos_tipo = calcular_gasto_por_tipo(dados["Gastos"])
    extras      = calcular_indicadores_extras(
        dados["Compras"], dados["Gastos"], dados["Vendas"], dados["Manejo"], r_fin["ctcab"]
    )
    return render_template("relatorios.html", r=r_fin, mbr=mbr,
                           alertas=_gerar_alertas(dados), anual=_calc_anual(dados),
                           gastos_tipo=gastos_tipo, extras=extras,
                           MEMBROS=MEMBROS, NOMES=NOMES_MEMBROS, EMOJIS=EMOJIS_MEMBROS)


# ══════════════════════════════════════════════════════════════════════════════
#  EXCLUIR
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/excluir/<aba>/<int:idx>", methods=["POST"])
@login_required
def excluir(aba, idx):
    _validar_csrf()
    fazer_backup()
    _limpar_backups_antigos()
    df = carregar_aba(aba)
    if not df.empty and idx < len(df):
        df = df.drop(df.index[idx]).reset_index(drop=True)
        reescrever_aba(aba, df)
        flash("Registro excluído.", "warning")
    return redirect(url_for({"Compras": "compras", "Gastos": "gastos",
                              "Vendas": "vendas", "Manejo": "manejo"}.get(aba, "dashboard")))


# ══════════════════════════════════════════════════════════════════════════════
#  IMPORTAR
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/importar", methods=["GET", "POST"])
@login_required
def importar():
    if request.method == "POST":
        _validar_csrf()
        arquivo = request.files.get("arquivo")
        if not arquivo or not arquivo.filename.endswith(".xlsx"):
            flash("Envie um arquivo .xlsx válido.", "error")
            return redirect(url_for("importar"))
        from db import safe_val
        from openpyxl import load_workbook
        tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
        arquivo.save(tmp.name)
        tmp.close()
        try:
            wb   = load_workbook(tmp.name, data_only=True)
            anos = sorted([s for s in wb.sheetnames if s.isdigit()])
            if not anos:
                flash("Nenhuma aba de ano encontrada.", "warning")
                return redirect(url_for("importar"))
            nc = ng = nv = 0
            detalhes = []
            for ano in anos:
                df_raw = pd.read_excel(tmp.name, sheet_name=ano, header=None)
                def _f(r, c):
                    try:
                        x = safe_val(df_raw, r, c)
                        return float(str(x).replace(",", ".")) if x not in (None, "") else 0.0
                    except Exception:
                        return 0.0
                cab_c = _f(0, 1)
                preco_c = _f(0, 10)
                if cab_c > 0 and preco_c > 0:
                    base = int(cab_c) // 3
                    salvar_linha("Compras", [f"01/01/{ano}", int(cab_c), preco_c,
                                             round(preco_c / int(cab_c), 2),
                                             base, base, int(cab_c) - base * 2,
                                             f"Nelore/Garrotes - Importado {ano}", "Importação"])
                    nc += 1
                    detalhes.append({"tipo": "compra", "ano": ano,
                                     "msg": f"Compra: {int(cab_c)} cabeças — R$ {preco_c:,.2f}"})
                gastos_ano = 0
                for ri in range(1, len(df_raw)):
                    vg = _f(ri, 6)
                    dg = safe_val(df_raw, ri, 7)
                    if vg > 0:
                        salvar_linha("Gastos", [f"01/01/{ano}", "Manutenção/Outros",
                                                str(dg).strip() if dg else "", vg, 0, 0, "Importação"])
                        ng += 1; gastos_ano += 1
                if gastos_ano:
                    detalhes.append({"tipo": "gasto", "ano": ano, "msg": f"{gastos_ano} gastos importados"})
                mae_v = _f(1, 15); dev_v = _f(2, 15); nil_v = _f(3, 15)
                mae_q = _f(1, 19); dev_q = _f(2, 19); nil_q = _f(3, 19)
                tv = mae_v + dev_v + nil_v
                tq = int(mae_q + dev_q + nil_q)
                raw_dv = safe_val(df_raw, 1, 17)
                try:
                    data_v = pd.Timestamp(raw_dv).strftime("%d/%m/%Y") if raw_dv else f"31/12/{ano}"
                except Exception:
                    data_v = f"31/12/{ano}"
                if tv > 0:
                    salvar_linha("Vendas", [data_v, tq, tv,
                                            round(tv / tq, 2) if tq else 0, _f(0, 12),
                                            int(mae_q), int(dev_q), int(nil_q),
                                            mae_v, dev_v, nil_v,
                                            0, 0, 0, 0, 0, 0, 0, f"Importado de {ano}"])
                    nv += 1
                    detalhes.append({"tipo": "venda", "ano": ano,
                                     "msg": f"Venda: {tq} cabeças — R$ {tv:,.2f}"})
            return render_template("importar.html", concluido=True, anos=anos,
                                   nc=nc, ng=ng, nv=nv, detalhes=detalhes)
        except Exception as e:
            flash(f"Erro na importação: {e}", "error")
            return redirect(url_for("importar"))
        finally:
            os.unlink(tmp.name)
    return render_template("importar.html", concluido=False, anos=[], detalhes=[])


# ══════════════════════════════════════════════════════════════════════════════
#  EXPORTAR / BACKUP
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/exportar")
@login_required
def exportar():
    from db import DATA_DIR
    nome = exportar_relatorio_excel()
    nome_abs = nome if os.path.isabs(nome) else os.path.join(DATA_DIR, nome)
    return send_file(nome_abs, as_attachment=True,
                     download_name=f"relatorio_gado_{_agora().strftime('%Y%m%d')}.xlsx")

@app.route("/backup", methods=["POST"])
@login_required
def backup():
    _validar_csrf()
    nome = fazer_backup()
    _limpar_backups_antigos()
    flash(f"Backup salvo: {nome}", "success")
    return redirect(url_for("dashboard"))


# ══════════════════════════════════════════════════════════════════════════════
#  USUÁRIOS E CONFIGURAÇÕES
# ══════════════════════════════════════════════════════════════════════════════

def _usuarios_path():
    from db import DATA_DIR
    return os.path.join(DATA_DIR, "usuarios.json")

def _carregar_usuarios():
    import json
    caminho = _usuarios_path()
    if os.path.exists(caminho):
        try:
            with open(caminho, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    dados = {u: {"hash": h, "criado": _agora().strftime("%d/%m/%Y")}
             for u, h in USUARIOS.items()}
    _salvar_usuarios(dados)
    return dados

def _salvar_usuarios(dados):
    import json
    with open(_usuarios_path(), "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

def _verificar_senha(usuario, senha):
    usuarios = _carregar_usuarios()
    if usuario not in usuarios:
        return False
    return _verificar_hash(senha, usuarios[usuario]["hash"])

@app.route("/configuracoes")
@login_required
def configuracoes():
    usuarios = _carregar_usuarios()
    return render_template("configuracoes.html", usuarios=usuarios)

@app.route("/configuracoes/trocar-senha", methods=["POST"])
@login_required
def trocar_senha():
    _validar_csrf()
    usuario = session["usuario"]
    atual   = request.form.get("senha_atual", "").strip()
    nova    = request.form.get("senha_nova",  "").strip()
    conf    = request.form.get("senha_conf",  "").strip()
    if not _verificar_senha(usuario, atual):
        flash("Senha atual incorreta.", "error")
        return redirect(url_for("configuracoes"))
    if len(nova) < 4:
        flash("A nova senha precisa ter pelo menos 4 caracteres.", "error")
        return redirect(url_for("configuracoes"))
    if nova != conf:
        flash("As senhas não coincidem.", "error")
        return redirect(url_for("configuracoes"))
    dados = _carregar_usuarios()
    dados[usuario]["hash"] = _hash_bcrypt(nova) if _bcrypt_disponivel() else _sha256(nova)
    _salvar_usuarios(dados)
    flash("✅ Senha alterada com sucesso!", "success")
    return redirect(url_for("configuracoes"))

@app.route("/configuracoes/adicionar-usuario", methods=["POST"])
@login_required
def adicionar_usuario():
    _validar_csrf()
    import re
    novo_user = request.form.get("usuario", "").strip().lower()
    senha     = request.form.get("senha",   "").strip()
    if not re.match(r"^[a-z]{2,20}$", novo_user):
        flash("Nome de usuário inválido (apenas letras, 2–20 caracteres).", "error")
        return redirect(url_for("configuracoes"))
    if len(senha) < 4:
        flash("A senha precisa ter pelo menos 4 caracteres.", "error")
        return redirect(url_for("configuracoes"))
    dados = _carregar_usuarios()
    if novo_user in dados:
        flash(f"Usuário '{novo_user}' já existe.", "error")
        return redirect(url_for("configuracoes"))
    dados[novo_user] = {
        "hash":   _hash_bcrypt(senha) if _bcrypt_disponivel() else _sha256(senha),
        "criado": _agora().strftime("%d/%m/%Y"),
    }
    _salvar_usuarios(dados)
    flash(f"✅ Usuário '{novo_user.capitalize()}' criado!", "success")
    return redirect(url_for("configuracoes"))

@app.route("/configuracoes/excluir-usuario", methods=["POST"])
@login_required
def excluir_usuario():
    _validar_csrf()
    alvo = request.form.get("usuario", "").strip().lower()
    if alvo == session["usuario"]:
        flash("Você não pode excluir sua própria conta.", "error")
        return redirect(url_for("configuracoes"))
    dados = _carregar_usuarios()
    if alvo not in dados:
        flash("Usuário não encontrado.", "error")
        return redirect(url_for("configuracoes"))
    del dados[alvo]
    _salvar_usuarios(dados)
    flash(f"Usuário '{alvo.capitalize()}' excluído.", "warning")
    return redirect(url_for("configuracoes"))

@app.route("/configuracoes/resetar-senha", methods=["POST"])
@login_required
def resetar_senha():
    _validar_csrf()
    alvo  = request.form.get("usuario",    "").strip().lower()
    senha = request.form.get("senha_nova", "").strip()
    if len(senha) < 4:
        flash("A senha precisa ter pelo menos 4 caracteres.", "error")
        return redirect(url_for("configuracoes"))
    dados = _carregar_usuarios()
    if alvo not in dados:
        flash("Usuário não encontrado.", "error")
        return redirect(url_for("configuracoes"))
    dados[alvo]["hash"] = _hash_bcrypt(senha) if _bcrypt_disponivel() else _sha256(senha)
    _salvar_usuarios(dados)
    flash(f"✅ Senha de '{alvo.capitalize()}' redefinida!", "success")
    return redirect(url_for("configuracoes"))


# ══════════════════════════════════════════════════════════════════════════════
#  VISITAS AO SÍTIO
# ══════════════════════════════════════════════════════════════════════════════

def _gerar_sugestoes_visita(f, estoque_esperado):
    sug = []
    gado_contado = int(f.get("gado_contado") or 0)
    if gado_contado > 0 and estoque_esperado > 0:
        if gado_contado < estoque_esperado:
            falt = estoque_esperado - gado_contado
            sug.append(f"⚠️ ALERTA: {falt} cabeça(s) não localizada(s)! Verificar pastagens vizinhas e cercas.")
        elif gado_contado > estoque_esperado:
            sug.append(f"ℹ️ {gado_contado - estoque_esperado} cabeça(s) a mais — possível animal de terceiro.")
    sal = f.get("sal_racao", "OK")
    if sal == "Baixo":   sug.append("🧂 Sal/Ração baixo — reabastecer nos próximos 2 a 3 dias.")
    elif sal == "Vazio": sug.append("🚨 Sal/Ração ESGOTADO — abastecer com urgência!")
    prot = f.get("proteinado", "OK")
    if prot == "Baixo":   sug.append("🟡 Proteinado baixo — repor em breve.")
    elif prot == "Vazio": sug.append("🚨 Proteinado ESGOTADO — comprar urgente!")
    mato = f.get("mato", "Limpo")
    if mato == "Precisa Capinar": sug.append("🌿 Vegetação crescida — programar roçagem.")
    elif mato == "Muito Mato":    sug.append("🌿 Mato excessivo — roçagem urgente!")
    grama = f.get("grama", "Boa")
    if grama == "Regular": sug.append("🌱 Pastagem regular — considerar rotação ou adubação.")
    elif grama == "Escassa": sug.append("🚨 Pastagem escassa — rotacionar IMEDIATAMENTE.")
    corrego = f.get("corrego", "Normal")
    if corrego == "Baixo": sug.append("💧 Água baixa — monitorar e preparar alternativa.")
    elif corrego == "Seco": sug.append("🚨 SEM ÁGUA — providenciar abastecimento urgente!")
    quintal = f.get("quintal", "OK")
    if quintal == "Precisa Atenção": sug.append("🏡 Quintal necessita atenção.")
    cisterna = f.get("cisterna", "OK")
    if cisterna == "Baixo": sug.append("🪣 Cisterna baixa — programar reabastecimento.")
    elif cisterna == "Vazia": sug.append("🚨 Cisterna VAZIA — abastecer imediatamente!")
    choveu = f.get("choveu", "nao") == "sim"
    try:
        mm = float(str(f.get("chuva_mm", "0") or "0").replace(",", "."))
    except Exception:
        mm = 0.0
    if choveu and mm >= 50:   sug.append(f"🌧️ Chuva forte ({mm:.0f}mm) — verificar erosão e cercas.")
    elif choveu and mm >= 15: sug.append(f"🌦️ Boa chuva ({mm:.0f}mm) — pastagem deve se recuperar.")
    elif choveu and mm > 0:   sug.append(f"🌂 Chuva leve ({mm:.0f}mm).")
    elif choveu:              sug.append("🌧️ Chuva registrada — anotar os mm na próxima vez.")
    else:                     sug.append("☀️ Sem chuva — acompanhar estiagem.")
    if not sug:
        sug.append("✅ Visita sem pendências — sítio em boas condições!")
    return " | ".join(sug)


@app.route("/visitas")
@login_required
def visitas():
    df = carregar_aba("Visitas")
    ordem = request.args.get("ordem", "desc")
    if not df.empty and "Data" in df.columns:
        df = df.sort_values("Data", ascending=(ordem == "asc"), na_position="last")
    alertas = []
    if not df.empty:
        ultima = df.iloc[0] if ordem == "desc" else df.iloc[-1]
        falt = int(ultima.get("Gado Faltando") or 0) if ultima.get("Gado Faltando") is not None else 0
        try: falt = int(falt)
        except Exception: falt = 0
        if falt > 0:
            alertas.append(("danger", f"⚠️ Na última visita, {falt} cabeça(s) estavam faltando!"))
        for campo, label in [("Sal/Ração", "Sal/Ração"), ("Proteinado", "Proteinado")]:
            v = str(ultima.get(campo, "OK") or "OK")
            if v == "Vazio":  alertas.append(("danger",  f"🚨 {label} ESGOTADO conforme última visita!"))
            elif v == "Baixo": alertas.append(("warning", f"⚠️ {label} está baixo — repor em breve."))
        corrego = str(ultima.get("Córrego/Água", "Normal") or "Normal")
        if corrego == "Seco":  alertas.append(("danger",  "🚨 Córrego/bebedouro SECO na última visita!"))
        elif corrego == "Baixo": alertas.append(("warning", "💧 Água no córrego estava baixa — verificar."))
    rows = []
    for real_idx, row in (df.iterrows() if not df.empty else []):
        d = row.to_dict()
        d["Data"] = fmt_data(d.get("Data"))
        d["_idx"] = int(real_idx)
        try:    d["Gado Faltando"] = int(d.get("Gado Faltando") or 0)
        except: d["Gado Faltando"] = 0
        rows.append(d)
    return render_template("lista_visitas.html", rows=rows, ordem=ordem, alertas=alertas)


@app.route("/visitas/nova", methods=["GET", "POST"])
@login_required
def nova_visita():
    dados = _get_dados_cache()
    estoque = calcular_estoque(dados["Compras"], dados["Vendas"], dados["Manejo"])
    if request.method == "POST":
        _validar_csrf()
        f = request.form
        data        = f.get("data", _agora().strftime("%d/%m/%Y"))
        responsavel = f.get("responsavel", "")
        gado_cnt    = int(f.get("gado_contado") or 0)
        gado_esp    = estoque
        gado_falt   = max(0, gado_esp - gado_cnt) if gado_cnt > 0 else 0
        sal      = f.get("sal_racao", "OK")
        prot     = f.get("proteinado", "OK")
        mato     = f.get("mato", "Limpo")
        grama    = f.get("grama", "Boa")
        corrego  = f.get("corrego", "Normal")
        quintal  = f.get("quintal", "OK")
        cisterna = f.get("cisterna", "OK")
        choveu = "Sim" if f.get("choveu") == "sim" else "Não"
        try:
            chuva_mm = float(str(f.get("chuva_mm", "0") or "0").replace(",", "."))
        except Exception:
            chuva_mm = 0.0
        obs = f.get("observacoes", "").strip()
        sugestoes = _gerar_sugestoes_visita(f, estoque)
        salvar_linha("Visitas", [
            data, responsavel,
            gado_cnt, gado_esp, gado_falt,
            sal, prot, mato, grama, corrego,
            quintal, cisterna,
            choveu, chuva_mm if chuva_mm > 0 else None,
            obs, sugestoes,
        ])
        if gado_falt > 0:
            flash(f"⚠️ Visita salva — mas {gado_falt} cabeça(s) estão faltando!", "warning")
        else:
            flash("✅ Visita registrada com sucesso!", "success")
        return redirect(url_for("visitas"))
    return render_template("form_visita.html", estoque=estoque,
                           MEMBROS=MEMBROS, NOMES=NOMES_MEMBROS,
                           hoje=_agora().strftime("%Y-%m-%d"))


@app.route("/visitas/excluir/<int:idx>", methods=["POST"])
@login_required
def excluir_visita(idx):
    _validar_csrf()
    fazer_backup()
    _limpar_backups_antigos()
    df = carregar_aba("Visitas")
    if df.empty or idx not in df.index:
        flash("Registro não encontrado.", "error")
        return redirect(url_for("visitas"))
    df = df.drop(index=idx).reset_index(drop=True)
    reescrever_aba("Visitas", df)
    flash("Visita excluída.", "success")
    return redirect(url_for("visitas"))


# ══════════════════════════════════════════════════════════════════════════════
#  RELATÓRIO PDF
# ══════════════════════════════════════════════════════════════════════════════

def _gerar_pdf_relatorio():
    from io import BytesIO
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                    Table, TableStyle, HRFlowable, PageBreak)
    dados  = _get_dados_cache()
    r      = _get_resumo_cache()
    mbr    = calcular_todos_membros(dados["Vendas"], dados["Compras"], dados["Gastos"], dados["Manejo"])
    extras = calcular_indicadores_extras(
        dados["Compras"], dados["Gastos"], dados["Vendas"], dados["Manejo"], r["ctcab"])
    gastos_tipo = calcular_gasto_por_tipo(dados["Gastos"])
    estoque_m   = calcular_estoque_por_membro(dados["Compras"], dados["Vendas"], dados["Manejo"])
    buf    = BytesIO()
    doc    = SimpleDocTemplate(buf, pagesize=A4,
                               leftMargin=2*cm, rightMargin=2*cm,
                               topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    VERDE   = colors.HexColor("#2e7d32")
    VERDE_L = colors.HexColor("#e8f5e9")
    CINZA   = colors.HexColor("#616161")
    BRANCO  = colors.white
    titulo_style = ParagraphStyle("titulo", parent=styles["Title"],
                                  textColor=VERDE, fontSize=20, spaceAfter=4)
    sub_style    = ParagraphStyle("sub", parent=styles["Normal"],
                                  textColor=CINZA, fontSize=10, spaceAfter=16)
    h2_style     = ParagraphStyle("h2", parent=styles["Heading2"],
                                  textColor=VERDE, fontSize=13, spaceBefore=14, spaceAfter=6)
    body_style   = styles["Normal"]

    def _brl(v):
        try: return f"R$ {float(v):,.2f}".replace(",","X").replace(".","¸").replace("X",".")
        except: return "—"
    def _pct(v):
        try:
            f = float(v)
            return f"{'+'if f>0 else ''}{f:.1f}%"
        except: return "—"
    def _tabela(dados_tab, col_widths=None):
        t = Table(dados_tab, colWidths=col_widths)
        t.setStyle(TableStyle([
            ("FONTNAME",  (0,0), (-1,-1), "Helvetica"),
            ("FONTSIZE",  (0,0), (-1,-1), 9),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [BRANCO, VERDE_L]),
            ("GRID",      (0,0), (-1,-1), 0.4, colors.HexColor("#c8e6c9")),
            ("LEFTPADDING", (0,0), (-1,-1), 6),
            ("RIGHTPADDING",(0,0), (-1,-1), 6),
            ("TOPPADDING",  (0,0), (-1,-1), 4),
            ("BOTTOMPADDING",(0,0),(-1,-1), 4),
            ("BACKGROUND",  (0,0), (-1,0), VERDE),
            ("TEXTCOLOR",   (0,0), (-1,0), BRANCO),
            ("FONTNAME",    (0,0), (-1,0), "Helvetica-Bold"),
        ]))
        return t

    story = []
    gerado_em = _agora().strftime("%d/%m/%Y %H:%M")
    story.append(Paragraph("🐄 Sítio Santo Antonio", titulo_style))
    story.append(Paragraph(f"Relatório Financeiro — {gerado_em}", sub_style))
    story.append(HRFlowable(width="100%", thickness=2, color=VERDE, spaceAfter=12))

    story.append(Paragraph("Resumo do Estoque e Custos", h2_style))
    story.append(_tabela([
        ["Indicador", "Valor"],
        ["Cabeças compradas",           str(int(r["cab_comp"]))],
        ["Cabeças vendidas",            str(int(r["cab_vend"]))],
        ["Estoque atual",               f"{int(r['estoque'])} cabeças"],
        ["CMP",                         _brl(r["cmp"]) + "/cab."],
        ["GPCab",                       _brl(r["gpcab"]) + "/cab."],
        ["CTCab",                       _brl(r["ctcab"]) + "/cab."],
        ["Break-even",                  _brl(r["break_even"]) + "/cab."],
        ["Capital imobilizado",         _brl(r["capital_imobilizado"])],
    ], col_widths=[10*cm, 7*cm]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Resultado Financeiro", h2_style))
    story.append(_tabela([
        ["Indicador", "Valor"],
        ["Total compras",               _brl(r["total_comp"])],
        ["Total gastos",                _brl(r["total_gast"])],
        ["Custo total",                 _brl(r["total_custo"])],
        ["Receita (vendas)",            _brl(r["total_vend"])],
        ["Resultado realizado",         _brl(r["resultado_realizado"])],
        ["ROI realizado",               _pct(r["roi_realizado"])],
        ["Resultado total (+ estoque)", _brl(r["resultado_total"])],
        ["ROI total",                   _pct(r["roi_total"])],
        ["Margem bruta",                _pct(r["margem_bruta"])],
    ], col_widths=[10*cm, 7*cm]))
    story.append(Spacer(1, 12))

    story.append(PageBreak())
    story.append(Paragraph("Resultado por Membro", h2_style))
    tab_mbr = [["Membro","Cabeças","Receita","Custo Total","Resultado","Margem"]]
    for m in MEMBROS:
        mr = mbr[m]
        tab_mbr.append([NOMES_MEMBROS[m], str(mr["cabecas"]), _brl(mr["receita"]),
                        _brl(mr["custo_total"]), _brl(mr["resultado"]), _pct(mr["margem_pct"])])
    story.append(_tabela(tab_mbr, col_widths=[3.5*cm,2.5*cm,3.5*cm,3.5*cm,3*cm,2*cm]))
    story.append(Spacer(1,16))

    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=1, color=CINZA))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        f"<font size='8' color='grey'>Gerado pelo Sistema de Gado — Sítio Santo Antonio | {gerado_em}</font>",
        body_style))
    doc.build(story)
    return buf.getvalue()


@app.route("/relatorio-pdf")
@login_required
def relatorio_pdf():
    from flask import Response
    try:
        pdf_bytes = _gerar_pdf_relatorio()
        nome_arquivo = f"relatorio_gado_{_agora().strftime('%Y%m%d_%H%M')}.pdf"
        return Response(pdf_bytes, mimetype="application/pdf",
                        headers={"Content-Disposition": f"attachment; filename={nome_arquivo}"})
    except Exception as e:
        flash(f"Erro ao gerar PDF: {e}", "error")
        return redirect(url_for("relatorios"))


# ══════════════════════════════════════════════════════════════════════════════
#  ENTRYPOINT
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    inicializar()
    import webbrowser, threading

    PORTA = 5000
    NGROK_TOKEN = os.environ.get("NGROK_TOKEN", "")
    url_publica = None
    if NGROK_TOKEN:
        try:
            import ngrok
            ngrok.set_auth_token(NGROK_TOKEN)
            listener    = ngrok.forward(PORTA, authtoken=NGROK_TOKEN,
                                        domain="sitiosantoantonio.ngrok-free.dev")
            url_publica = listener.url()
        except ImportError:
            print("⚠️  ngrok não instalado. Rode: pip install ngrok")
        except Exception as e:
            print(f"⚠️  ngrok não iniciou: {e}")

    def abrir_browser():
        webbrowser.open(f"http://localhost:{PORTA}")

    threading.Timer(1.2, abrir_browser).start()

    print("\n🐄 Sítio Santo Antonio — Sistema de Gado v3.3")
    print(f"   Local:  http://localhost:{PORTA}")
    if url_publica:
        print(f"   🌐 Ngrok: {url_publica}")
    print("   SECRET_KEY:", "via variável GADO_SECRET_KEY" if os.environ.get("GADO_SECRET_KEY") else "PADRÃO (defina GADO_SECRET_KEY em produção)")
    print("   Para encerrar: Ctrl+C\n")

    app.run(debug=False, port=PORTA)
