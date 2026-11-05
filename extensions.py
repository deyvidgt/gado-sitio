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
from datetime import date, datetime, timedelta

import pandas as pd
from flask import (Flask, session, request, redirect, url_for,
                   abort, jsonify, g)

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
    BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
    BUNDLE_DIR = BASE_DIR

# ── App Flask ──────────────────────────────────────────────────────────────────
app = Flask(
    __name__,
    template_folder=os.path.join(BUNDLE_DIR, "templates"),
    static_folder=os.path.join(BUNDLE_DIR, "static"),
)

from config import SECRET_KEY, SESSAO_MINUTOS, CACHE_RESUMO_TTL, VERSAO, MEMBROS, NOMES_MEMBROS


def _chave_secreta() -> str:
    """
    Sem GADO_SECRET_KEY, o padrão de config.py está publicado no Git: quem o lesse
    podia forjar o cookie de sessão ("logado") e entrar sem senha. Agora, sem a
    variável, gera uma chave aleatória UMA vez e a guarda na pasta de dados.
    """
    if os.environ.get("GADO_SECRET_KEY"):
        return SECRET_KEY
    try:
        from db import RAIZ
        caminho = os.path.join(RAIZ, "secret_key.txt")
        if os.path.exists(caminho):
            with open(caminho, encoding="utf-8") as fh:
                chave = fh.read().strip()
            if len(chave) >= 32:
                return chave
        chave = _secrets.token_hex(32)
        with open(caminho, "w", encoding="utf-8") as fh:
            fh.write(chave)
        return chave
    except Exception:
        return SECRET_KEY


app.secret_key = _chave_secreta()

# v5.11 — Configuração de segurança de sessão
# Cookie de sessão não vai em POST vindo de outro site (proteção extra das rotas
# /api/* em JSON, que não usam o token CSRF do formulário).
session_config = {
    "SESSION_COOKIE_SAMESITE": "Lax",
    "SESSION_COOKIE_HTTPONLY": True,
    # Em produção (HTTPS), ativar SESSION_COOKIE_SECURE
    "SESSION_COOKIE_SECURE": os.environ.get("SESSION_COOKIE_SECURE", "False").lower() == "true",
}
app.config.update(session_config)
app.jinja_env.globals["enumerate"] = enumerate

@app.before_request
def _renovar_sessao():
    session.permanent = True
    app.permanent_session_lifetime = timedelta(minutes=SESSAO_MINUTOS)


# ── Sítio do pedido (v5.0 fase 2) ─────────────────────────────────────────────
# shortcut: um pedido por vez por processo — db.DATA_DIR e os donos (config) são
# globais e cada pedido aponta para o seu sítio. Para uma família é de sobra; se o
# site ficar lento com muita gente, trocar os globais por contexto do pedido.
_trava_sitio = threading.Lock()
_SEM_DADOS = {None, "static", "favicon", "service_worker", "manifest"}


@app.before_request
def _entrar_no_sitio():
    if request.endpoint in _SEM_DADOS:
        return
    import sitios
    if not _trava_sitio.acquire(timeout=60):
        abort(503)
    g._trava_sitio = True
    logado = bool(session.get("logado"))
    permitidos = sitios.sitios_do_usuario(session.get("usuario")) if logado else []
    if logado and not permitidos and request.endpoint not in ("login", "logout"):
        abort(403)
    slug = session.get("sitio")
    if slug not in permitidos:
        slug = permitidos[0] if permitidos else next(iter(sitios.carregar()["sitios"]))
    sitios.ativar(slug)
    if logado and permitidos:
        session["sitio"] = slug
    if logado:
        import modulos
        modulo = modulos.modulo_da_rota(request.path)
        if modulo and not modulos.esta_ativo(modulo, modulos.estado_sitio()):
            nome = modulos.MODULOS[modulo]["nome"]
            mensagem = f"O módulo {nome} está desativado neste sítio. Reative-o para continuar."
            if request.path.startswith("/api/"):
                return jsonify({"ok": False, "erro": "modulo_desativado",
                                "modulo": modulo, "mensagem": mensagem}), 403
            from flask import flash
            flash(mensagem, "warning")
            return redirect(url_for("configuracoes_modulos"))


@app.teardown_request
def _sair_do_sitio(_exc=None):
    if g.pop("_trava_sitio", None):
        _trava_sitio.release()


@app.context_processor
def _inject_sitios():
    """Seletor do topo: só aparece com 2+ sítios para o usuário."""
    import sitios
    if not session.get("logado"):
        return {"sitios_menu": [], "sitio_atual": sitios.atual(), "varios_sitios": False}
    return {"sitios_menu": [(s, sitios.nome(s)) for s in sitios.sitios_do_usuario(session.get("usuario"))],
            "sitio_atual": sitios.atual(),
            "varios_sitios": len(sitios.carregar()["sitios"]) > 1}   # link do painel da Família


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

def _versao_dados():
    from db import versao_arquivo
    return versao_arquivo()

def _chave_cache(chave):
    import db
    return (db.DATA_DIR, chave)   # cada sítio com o seu cache

def _cache_get(chave, versao=None):
    """Valor em cache, se não venceu o TTL e (quando `versao` é dada) se o .xlsx
    não mudou desde que foi calculado. Sem a checagem de versão, uma gravação feita
    por OUTRO processo (Task, outro worker) deixava a lista com índices velhos e
    editar/excluir podia acertar o registro errado."""
    with _cache_lock:
        entry = _cache.get(_chave_cache(chave))
        if entry and (time.time() - entry[0]) < CACHE_RESUMO_TTL \
                and (versao is None or entry[1] == versao):
            return entry[2]
    return None

def _cache_set(chave, valor, versao=None):
    with _cache_lock:
        _cache[_chave_cache(chave)] = (time.time(), versao, valor)

def _cache_dados(chave, calcular):
    """Cache de algo derivado da planilha: recalcula só quando o arquivo muda."""
    versao = _versao_dados()
    v = _cache_get(chave, versao)
    if v is None:
        v = calcular()
        _cache_set(chave, v, versao)
    return v

def _get_dados_cache():
    from db import carregar_todas
    return _cache_dados("dados", carregar_todas)


def _get_dados_busca_cache():
    from db import carregar_todas_abas
    return _cache_dados("dados_busca", carregar_todas_abas)


def _get_resumo_cache():
    from calculos import calcular_resumo_financeiro
    def _calc():
        d = _get_dados_cache()
        return calcular_resumo_financeiro(d["Compras"], d["Gastos"], d["Vendas"], d["Manejo"])
    return _cache_dados("resumo", _calc)

def _get_membros_cache():
    """Resultado por membro (painel, /api/membros, relatórios e PDF) — antes cada
    página refazia a simulação inteira."""
    from calculos import calcular_todos_membros
    def _calc():
        d = _get_dados_cache()
        return calcular_todos_membros(d["Vendas"], d["Compras"], d["Gastos"], d["Manejo"])
    return _cache_dados("membros", _calc)

def _get_evolucao_cache():
    from calculos import calcular_evolucao_rebanho
    def _calc():
        d = _get_dados_cache()
        return calcular_evolucao_rebanho(d["Compras"], d["Gastos"], d["Vendas"], d["Manejo"])
    return _cache_dados("evolucao", _calc)

# Monkey-patch db para invalidar cache em toda escrita
def _setup_cache_patch():
    import db as _db_mod
    from db import salvar_linha as _sl, reescrever_aba as _ra
    _sla = _db_mod.salvar_linhas_atomicas

    def _salvar_e_invalidar(aba, linha):
        _sl(aba, linha)
        _cache_invalidar()

    def _reescrever_e_invalidar(aba, df):
        _ra(aba, df)
        _cache_invalidar()

    def _salvar_linhas_e_invalidar(registros):
        _sla(registros)
        _cache_invalidar()

    _db_mod.salvar_linha   = _salvar_e_invalidar
    _db_mod.reescrever_aba = _reescrever_e_invalidar
    _db_mod.salvar_linhas_atomicas = _salvar_linhas_e_invalidar
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


# ── Config do sítio com cache ──────────────────────────────────────────────────
_SITIO_CFG_DEFAULT = {
    "nome": "Sítio Santo Antonio",
    "logo": "🐄",
    "logo_tipo": "emoji",
}

def _cache_invalidar_chave(chave):
    with _cache_lock:
        _cache.pop(_chave_cache(chave), None)

def invalidar_cache_sitio():
    _cache_invalidar_chave("sitio_config")

def _ler_sitio_config_disco() -> dict:
    import json
    try:
        from db import DATA_DIR as _DD
        candidatos = [os.path.join(_DD, "sitio_config.json"),
                      os.path.join(BASE_DIR, "sitio_config.json")]
    except Exception:
        candidatos = [os.path.join(BASE_DIR, "sitio_config.json")]
    for p in candidatos:
        if os.path.exists(p):
            try:
                with open(p, encoding="utf-8") as fh:
                    cfg = json.load(fh)
                    for k, v in _SITIO_CFG_DEFAULT.items():
                        cfg.setdefault(k, v)
                    cfg.setdefault("donos", _donos_txt())
                    return cfg
            except Exception:
                pass
    return {**_SITIO_CFG_DEFAULT, "donos": _donos_txt()}


def _donos_txt() -> str:
    """Donos do sítio do pedido (não os do boot: cada sítio tem os seus)."""
    return " · ".join(NOMES_MEMBROS[m] for m in MEMBROS)

@app.context_processor
def _inject_sitio_config():
    """Injeta sitio_config em todos os templates — leitura cacheada."""
    cfg = _cache_get("sitio_config")
    if cfg is None:
        cfg = _ler_sitio_config_disco()
        _cache_set("sitio_config", cfg)
    return {"sitio_config": cfg, "VERSAO": VERSAO}


@app.context_processor
def _inject_modulos():
    """Estado efetivo e preferências editáveis do sítio atual."""
    import modulos
    cfg = _cache_get("sitio_config")
    if cfg is None:
        cfg = _ler_sitio_config_disco()
        _cache_set("sitio_config", cfg)
    return {
        "modulos": modulos.estado_efetivo(cfg),
        "modulos_preferencias": modulos.preferencias(cfg),
        "catalogo_modulos": modulos.MODULOS,
    }


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
            # Usar redirect direto — url_for("login") falha se routes_auth
            # ainda não foi importado no momento em que extensions é carregado
            next_url = request.path
            return redirect(f"/login?next={next_url}")
        return f(*args, **kwargs)
    return decorated


# ── Filtros de template ────────────────────────────────────────────────────────
@app.template_filter("brl")
def fmt_brl(v):
    try:
        return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "—"

@app.template_filter("br_num")
def fmt_num(v, casas=1):
    try:
        return f"{float(v):,.{int(casas)}f}".replace(",", "X").replace(".", ",").replace("X", ".")
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
    if v is None:
        return ""
    try:
        if pd.isna(v):
            return ""
    except (TypeError, ValueError):
        pass
    if isinstance(v, pd.Timestamp) and pd.notna(v):
        return v.strftime("%d/%m/%Y")
    if isinstance(v, (date, datetime)):
        return v.strftime("%d/%m/%Y")
    if isinstance(v, str):
        try:
            return datetime.strptime(v.strip(), "%Y-%m-%d").strftime("%d/%m/%Y")
        except ValueError:
            pass
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
    # Os backups ficam na pasta de DADOS (db.fazer_backup), não na do código.
    from db import DATA_DIR
    backup_dir = os.path.join(DATA_DIR, "backups")
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
    from db import get_alertas_saude
    alertas = []
    hoje = _agora()
    df_man = dados["Manejo"]
    from saude import ultima_data, lembretes_sazonais
    for tipo, dias in get_alertas_saude().items():
        ultima = ultima_data(df_man, tipo)
        if ultima is None:
            alertas.append({"nivel": "warning", "msg": f"Nenhum registro de {tipo}.",
                           "rota": "/manejo/novo"})  # Atalho para registrar manejo
            continue
        d = (hoje - ultima.to_pydatetime()).days
        if d > dias:
            alertas.append({"nivel": "danger",
                             "msg": f"{tipo} atrasada! Última: {ultima.strftime('%d/%m/%Y')} ({d} dias)",
                             "rota": "/manejo/novo"})
    alertas.extend(lembretes_sazonais(df_man, hoje))
    # v4.3: fêmeas com brinco na janela da brucelose (3–8 meses), pelo nascimento.
    try:
        import animais as _A
        for b in _A.janela_brucelose(_A.carregar(), df_man, hoje):
            if b["situacao"] == "na janela":
                a = b["animal"]
                alertas.append({"nivel": "warning",
                                "msg": f"Brucelose: {a['Categoria'] or 'fêmea'} "
                                       f"{_A.fmt_brinco(a['Brinco Cor'], a['Brinco Nº'])} {b['msg']}",
                                "rota": f"/animais/{a.get('ID')}"})  # Atalho para ficha do animal
    except Exception:
        pass
    from calculos import calcular_resumo_financeiro
    r_fin = _get_resumo_cache()
    if r_fin["resultado_realizado"] < 0:
        alertas.append({"nivel": "danger",
                        "msg": f"Resultado negativo: {fmt_brl(r_fin['resultado_realizado'])}",
                        "rota": "/relatorios"})  # Atalho para ver detalhes financeiros
    if r_fin["estoque"] > 0:
        alertas.append({"nivel": "info",
                        "msg": f"Break-even do estoque: {fmt_brl(r_fin['break_even'])}/cabeça",
                        "rota": "/vendas"})  # Atalho para registrar venda
    return alertas

def _calc_anual(dados):
    from calculos import calcular_resultado_anual
    return calcular_resultado_anual(dados["Compras"], dados["Gastos"],
                                    dados["Vendas"], dados["Manejo"])

def _usuarios_path() -> str:
    """Retorna o caminho correto do usuarios.json, sempre na pasta da família."""
    try:
        from db import RAIZ as _DD
        return os.path.join(_DD, "usuarios.json")
    except Exception:
        return os.path.join(BASE_DIR, "usuarios.json")

def _carregar_usuarios():
    import json
    caminho = _usuarios_path()
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
    caminho = _usuarios_path()
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)
