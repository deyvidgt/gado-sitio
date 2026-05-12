#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sistema de Gestão de Gado — Sítio Santo Antonio"""

import sys, os, tempfile, hashlib
from functools import wraps
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Caminho base: pasta do .exe quando compilado, pasta do script quando em Python
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
    BUNDLE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    BUNDLE_DIR = BASE_DIR

sys.path.insert(0, BUNDLE_DIR)

from flask import (Flask, render_template, request, redirect, url_for,
                   jsonify, flash, send_file, session)
import pandas as pd
from datetime import datetime, timedelta

from db import carregar_todas, carregar_aba, salvar_linha, reescrever_aba, inicializar, fazer_backup
from calculos import (
    calcular_estoque, calcular_resumo_financeiro, calcular_todos_membros,
    calcular_fluxo_caixa, calcular_cmp_ate_data, calcular_gpcab_ate_data,
    calcular_cmp, calcular_gpcab, calcular_estoque_por_membro,
    calcular_indicadores_extras, calcular_gasto_por_tipo, calcular_evolucao_cmp,
)
from config import (TIPOS_GASTO, TIPOS_MANEJO, MEMBROS, NOMES_MEMBROS,
                    EMOJIS_MEMBROS, USUARIOS, SESSAO_MINUTOS, OPCOES_VISITA)
from exportar import exportar_relatorio_excel

app = Flask(__name__,
            template_folder=os.path.join(BUNDLE_DIR, "templates"),
            static_folder=os.path.join(BUNDLE_DIR, "static"))
app.secret_key = "gado_sitio_santo_antonio_2025_xK9mP"
app.jinja_env.globals["enumerate"] = enumerate

# Sessão expira após SESSAO_MINUTOS de inatividade
@app.before_request
def _renovar_sessao():
    session.permanent = True
    app.permanent_session_lifetime = timedelta(minutes=SESSAO_MINUTOS)

# ── Autenticação ──────────────────────────────────────────────────────────────

MAX_TENTATIVAS = 7   # bloqueio temporário após N erros seguidos

def _hash(senha: str) -> str:
    return hashlib.sha256(senha.strip().encode()).hexdigest()

def login_required(f):
    """Decorator: redireciona para login se não autenticado."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logado"):
            return redirect(url_for("login", next=request.path))
        return f(*args, **kwargs)
    return decorated

@app.route("/login", methods=["GET", "POST"])
def login():
    # Já logado → ir direto
    if session.get("logado"):
        return redirect(url_for("dashboard"))

    erro = None
    usuario_digitado = ""

    if request.method == "POST":
        usuario = request.form.get("usuario", "").strip().lower()
        senha   = request.form.get("senha",   "").strip()
        usuario_digitado = usuario

        # Controle de tentativas por sessão
        tentativas = session.get("tentativas_login", 0)
        usuarios_db = _carregar_usuarios()

        if tentativas >= MAX_TENTATIVAS:
            erro = f"Muitas tentativas. Feche e abra o programa para desbloquear."
        elif usuario in usuarios_db and _hash(senha) == usuarios_db[usuario]["hash"]:
            # ✅ Login bem-sucedido
            session.clear()
            session["logado"]  = True
            session["usuario"] = usuario
            next_url = request.args.get("next") or url_for("dashboard")
            return redirect(next_url)
        else:
            session["tentativas_login"] = tentativas + 1
            restantes = MAX_TENTATIVAS - session["tentativas_login"]
            if restantes <= 0:
                erro = "Acesso bloqueado. Feche e abra o programa para tentar novamente."
            elif usuario and usuario not in usuarios_db:
                erro = f"Usuário '{usuario}' não encontrado."
            else:
                erro = "Usuário ou senha incorretos."

    tentativas_restantes = MAX_TENTATIVAS - session.get("tentativas_login", 0)
    return render_template("login.html", erro=erro,
                           usuario_digitado=usuario_digitado,
                           tentativas_restantes=tentativas_restantes)

@app.route("/logout", methods=["POST"])
def logout():
    usuario = session.get("usuario", "")
    session.clear()
    flash(f"Até logo, {usuario.capitalize()}! 👋", "success")
    return redirect(url_for("login"))

# Rota de fallback para o favicon na raiz
@app.route("/favicon.ico")
def favicon():
    import os as _os
    from flask import send_from_directory
    static = _os.path.join(BUNDLE_DIR, "static")
    if _os.path.exists(_os.path.join(static, "favicon.ico")):
        return send_from_directory(static, "favicon.ico")
    return "", 204

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
    """Converte string de valor monetário para float.
    Aceita: 60.000,00 | 60000,00 | 60000.00 | 60.000 | 60.000.00
    """
    try:
        s = str(s).strip().replace("R$", "").replace(" ", "").replace("\xa0", "")
        if not s or s in ("0", "0.0", "0,0"):
            return 0.0
        if "," in s and "." in s:
            # BR: ponto=milhar, vírgula=decimal  →  60.000,00
            s = s.replace(".", "").replace(",", ".")
        elif "," in s:
            # Só vírgula=decimal  →  60000,00
            s = s.replace(",", ".")
        else:
            partes = s.split(".")
            if len(partes) == 1:
                pass  # só número inteiro
            elif len(partes) == 2:
                if len(partes[1]) == 3:
                    # Ponto de milhar (60.000)
                    s = s.replace(".", "")
                # else: ponto decimal normal (60000.00 ou 60.50)
            else:
                # Múltiplos pontos: 60.000.00 ou 1.000.000
                # Se última parte tem 1-2 dígitos → é decimal
                if len(partes[-1]) <= 2:
                    inteiro = "".join(partes[:-1])
                    s = inteiro + "." + partes[-1]
                else:
                    # Todos são milhares (1.000.000)
                    s = s.replace(".", "")
        return float(s)
    except Exception:
        return 0.0


def _limpar_backups_antigos(max_backups: int = 15):
    """
    Mantém apenas os N backups mais recentes na pasta backups/.
    Evita que o disco encha com backups acumulados.
    """
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
    hoje = datetime.now()
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
    r_fin = calcular_resumo_financeiro(dados["Compras"], dados["Gastos"], dados["Vendas"], dados["Manejo"])
    if r_fin["resultado_realizado"] < 0:
        alertas.append({"nivel": "danger", "msg": f"Resultado negativo: {fmt_brl(r_fin['resultado_realizado'])}"})
    if r_fin["estoque"] > 0:
        alertas.append({"nivel": "info", "msg": f"Break-even do estoque: {fmt_brl(r_fin['break_even'])}/cabeça"})
    return alertas


def _calc_anual(dados):
    """
    Resumo financeiro por ano.
    NOTA: o 'custo' aqui é a soma de compras + gastos registrados NAQUELE ano.
    Para resultado verdadeiro por ano (considerando custo histórico das vendas),
    veja o relatório completo que usa CTCab histórico.
    """
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
            "ano":      int(ano),
            "compras":  tc,
            "gastos":   tg,
            "custo":    custo,
            "vendas":   tv,
            "lucro":    lucro,
            "roi":      round(lucro / custo * 100, 1) if custo > 0 else 0,
            "positivo": lucro >= 0,
        })
    return result


def _salvar_venda(f, dados, idx=None):
    data    = f.get("data", datetime.now().strftime("%d/%m/%Y"))
    cabecas = int(f.get("cabecas", 0) or 0)
    valor   = parse_valor(f.get("valor", 0))
    arroba  = parse_valor(f.get("arroba") or "0")
    desc    = f.get("descricao", "").strip()

    # Validação básica
    if cabecas <= 0:
        cabecas = 1
    if valor < 0:
        valor = 0.0

    qtd_mae    = int(f.get("qtd_mae",    0) or 0)
    qtd_deyvid = int(f.get("qtd_deyvid", 0) or 0)
    qtd_nilson = int(f.get("qtd_nilson", 0) or 0)
    soma = qtd_mae + qtd_deyvid + qtd_nilson
    if soma == 0:
        # Nenhum membro informado: dividir igualmente
        base = cabecas // 3
        qtd_mae    = base
        qtd_deyvid = base
        qtd_nilson = cabecas - base * 2
    elif soma != cabecas:
        # Ajustar proporcionalmente para fechar em cabecas
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

    # CTCab histórico na data da venda (contexto completo passado corretamente)
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


# ── DASHBOARD ──

@app.route("/")
@login_required
def dashboard():
    dados = carregar_todas()
    r = calcular_resumo_financeiro(dados["Compras"], dados["Gastos"], dados["Vendas"], dados["Manejo"])
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
    # Ordenar por data real (Timestamp)
    recentes.sort(key=lambda x: x["_ts"], reverse=True)
    for rec in recentes:
        rec.pop("_ts", None)
    return render_template("dashboard.html", r=r, membros=membros_r,
                           estoque_membro=estoque_membro, recentes=recentes[:6],
                           alertas=_gerar_alertas(dados),
                           NOMES=NOMES_MEMBROS, EMOJIS=EMOJIS_MEMBROS, MEMBROS=MEMBROS)


# ── API ──

@app.route("/api/fluxo")
@login_required
def api_fluxo():
    dados = carregar_todas()
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
    dados = carregar_todas()
    mbr = calcular_todos_membros(dados["Vendas"], dados["Compras"], dados["Gastos"], dados["Manejo"])
    return jsonify({"nomes":      [NOMES_MEMBROS[m] for m in MEMBROS],
                    "receitas":   [round(mbr[m]["receita"],    2) for m in MEMBROS],
                    "custos":     [round(mbr[m]["custo_total"], 2) for m in MEMBROS],
                    "resultados": [round(mbr[m]["resultado"],  2) for m in MEMBROS]})

@app.route("/api/cotacao-scot")
def api_cotacao_scot():
    try:
        import requests, re
        from bs4 import BeautifulSoup
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9",
            "Referer": "https://www.google.com/",
        }
        r = requests.get("https://www.scotconsultoria.com.br/cotacoes/novilha/",
                         headers=headers, timeout=12)
        soup = BeautifulSoup(r.text, "html.parser")
        cotacoes = []
        regioes_alvo = ["triângulo", "triangulo", "uberlândia", "uberaba", "patos de minas"]
        for table in soup.find_all("table"):
            rows_t = table.find_all("tr")
            for row_t in rows_t[1:]:
                cols = row_t.find_all(["td", "th"])
                if not cols:
                    continue
                regiao = cols[0].get_text(strip=True)
                if any(k in regiao.lower() for k in regioes_alvo):
                    preco_str = " ".join(c.get_text(strip=True) for c in cols[1:3])
                    nums = re.findall(r"\d{2,3}[.,]\d{2}", preco_str)
                    preco = float(nums[0].replace(",", ".")) if nums else None
                    cotacoes.append({"regiao": regiao, "preco": preco, "raw": preco_str})
        # Fallback: buscar no texto
        if not cotacoes:
            text = soup.get_text()
            lines = text.split("\n")
            for i, line in enumerate(lines):
                if any(k in line.lower() for k in regioes_alvo):
                    context = " ".join(lines[i:i + 4])
                    nums = re.findall(r"\d{2,3}[.,]\d{2}", context)
                    if nums:
                        cotacoes.append({"regiao": "Triângulo Mineiro",
                                         "preco": float(nums[0].replace(",", ".")),
                                         "raw": nums[0]})
                        break
        return jsonify({"ok": True, "cotacoes": cotacoes,
                        "atualizado": datetime.now().strftime("%d/%m/%Y %H:%M"),
                        "fonte": "Scot Consultoria"})
    except Exception as e:
        return jsonify({"ok": False, "erro": str(e)})


# ── Cotação IMEA (Playwright) ─────────────────────────────────────────────────
# O IMEA usa Angular — a página só tem dados após o JS renderizar.
# Playwright abre um Chromium headless real, executa o Angular e retorna
# o HTML completo com os dados.
#
# Instalar UMA VEZ no terminal:
#   pip install playwright
#   python -m playwright install chromium

def _parse_preco_imea(texto: str) -> float | None:
    """Extrai preço monetário BR: 2.940,17 | 2940,17 | 2940.17"""
    import re
    m = re.search(r"\d{1,3}(?:\.\d{3})*,\d{2}", texto)
    if m:
        return float(m.group().replace(".", "").replace(",", "."))
    m = re.search(r"\d{3,6}\.\d{2}", texto)
    if m:
        return float(m.group())
    return None


def _parse_variacao_imea(texto: str) -> float | None:
    """Extrai variação percentual (positiva ou negativa)."""
    import re
    m = re.search(r"([+-]?\d{1,3}[.,]\d{1,2})%?", texto)
    if m:
        return float(m.group(1).replace(",", "."))
    return None


def _garantir_chromium():
    """
    Verifica se o Chromium do Playwright está instalado.
    Se não estiver, instala automaticamente (pode demorar ~1 min na 1ª vez).
    Retorna (ok: bool, mensagem: str).
    """
    import subprocess, sys
    from playwright.sync_api import sync_playwright

    try:
        # Testa se consegue criar o browser sem lançar
        with sync_playwright() as p:
            info = p.chromium.executable_path
            if not os.path.exists(info):
                raise FileNotFoundError(info)
        return True, "Chromium OK"
    except Exception:
        pass

    # Chromium não existe — instalar agora
    try:
        resultado = subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            capture_output=True, text=True, timeout=180,
        )
        if resultado.returncode == 0:
            return True, "Chromium instalado com sucesso"
        return False, f"Falha ao instalar: {resultado.stderr[:300]}"
    except subprocess.TimeoutExpired:
        return False, "Timeout ao instalar Chromium (>3 min). Rode manualmente: python -m playwright install chromium"
    except Exception as e:
        return False, str(e)


def _fetch_imea_playwright() -> tuple[str, str]:
    """
    Abre o IMEA com Chromium headless, aguarda o Angular renderizar
    e retorna (html_completo, log_debug).

    Instala o Chromium automaticamente se ainda não estiver baixado.
    """
    import subprocess, sys
    from playwright.sync_api import sync_playwright, TimeoutError as PwTimeout

    log = []
    URL = "https://www.imea.com.br/imea-site/indicador-boi"

    SELETORES = [
        "table", "mat-table", "tbody tr",
        "[class*='table']", "[class*='indicador']",
        "[class*='cotacao']", "[class*='card']",
    ]

    def _launch_browser(p):
        """Tenta lançar o Chromium; se executável não existir, instala e tenta de novo."""
        try:
            return p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox",
                      "--disable-blink-features=AutomationControlled"],
            )
        except Exception as e:
            msg = str(e)
            if "Executable doesn't exist" in msg or "executable" in msg.lower():
                log.append("Chromium não encontrado — instalando automaticamente...")
                result = subprocess.run(
                    [sys.executable, "-m", "playwright", "install", "chromium"],
                    capture_output=True, text=True, timeout=180,
                )
                if result.returncode != 0:
                    raise RuntimeError(
                        f"Falha ao instalar Chromium: {result.stderr[:300]}\n"
                        "Execute manualmente: python -m playwright install chromium"
                    )
                log.append("Chromium instalado! Iniciando navegador...")
                return p.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-setuid-sandbox",
                          "--disable-blink-features=AutomationControlled"],
                )
            raise

    with sync_playwright() as p:
        browser = _launch_browser(p)
        ctx = browser.new_context(
            locale="pt-BR",
            timezone_id="America/Sao_Paulo",
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        )
        page = ctx.new_page()
        try:
            log.append("Navegando...")
            page.goto(URL, wait_until="networkidle", timeout=40000)
            log.append("networkidle OK")

            # Esperar seletor de conteúdo
            achou_sel = False
            for sel in SELETORES:
                try:
                    page.wait_for_selector(sel, timeout=8000)
                    log.append(f"Seletor: {sel}")
                    achou_sel = True
                    break
                except PwTimeout:
                    continue
            if not achou_sel:
                log.append("Nenhum seletor — aguardando 6s...")
                page.wait_for_timeout(6000)

            # Scroll completo para forçar lazy-load
            page.evaluate("""() => new Promise(resolve => {
                let d = 0;
                const t = setInterval(() => {
                    window.scrollBy(0, 250);
                    d += 250;
                    if (d >= document.body.scrollHeight) {
                        clearInterval(t);
                        window.scrollTo(0, 0);
                        resolve();
                    }
                }, 60);
            })""")
            page.wait_for_timeout(2500)

            # Se conteúdo ainda não apareceu, tentar clicar em abas/botões
            chk = page.content().upper()
            if not any(k in chk for k in ["NOVILHA", "BEZERRA", "NELORE", "BOI GORDO"]):
                log.append("Conteúdo ausente — tentando interagir...")
                for txt in ["BOI", "INDICADOR", "COTAÇÃO", "PREÇO"]:
                    try:
                        page.locator(
                            f"button:has-text('{txt}'), a:has-text('{txt}')"
                        ).first.click(timeout=3000)
                        page.wait_for_timeout(3500)
                        break
                    except Exception:
                        pass

            html = page.content()
            log.append(f"HTML: {len(html)} chars")

        except PwTimeout as e:
            html = page.content()
            log.append(f"Timeout parcial: {e}")
        except Exception as e:
            html = ""
            log.append(f"Erro: {e}")
        finally:
            browser.close()

    return html, " | ".join(log)


def _buscar_indicador_imea(soup, palavras_chave: list[str]) -> dict | None:
    """
    Localiza bloco de indicador pelo título e extrai linha da região Sudeste.

    Suporta <table> normal e Angular Material (<mat-table>, <mat-row>).
    Score: Sudeste=10, sinônimos=5, qualquer linha=0 (fallback).
    """
    REGIOES_SUDESTE = [
        "sudeste", "são paulo", "sao paulo", "sp",
        "minas gerais", "minas", "mg",
        "goiás", "goias", "go",
        "espírito santo", "espirito santo", "es",
        "rio de janeiro", "rj",
        "centro-sul",
    ]

    candidatos = [
        el for el in soup.find_all(string=True)
        if all(p.upper() in str(el).upper().strip() for p in palavras_chave)
    ]

    for cand in candidatos:
        container = cand.parent
        tabela = None
        for _ in range(14):
            if container is None:
                break
            tabela = (
                container.find(["table", "mat-table"])
                or container.find(attrs={"class": lambda c: c and "table" in " ".join(c).lower()})
            )
            if tabela:
                break
            container = container.parent
        if tabela is None:
            continue

        titulo_bloco = cand.strip()

        # Linhas — suporta tr, mat-row e role=row
        linhas = (tabela.find_all(["tr", "mat-row"])
                  or tabela.find_all(attrs={"role": "row"}))
        if not linhas:
            continue

        # Detectar colunas pelo cabeçalho
        preco_col = 1
        var_col   = 2
        hdr = linhas[0].find_all(["th", "td", "mat-header-cell"])
        for i, c in enumerate(hdr):
            t = c.get_text(strip=True).lower()
            if any(k in t for k in ["r$", "preço", "preco", "cab", "@", "arroba"]):
                preco_col = i
            elif any(k in t for k in ["varia", "%", "var."]):
                var_col = i

        # Encontrar melhor linha (Sudeste em primeiro lugar)
        melhor = None
        score_max = -1
        for tr in linhas[1:]:
            cells = (tr.find_all(["td", "th", "mat-cell"])
                     or tr.find_all(attrs={"role": lambda r: r in ("cell", "gridcell")}))
            if not cells:
                continue
            reg = cells[0].get_text(strip=True).lower()
            score = 10 if "sudeste" in reg else (5 if any(s in reg for s in REGIOES_SUDESTE) else 0)
            if score > score_max:
                score_max = score
                melhor = cells

        # Fallback absoluto: primeira linha de dados
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
        if preco is not None:
            return {
                "titulo":   titulo_bloco,
                "regiao":   melhor[0].get_text(strip=True),
                "preco":    preco,
                "variacao": _parse_variacao_imea(var_txt),
            }

    return None


@app.route("/api/cotacao-imea")
@login_required
def api_cotacao_imea():
    """
    Busca os 3 indicadores IMEA (Sudeste) via Playwright (Chromium headless).
    Retorna cotacoes[] no formato que o dashboard.html espera.

    Indicadores:
        • NOVILHA NELORE 18M 255KG 8,5@
        • BEZERRA NELORE 12M 180KG 6@
        • BEZERRA NELORE 8M 150KG 5@  (variante 165KG/5,5@ incluída)
    """
    # ── Dados financeiros do rebanho ──────────────────────────────────────────
    dados      = carregar_todas()
    r_fin      = calcular_resumo_financeiro(
        dados["Compras"], dados["Gastos"], dados["Vendas"], dados["Manejo"]
    )
    break_even = round(r_fin["break_even"], 2)
    ctcab      = round(r_fin["ctcab"],      2)

    def _erro(msg, debug=""):
        return jsonify({
            "ok": False, "cotacoes": [],
            "break_even": break_even, "ctcab": ctcab,
            "erro": msg, "debug": debug,
        })

    # ── Verificar / instalar Playwright + Chromium ───────────────────────────
    try:
        import playwright  # noqa: F401
    except ImportError:
        return _erro(
            "Playwright não instalado. Abra o terminal e execute:\n"
            "  pip install playwright\n"
            "  python -m playwright install chromium\n"
            "Depois clique em Buscar novamente."
        )

    # ── Definição dos 3 indicadores ──────────────────────────────────────────
    INDICADORES = [
        {
            "emoji": "🐮", "nome": "Novilha 18M 255kg 8,5@",
            "kg": 255, "arrobas": 8.5,
            "chaves": [
                ["NOVILHA", "255"],
                ["NOVILHA", "18M", "8,5"],
                ["NOVILHA", "18M", "8.5"],
                ["NOVILHA", "NELORE", "18"],
                ["NOVILHA", "NELORE"],
            ],
        },
        {
            "emoji": "🐄", "nome": "Bezerra 12M 180kg 6@",
            "kg": 180, "arrobas": 6.0,
            "chaves": [
                ["BEZERRA", "180", "6"],
                ["BEZERRA", "12M", "180"],
                ["BEZERRA", "12M", "6"],
                ["BEZERRA", "180"],
                ["BEZERRA", "NELORE", "12"],
            ],
        },
        {
            "emoji": "🐄", "nome": "Bezerra 8M 150kg 5@",
            "kg": 150, "arrobas": 5.0,
            "chaves": [
                ["BEZERRA", "150", "5"],
                ["BEZERRA", "8M", "150"],
                ["BEZERRA", "8M", "5"],
                ["BEZERRA", "150"],
                ["BEZERRA", "165"],       # variante visível no screenshot
                ["BEZERRA", "8M", "5,5"],
                ["BEZERRA", "NELORE", "8"],
            ],
        },
    ]

    # ── Buscar HTML via Playwright ────────────────────────────────────────────
    try:
        html, debug_log = _fetch_imea_playwright()
    except RuntimeError as e:
        # RuntimeError com mensagem clara (ex: falha ao instalar Chromium)
        return _erro(str(e))
    except Exception as e:
        import traceback
        msg = str(e)
        if "Executable doesn't exist" in msg or "executable" in msg.lower():
            return _erro(
                "Chromium não encontrado. Abra o terminal (cmd) e execute:\n"
                "  python -m playwright install chromium\n"
                "Depois clique em Buscar novamente.",
                msg,
            )
        return _erro(f"Erro ao iniciar Playwright: {e}", traceback.format_exc())

    if not html:
        return _erro("Playwright não retornou HTML.", debug_log)

    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    texto = soup.get_text(" ", strip=True).upper()

    if not any(k in texto for k in ["NOVILHA", "BEZERRA", "BEZERRO", "BOI GORDO", "NELORE"]):
        return _erro(
            "Angular renderizou mas sem dados de cotação. "
            "Verifique: imea.com.br/imea-site/indicador-boi",
            debug_log,
        )

    # ── Montar cotacoes[] ────────────────────────────────────────────────────
    cotacoes = []
    for ind in INDICADORES:
        achado = None
        for chave in ind["chaves"]:
            achado = _buscar_indicador_imea(soup, chave)
            if achado:
                break

        if achado and achado.get("preco"):
            pc   = achado["preco"]
            arrs = ind["arrobas"]
            vs   = round(pc - break_even, 2)
            cotacoes.append({
                "emoji":            ind["emoji"],
                "nome":             ind["nome"],
                "kg":               ind["kg"],
                "arrobas":          arrs,
                "regiao":           achado.get("regiao", "Sudeste"),
                "preco_cab":        round(pc, 2),
                "preco_arroba":     round(pc / arrs, 2) if arrs else 0.0,
                "variacao":         achado.get("variacao"),
                "lucra":            pc >= break_even,
                "vs_breakeven":     vs,
                "vs_breakeven_pct": round(vs / break_even * 100, 1) if break_even else 0.0,
            })
        else:
            cotacoes.append({
                "emoji": ind["emoji"], "nome": ind["nome"],
                "kg": ind["kg"], "arrobas": ind["arrobas"],
                "regiao": "Sudeste",
                "preco_cab": None, "preco_arroba": None,
                "variacao": None, "lucra": None,
                "vs_breakeven": None, "vs_breakeven_pct": None,
            })

    algum_ok = any(c["preco_cab"] is not None for c in cotacoes)

    return jsonify({
        "ok":         algum_ok,
        "cotacoes":   cotacoes,
        "break_even": break_even,
        "ctcab":      ctcab,
        "fonte":      "IMEA — imea.com.br",
        "url":        "https://www.imea.com.br/imea-site/indicador-boi",
        "atualizado": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "referencia": "Região: Sudeste | Fonte: IMEA",
        "debug":      debug_log,
        "erro":       None if algum_ok else (
            "Nenhum indicador encontrado na página renderizada. "
            f"Debug: {debug_log}"
        ),
    })


# ── COMPRAS ──

@app.route("/compras")
@login_required
def compras():
    dados = carregar_todas()
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
                           colunas=["Data", "Qtd Cabeças", "Valor Total (R$)", "Valor/Cabeça (R$)",
                                    "Qtd Mae", "Qtd Deyvid", "Qtd Nilson", "Descrição", "Registrado Por"],
                           rows=rows, ordem=ordem)

@app.route("/compras/nova", methods=["GET", "POST"])
@login_required
def nova_compra():
    dados = carregar_todas()
    cmp_atual = calcular_cmp(dados["Compras"])
    if request.method == "POST":
        f = request.form
        data    = f.get("data", datetime.now().strftime("%d/%m/%Y"))
        cabecas = int(f.get("cabecas", 0) or 0)
        valor   = parse_valor(f.get("valor", 0))
        desc    = f.get("descricao", "").strip()
        membro  = f.get("membro", "")

        # Validação
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
                           hoje=datetime.now().strftime("%Y-%m-%d"))

@app.route("/compras/editar/<int:idx>", methods=["GET", "POST"])
@login_required
def editar_compra(idx):
    df = carregar_aba("Compras")
    if df.empty or idx >= len(df):
        flash("Registro não encontrado.", "error")
        return redirect(url_for("compras"))
    if request.method == "POST":
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
                df[col] = None
                df.at[idx, col] = val
        reescrever_aba("Compras", df)
        flash("Compra atualizada!", "success")
        return redirect(url_for("compras"))
    row = df.iloc[idx].to_dict()
    row["Data"] = fmt_data(row.get("Data"))
    row["data_input"] = df.iloc[idx]["Data"].strftime("%Y-%m-%d") if pd.notna(df.iloc[idx]["Data"]) else ""
    return render_template("form_compra.html", modo="editar", row=row, idx=idx,
                           cmp_atual=calcular_cmp(df), MEMBROS=MEMBROS, NOMES=NOMES_MEMBROS,
                           hoje=datetime.now().strftime("%Y-%m-%d"))


# ── GASTOS ──

@app.route("/gastos")
@login_required
def gastos():
    dados = carregar_todas()
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
                           colunas=["Data", "Tipo", "Descrição", "Valor Total (R$)",
                                    "Qtd Cabeças", "Valor/Cabeça (R$)", "Registrado Por"],
                           rows=rows, ordem=ordem)

@app.route("/gastos/novo", methods=["GET", "POST"])
@login_required
def novo_gasto():
    dados = carregar_todas()
    estoque = calcular_estoque(dados["Compras"], dados["Vendas"], dados["Manejo"])
    # BUG CORRIGIDO: passa contexto completo para GPCab ser calculado corretamente,
    # incluindo gastos importados com Qtd=0 e Val/Cab=0
    gpcab = calcular_gpcab(dados["Gastos"], dados["Compras"], dados["Vendas"], dados["Manejo"])
    if request.method == "POST":
        f = request.form
        data   = f.get("data", datetime.now().strftime("%d/%m/%Y"))
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
                           hoje=datetime.now().strftime("%Y-%m-%d"))

@app.route("/gastos/editar/<int:idx>", methods=["GET", "POST"])
@login_required
def editar_gasto(idx):
    dados   = carregar_todas()
    df      = carregar_aba("Gastos")
    estoque = calcular_estoque(dados["Compras"], dados["Vendas"], dados["Manejo"])
    # BUG CORRIGIDO: passa contexto completo
    gpcab   = calcular_gpcab(dados["Gastos"], dados["Compras"], dados["Vendas"], dados["Manejo"])
    if df.empty or idx >= len(df):
        flash("Registro não encontrado.", "error")
        return redirect(url_for("gastos"))
    if request.method == "POST":
        f      = request.form
        data   = f.get("data", "")
        tipo   = f.get("tipo", "")
        desc   = f.get("descricao", "").strip()
        valor  = parse_valor(f.get("valor", 0))
        cab    = int(f.get("cabecas", estoque) or estoque)
        membro = f.get("membro", "")
        if cab <= 0:
            cab = max(1, estoque)
        v_cab  = round(valor / cab, 4) if cab > 0 else 0
        fazer_backup()
        _limpar_backups_antigos()
        updates = {
            "Data": pd.to_datetime(data, dayfirst=True, errors="coerce"),
            "Tipo": tipo, "Descrição": desc,
            "Valor Total (R$)": valor, "Qtd Cabeças": cab,
            "Valor/Cabeça (R$)": v_cab, "Registrado Por": membro,
        }
        for col, val in updates.items():
            if col in df.columns:
                df.at[idx, col] = val
            else:
                df[col] = None
                df.at[idx, col] = val
        reescrever_aba("Gastos", df)
        flash("Gasto atualizado!", "success")
        return redirect(url_for("gastos"))
    row = df.iloc[idx].to_dict()
    row["Data"] = fmt_data(row.get("Data"))
    row["data_input"] = df.iloc[idx]["Data"].strftime("%Y-%m-%d") if pd.notna(df.iloc[idx].get("Data")) else ""
    return render_template("form_gasto.html", modo="editar", row=row, idx=idx,
                           estoque=estoque, gpcab=gpcab,
                           TIPOS=TIPOS_GASTO, MEMBROS=MEMBROS, NOMES=NOMES_MEMBROS,
                           hoje=datetime.now().strftime("%Y-%m-%d"))


# ── VENDAS ──

@app.route("/vendas")
@login_required
def vendas():
    dados = carregar_todas()
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
                           colunas=["Data", "Qtd Cabeças", "Valor Total (R$)", "Valor/Cabeça (R$)",
                                    "Valor Arroba (R$)", "Qtd Mae", "Qtd Deyvid", "Qtd Nilson",
                                    "Valor Mae (R$)", "Valor Deyvid (R$)", "Valor Nilson (R$)", "Descrição"],
                           rows=rows, ordem=ordem)

@app.route("/vendas/nova", methods=["GET", "POST"])
@login_required
def nova_venda():
    dados = carregar_todas()
    r_fin = calcular_resumo_financeiro(dados["Compras"], dados["Gastos"], dados["Vendas"], dados["Manejo"])
    if request.method == "POST":
        cabecas = int(request.form.get("cabecas", 0) or 0)
        if cabecas <= 0:
            flash("Informe ao menos 1 cabeça.", "error")
            return redirect(url_for("nova_venda"))
        _salvar_venda(request.form, dados)
        flash("Venda registrada!", "success")
        return redirect(url_for("vendas"))
    return render_template("form_venda.html", modo="nova", row=None, idx=None, r_fin=r_fin,
                           MEMBROS=MEMBROS, NOMES=NOMES_MEMBROS,
                           hoje=datetime.now().strftime("%Y-%m-%d"))

@app.route("/vendas/editar/<int:idx>", methods=["GET", "POST"])
@login_required
def editar_venda(idx):
    dados = carregar_todas()
    df    = carregar_aba("Vendas")
    if df.empty or idx >= len(df):
        flash("Registro não encontrado.", "error")
        return redirect(url_for("vendas"))
    r_fin = calcular_resumo_financeiro(dados["Compras"], dados["Gastos"], dados["Vendas"], dados["Manejo"])
    if request.method == "POST":
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
                           hoje=datetime.now().strftime("%Y-%m-%d"))


# ── MANEJO ──

@app.route("/manejo")
@login_required
def manejo():
    dados = carregar_todas()
    df = dados["Manejo"]
    rows = []
    for real_idx, row in (df.iterrows() if not df.empty else []):
        d = row.to_dict()
        d["Data"] = fmt_data(d.get("Data"))
        d["_idx"] = int(real_idx)
        rows.append(d)
    return render_template("lista.html", titulo="Manejo 🩺", secao="manejo", aba="Manejo",
                           colunas=["Data", "Tipo", "Qtd Cabeças", "Descrição", "Responsável"],
                           rows=rows)

@app.route("/manejo/novo", methods=["GET", "POST"])
@login_required
def novo_manejo():
    dados   = carregar_todas()
    estoque = calcular_estoque(dados["Compras"], dados["Vendas"], dados["Manejo"])
    if request.method == "POST":
        f = request.form
        salvar_linha("Manejo", [f.get("data"), f.get("tipo"), int(f.get("cabecas", 0) or 0),
                                f.get("descricao", "").strip(), f.get("responsavel", "")])
        flash(f"Manejo registrado! ({f.get('tipo')})", "success")
        return redirect(url_for("manejo"))
    return render_template("form_manejo.html", estoque=estoque, TIPOS=TIPOS_MANEJO,
                           MEMBROS=MEMBROS, NOMES=NOMES_MEMBROS,
                           hoje=datetime.now().strftime("%Y-%m-%d"))


# ── RELATÓRIOS ──

@app.route("/relatorios")
@login_required
def relatorios():
    dados = carregar_todas()
    r_fin = calcular_resumo_financeiro(dados["Compras"], dados["Gastos"], dados["Vendas"], dados["Manejo"])
    mbr   = calcular_todos_membros(dados["Vendas"], dados["Compras"], dados["Gastos"], dados["Manejo"])
    gastos_tipo = calcular_gasto_por_tipo(dados["Gastos"])
    extras      = calcular_indicadores_extras(
        dados["Compras"], dados["Gastos"], dados["Vendas"], dados["Manejo"],
        r_fin["ctcab"]
    )
    return render_template("relatorios.html", r=r_fin, mbr=mbr,
                           alertas=_gerar_alertas(dados), anual=_calc_anual(dados),
                           gastos_tipo=gastos_tipo, extras=extras,
                           MEMBROS=MEMBROS, NOMES=NOMES_MEMBROS, EMOJIS=EMOJIS_MEMBROS)


# ── EXCLUIR ──

@app.route("/excluir/<aba>/<int:idx>", methods=["POST"])
@login_required
def excluir(aba, idx):
    fazer_backup()
    _limpar_backups_antigos()
    df = carregar_aba(aba)
    if not df.empty and idx < len(df):
        df = df.drop(df.index[idx]).reset_index(drop=True)
        reescrever_aba(aba, df)
        flash("Registro excluído.", "warning")
    return redirect(url_for({"Compras": "compras", "Gastos": "gastos",
                              "Vendas": "vendas", "Manejo": "manejo"}.get(aba, "dashboard")))


# ── IMPORTAR ──

@app.route("/importar", methods=["GET", "POST"])
@login_required
def importar():
    if request.method == "POST":
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
                        ng += 1
                        gastos_ano += 1
                if gastos_ano:
                    detalhes.append({"tipo": "gasto", "ano": ano,
                                     "msg": f"{gastos_ano} gastos importados"})

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
                                            0, 0, 0, 0, 0, 0, 0,
                                            f"Importado de {ano}"])
                    nv += 1
                    detalhes.append({"tipo": "venda", "ano": ano,
                                     "msg": f"Venda: {tq} cabeças — R$ {tv:,.2f} "
                                            f"(Geane {int(mae_q)} · Deyvid {int(dev_q)} · Nilson {int(nil_q)})"})
            return render_template("importar.html", concluido=True, anos=anos,
                                   nc=nc, ng=ng, nv=nv, detalhes=detalhes)
        except Exception as e:
            flash(f"Erro na importação: {e}", "error")
            return redirect(url_for("importar"))
        finally:
            os.unlink(tmp.name)
    return render_template("importar.html", concluido=False, anos=[], detalhes=[])


# ── EXPORTAR / BACKUP ──

@app.route("/exportar")
@login_required
def exportar():
    from db import DATA_DIR
    nome = exportar_relatorio_excel()
    nome_abs = nome if os.path.isabs(nome) else os.path.join(DATA_DIR, nome)
    return send_file(nome_abs, as_attachment=True,
                     download_name=f"relatorio_gado_{datetime.now().strftime('%Y%m%d')}.xlsx")

@app.route("/backup", methods=["POST"])
@login_required
def backup():
    nome = fazer_backup()
    _limpar_backups_antigos()
    flash(f"Backup salvo: {nome}", "success")
    return redirect(url_for("dashboard"))


# ── Gerenciamento de usuários ─────────────────────────────────────────────────

def _usuarios_path() -> str:
    from db import DATA_DIR
    return os.path.join(DATA_DIR, "usuarios.json")


def _carregar_usuarios() -> dict:
    """
    Carrega usuários do arquivo usuarios.json (DATA_DIR).
    Se não existir ainda, inicializa a partir do config.py e salva o JSON.
    Formato: { "nome": {"hash": "...", "criado": "DD/MM/YYYY"} }
    """
    import json
    caminho = _usuarios_path()
    if os.path.exists(caminho):
        try:
            with open(caminho, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    # Primeira execução — migrar do config.py
    dados = {
        u: {"hash": h, "criado": datetime.now().strftime("%d/%m/%Y")}
        for u, h in USUARIOS.items()
    }
    _salvar_usuarios(dados)
    return dados


def _salvar_usuarios(dados: dict):
    import json
    caminho = _usuarios_path()
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)


def _verificar_senha(usuario: str, senha: str) -> bool:
    """Verifica se a senha bate com o hash armazenado (JSON ou config.py fallback)."""
    usuarios = _carregar_usuarios()
    if usuario not in usuarios:
        return False
    return _hash(senha) == usuarios[usuario]["hash"]


@app.route("/configuracoes")
@login_required
def configuracoes():
    usuarios = _carregar_usuarios()
    return render_template("configuracoes.html", usuarios=usuarios)


@app.route("/configuracoes/trocar-senha", methods=["POST"])
@login_required
def trocar_senha():
    usuario   = session["usuario"]
    atual     = request.form.get("senha_atual",  "").strip()
    nova      = request.form.get("senha_nova",   "").strip()
    conf      = request.form.get("senha_conf",   "").strip()

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
    dados[usuario]["hash"] = _hash(nova)
    _salvar_usuarios(dados)
    flash("✅ Senha alterada com sucesso!", "success")
    return redirect(url_for("configuracoes"))


@app.route("/configuracoes/adicionar-usuario", methods=["POST"])
@login_required
def adicionar_usuario():
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
        "hash":   _hash(senha),
        "criado": datetime.now().strftime("%d/%m/%Y"),
    }
    _salvar_usuarios(dados)
    flash(f"✅ Usuário '{novo_user.capitalize()}' criado!", "success")
    return redirect(url_for("configuracoes"))


@app.route("/configuracoes/excluir-usuario", methods=["POST"])
@login_required
def excluir_usuario():
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
    alvo  = request.form.get("usuario",    "").strip().lower()
    senha = request.form.get("senha_nova", "").strip()

    if len(senha) < 4:
        flash("A senha precisa ter pelo menos 4 caracteres.", "error")
        return redirect(url_for("configuracoes"))

    dados = _carregar_usuarios()
    if alvo not in dados:
        flash("Usuário não encontrado.", "error")
        return redirect(url_for("configuracoes"))

    dados[alvo]["hash"] = _hash(senha)
    _salvar_usuarios(dados)
    flash(f"✅ Senha de '{alvo.capitalize()}' redefinida!", "success")
    return redirect(url_for("configuracoes"))


if __name__ == "__main__":
    inicializar()
    import webbrowser, threading

    PORTA = 5000

    # ── Ngrok (opcional) ──────────────────────────────────────────────────────
    # Para ativar: defina a variável de ambiente NGROK_TOKEN com seu authtoken,
    # ou cole o token direto na variável abaixo (entre as aspas).
    # Obtenha em: https://dashboard.ngrok.com/get-started/your-authtoken
    #
    # BUG CORRIGIDO: antes, o token estava sendo usado como NOME da variável de
    # ambiente (os.environ.get("<token>", "")) — nunca funcionava.
    # Agora usa corretamente a variável de ambiente "NGROK_TOKEN".
    NGROK_TOKEN = os.environ.get("NGROK_TOKEN", "")
    # Para usar sem variável de ambiente, cole o token aqui:
    # NGROK_TOKEN = "3DbSQ7lb5EZX0tZuB6n6sN2uhDF_57PYTKk99ViUqVPhLSt2H"

    url_publica = None
    if NGROK_TOKEN:
        try:
            import ngrok
            ngrok.set_auth_token(NGROK_TOKEN)
            listener    = ngrok.forward(PORTA, authtoken=NGROK_TOKEN,
                                        domain="sitiosantoantonio.ngrok-free.dev")
            url_publica = listener.url()
        except ImportError:
            print("⚠️  ngrok não instalado. Rode:  pip install ngrok")
        except Exception as e:
            print(f"⚠️  ngrok não iniciou: {e}")
    # ─────────────────────────────────────────────────────────────────────────

    def abrir_browser():
        webbrowser.open(f"http://localhost:{PORTA}")

    threading.Timer(1.2, abrir_browser).start()

    print("\n🐄 Sítio Santo Antonio — Sistema de Gado")
    print(f"   Local:  http://localhost:{PORTA}")
    if url_publica:
        print(f"   🌐 Ngrok: {url_publica}  ← compartilhe este link")
    else:
        print("   (ngrok inativo — defina NGROK_TOKEN para acesso externo)")
    print("   Para encerrar: Ctrl+C\n")

    app.run(debug=False, port=PORTA)
