#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extensions.py — Sítio Santo Antonio
=====================================
Objeto Flask, cache, CSRF, filtros de template e helpers compartilhados.
Importado por todos os blueprints — evita importações circulares.
"""

import os, sys, hashlib, time, threading
import secrets as _secrets
from functools import wraps
from datetime import datetime, timedelta

import pandas as pd
from flask import (Flask, session, request, redirect, url_for,
                   abort, jsonify)

try:
    from zoneinfo import ZoneInfo
    _TZ_BR = ZoneInfo("America/Sao_Paulo")
except ImportError:
    _TZ_BR = None

# ── Paths ──────────────────────────────────────────────────────────────────────
if getattr(sys, "frozen", False):
    BASE_DIR   = os.path.dirname(sys.executable)
    BUNDLE_DIR = sys._MEIPASS
else:
    BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    BUNDLE_DIR = BASE_DIR

# ── App Flask ──────────────────────────────────────────────────────────────────
app = Flask(
    __name__,
    template_folder=os.path.join(BUNDLE_DIR, "templates"),
    static_folder=os.path.join(BUNDLE_DIR, "static"),
)

from config import SECRET_KEY, SESSAO_MINUTOS, CACHE_RESUMO_TTL
app.secret_key = SECRET_KEY
app.jinja_env.globals["enumerate"] = enumerate

@app.before_request
def _renovar_sessao():
    session.permanent = True
    app.permanent_session_lifetime = timedelta(minutes=SESSAO_MINUTOS)


# ── Timezone ───────────────────────────────────────────────────────────────────
def _agora() -> datetime:
    """Retorna datetime atual no fuso de Brasília (ou local como fallback)."""
    if _TZ_BR:
        return datetime.now(_TZ_BR).replace(tzinfo=None)
    return datetime.now()


# ── Cache ──────────────────────────────────────────────────────────────────────
_cache_lock = threading.Lock()
_cache: dict = {}

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
    from db import carregar_todas
    dados = _cache_get("dados")
    if dados is None:
        dados = carregar_todas()
        _cache_set("dados", dados)
    return dados

def _get_resumo_cache():
    from calculos import calcular_resumo_financeiro
    r = _cache_get("resumo")
    if r is None:
        dados = _get_dados_cache()
        r = calcular_resumo_financeiro(
            dados["Compras"], dados["Gastos"], dados["Vendas"], dados["Manejo"]
        )
        _cache_set("resumo", r)
    return r

# Monkey-patch db para invalidar cache em toda escrita
def _setup_cache_patch():
    import db as _db_mod
    from db import salvar_linha as _sl, reescrever_aba as _ra

    def _salvar_e_invalidar(aba, linha):
        _sl(aba, linha)
        _cache_invalidar()

    def _reescrever_e_invalidar(aba, df):
        _ra(aba, df)
        _cache_invalidar()

    _db_mod.salvar_linha   = _salvar_e_invalidar
    _db_mod.reescrever_aba = _reescrever_e_invalidar
    return _salvar_e_invalidar, _reescrever_e_invalidar

salvar_linha, reescrever_aba = _setup_cache_patch()


# ── CSRF ───────────────────────────────────────────────────────────────────────
def _gerar_csrf():
    if "csrf_token" not in session:
        session["csrf_token"] = _secrets.token_hex(32)
    return session["csrf_token"]

def _validar_csrf():
    token_form = request.form.get("csrf_token", "")
    token_sess = session.get("csrf_token", "")
    if not token_form or not token_sess or token_form != token_sess:
        abort(403)

@app.context_processor
def _inject_csrf():
    return {"csrf_token": _gerar_csrf()}


# ── Auth helpers ───────────────────────────────────────────────────────────────
def _sha256(senha: str) -> str:
    return hashlib.sha256(senha.strip().encode()).hexdigest()

def _bcrypt_disponivel() -> bool:
    try:
        import bcrypt; return True  # noqa
    except ImportError:
        return False

def _hash_bcrypt(senha: str) -> str:
    import bcrypt
    return bcrypt.hashpw(senha.strip().encode(), bcrypt.gensalt(rounds=12)).decode()

def _verificar_hash(senha: str, stored: str) -> bool:
    if stored.startswith("$2b$") or stored.startswith("$2a$"):
        if _bcrypt_disponivel():
            import bcrypt
            return bcrypt.checkpw(senha.strip().encode(), stored.encode())
        return False
    return _sha256(senha) == stored

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logado"):
            return redirect(url_for("auth.login", next=request.path))
        return f(*args, **kwargs)
    return decorated


# ── Filtros de template ────────────────────────────────────────────────────────
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


# ── Helpers gerais ─────────────────────────────────────────────────────────────
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
                s = "".join(partes[:-1]) + "." + partes[-1] if len(partes[-1]) <= 2 else s.replace(".", "")
        return float(s)
    except Exception:
        return 0.0

def _limpar_backups_antigos(max_backups: int = 30):
    backup_dir = os.path.join(BASE_DIR, "backups")
    if not os.path.exists(backup_dir):
        return
    arquivos = sorted(
        [os.path.join(backup_dir, f) for f in os.listdir(backup_dir)
         if f.endswith(".xlsx") and f.startswith("backup_")],
        key=os.path.getmtime,
    )
    while len(arquivos) > max_backups:
        try:
            os.remove(arquivos.pop(0))
        except OSError:
            break

# Throttle de backup (1/hora)
_ultimo_backup: float = 0.0
_BACKUP_INTERVALO = 3600

def _fazer_backup_inteligente(forcar: bool = False):
    global _ultimo_backup
    from db import fazer_backup
    agora_ts = time.time()
    if not forcar and (agora_ts - _ultimo_backup) < _BACKUP_INTERVALO:
        return None
    nome = fazer_backup()
    if nome:
        _ultimo_backup = agora_ts
        _limpar_backups_antigos()
    return nome

# Throttle de alertas WhatsApp (20h)
_ultimo_alerta_wpp: float = 0.0
_ALERTA_INTERVALO = 20 * 3600

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
    from calculos import calcular_resumo_financeiro
    r_fin = _get_resumo_cache()
    if r_fin["resultado_realizado"] < 0:
        alertas.append({"nivel": "danger",
                        "msg": f"Resultado negativo: {fmt_brl(r_fin['resultado_realizado'])}"})
    if r_fin["estoque"] > 0:
        alertas.append({"nivel": "info",
                        "msg": f"Break-even do estoque: {fmt_brl(r_fin['break_even'])}/cabeça"})
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
        tc = soma(dados["Compras"]); tg = soma(dados["Gastos"]); tv = soma(dados["Vendas"])
        custo = tc + tg; lucro = tv - custo
        result.append({
            "ano": int(ano), "compras": tc, "gastos": tg, "custo": custo,
            "vendas": tv, "lucro": lucro,
            "roi": round(lucro / custo * 100, 1) if custo > 0 else 0,
            "positivo": lucro >= 0,
        })
    return result

def _carregar_usuarios():
    import json
    caminho = os.path.join(BASE_DIR, "usuarios.json")
    from config import USUARIOS
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
    caminho = os.path.join(BASE_DIR, "usuarios.json")
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)
