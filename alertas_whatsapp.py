#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
alertas_whatsapp.py — Sítio Santo Antonio
==========================================
Envia alertas automáticos via WhatsApp (CallMeBot) para todos os
membros da família que tiverem o WhatsApp configurado no sistema.

Configure no PythonAnywhere em:
  Dashboard → Tasks → Add a new scheduled task
  Comando: python3 /home/deyvidgt16/gado/alertas_whatsapp.py
  Horário: Daily às 07:00

Segunda-feira: resumo semanal completo. Outros dias: só alertas URGENTES
(vacina atrasada/vencendo, insumo acabando, muitos dias sem visita, lembrete de
campanha), cada um repetido no máximo a cada poucos dias. Sem urgência, nada é
enviado. Teste sem enviar:  python3 alertas_whatsapp.py --teste [--semanal]
"""
from __future__ import annotations
from agora import agora

import os
import sys
import json
import logging
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

# ── Configuração ──────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))
# Log junto dos dados (~/gado-dados/backups/), não na pasta do código.
from db import _resolver_data_dir  # noqa: E402
LOG_FILE = Path(_resolver_data_dir()) / "backups" / "alertas_whatsapp.log"
Path(LOG_FILE).parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%d/%m/%Y %H:%M:%S",
)

sys.path.insert(0, str(BASE_DIR))

# ── Imports do sistema ────────────────────────────────────────────────────────
try:
    from db import carregar_aba, carregar_todas, get_alertas_saude
    from calculos import calcular_estoque, calcular_resumo_financeiro
except Exception as e:
    logging.error(f"Erro ao importar módulos do sistema: {e}")
    sys.exit(1)


# ── Helpers ───────────────────────────────────────────────────────────────────

URL_SISTEMA = "https://deyvidgt16.pythonanywhere.com"

def _cabecalho() -> str:
    """1ª linha das mensagens: o nome do sítio de onde vem (vários sítios, v5.0)."""
    import sitios
    return f"🐄 *{sitio_nome()}*"


def sitio_nome() -> str:
    import sitios
    return sitios.nome(sitios.atual())


def fmt_r(v):
    try:
        return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "—"


def _texto_whatsapp(valor) -> str:
    return valor.strip() if isinstance(valor, str) else ""


def carregar_usuarios() -> dict:
    """
    Carrega usuarios.json da pasta da família (db.RAIZ, ~/gado-dados/), que é onde
    o sistema salva as configurações de WhatsApp. Fallback para BASE_DIR em dev local.
    """
    from db import RAIZ
    candidatos = [
        Path(RAIZ) / "usuarios.json",       # produção: ~/gado-dados/
        BASE_DIR / "usuarios.json",         # desenvolvimento local
    ]
    for caminho in candidatos:
        if caminho.exists():
            try:
                usuarios = json.loads(caminho.read_text(encoding="utf-8"))
                if isinstance(usuarios, dict):
                    return usuarios
                logging.error("Arquivo de usuários inválido em %s: conteúdo não é um objeto.", caminho)
            except (OSError, ValueError) as e:
                logging.error(f"Não foi possível ler usuários em {caminho}: {e}")
    return {}


def enviar_whatsapp_resultado(telefone: str, apikey: str, msg: str) -> dict:
    """Envia pelo CallMeBot e devolve erro legível sem expor credenciais."""
    try:
        import requests
        resp = requests.get(
            "https://api.callmebot.com/whatsapp.php",
            params={"phone": telefone, "text": msg, "apikey": apikey},
            timeout=20,
        )
        corpo = resp.text.lower()
        if resp.status_code == 200 and "message queued" in corpo:
            logging.info("WhatsApp enviado para %s*** OK", telefone[:6])
            return {"ok": True, "erro": None}
        if "phone number not correct" in corpo or "incorrect phone" in corpo:
            erro = ("Número inválido ou não autorizado no CallMeBot. Confira o telefone "
                    "e se a autorização foi enviada ao número do bot.")
        elif "apikey" in corpo or "api key" in corpo or "not found" in corpo:
            erro = ("API Key inválida ou expirada. Confira a API Key e o número do bot "
                    "nas configurações do WhatsApp.")
        elif resp.status_code == 403:
            erro = "Acesso negado pelo CallMeBot (erro 403). Confira o número do bot."
        else:
            erro = f"CallMeBot retornou erro HTTP {resp.status_code}."
        logging.warning("WhatsApp para %s*** falhou: %s", telefone[:6], erro)
        return {"ok": False, "erro": erro}
    except Exception as e:
        tipo_erro = type(e).__name__
        logging.error("Erro ao enviar WhatsApp para %s*** (%s)", telefone[:6], tipo_erro)
        msg_e = tipo_erro.lower()
        if any(k in msg_e for k in ("proxyerror", "max retries", "connectionerror",
                                     "tunnel connection", "timeout", "requestexception")):
            erro = ("Servidor sem acesso ao CallMeBot (restrição de rede do PythonAnywhere). "
                    "O envio funciona pelo celular ou pelo script local.")
        else:
            erro = "Erro inesperado ao comunicar com o CallMeBot."
        return {"ok": False, "erro": erro}


def enviar_whatsapp(telefone: str, apikey: str, msg: str) -> bool:
    """Envia mensagem via CallMeBot. Retorna True se enviou com sucesso."""
    return enviar_whatsapp_resultado(telefone, apikey, msg)["ok"]


def _str_campo(v, default="—"):
    """Converte valor de célula para string legível, tratando NaN/None."""
    import pandas as pd
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return default
    s = str(v).strip()
    return s if s else default


def _num_campo(v) -> float:
    """Número de célula; vazio (NaN) vira 0. `NaN or 0` continua NaN e int(NaN)
    derrubava o relatório diário inteiro — ninguém recebia nada naquele dia."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return 0.0
    return f if f == f else 0.0


# ── Mensagem de NOVA VISITA (disparada ao registrar) ─────────────────────────

def montar_msg_nova_visita(row: dict, estoque_esperado: int) -> str:
    """
    Monta mensagem WhatsApp completa ao registrar uma nova visita.
    Detalha tudo: quem foi, gado, pastagem, água, sal, sugestões.
    """
    import pandas as pd

    def _v(campo, default="—"):
        val = row.get(campo)
        return _str_campo(val, default)

    responsavel = _v("Responsável", "?")
    data_vis    = row.get("Data")
    if isinstance(data_vis, pd.Timestamp) and pd.notna(data_vis):
        data_str = data_vis.strftime("%d/%m/%Y")
    elif isinstance(data_vis, str) and data_vis:
        data_str = data_vis
    else:
        data_str = _agora_br().strftime("%d/%m/%Y")

    gado_cnt  = int(_num_campo(row.get("Gado Contado")))
    gado_esp  = int(_num_campo(row.get("Gado Esperado")) or estoque_esperado)
    gado_falt = int(_num_campo(row.get("Gado Faltando")))

    sal      = _v("Sal/Ração",    "OK")
    prot     = _v("Proteinado",   "OK")
    mato     = _v("Mato/Vegetação", "Limpo")
    grama    = _v("Grama/Pastagem", "Boa")
    corrego  = _v("Córrego/Água", "Normal")
    quintal  = _v("Quintal",      "OK")
    cisterna = _v("Cisterna",     "OK")
    choveu   = _v("Choveu",       "Não")
    chuva_mm = _num_campo(row.get("Chuva mm"))
    obs      = _v("Observações",  "")
    sug      = _v("Sugestões",    "")

    # ── Ícones de status ──────────────────────────────────────────────────────
    def _icone_nivel(v, ok_vals, warn_vals):
        if v in ok_vals:  return "✅"
        if v in warn_vals: return "⚠️"
        return "🚨"

    i_sal  = _icone_nivel(sal,     ["OK"],             ["Meio Saco", "Baixo"])
    i_prot = _icone_nivel(prot,    ["OK"],             ["Meio Saco", "Baixo"])
    i_gram = _icone_nivel(grama,   ["Boa"],            ["Regular", "Amarelando/Secando"])
    i_corr = _icone_nivel(corrego, ["Normal"],         ["Baixo"])
    i_cist = _icone_nivel(cisterna,["OK"],             ["Baixo/Secando"])
    i_mato = _icone_nivel(mato,    ["Limpo"],          ["Precisa Capinar"])
    i_quin = _icone_nivel(quintal, ["OK"],             [])

    # ── Gado ─────────────────────────────────────────────────────────────────
    if gado_cnt > 0:
        if gado_falt > 0:
            gado_info = f"🚨 FALTANDO {gado_falt} cab! (contado: {gado_cnt} / esperado: {gado_esp})"
        elif gado_cnt > gado_esp:
            extra = gado_cnt - gado_esp
            gado_info = f"✅ {gado_cnt} cab (+ {extra} a mais que esperado)"
        else:
            gado_info = f"✅ {gado_cnt}/{gado_esp} cab — conferido"
    else:
        gado_info = "➖ Gado não contado"

    # ── Chuva ────────────────────────────────────────────────────────────────
    if choveu == "Sim":
        if chuva_mm >= 50:
            chuva_info = f"🌧️ Chuva forte: {chuva_mm:g}mm"
        elif chuva_mm >= 15:
            chuva_info = f"🌦️ Boa chuva: {chuva_mm:g}mm"
        elif chuva_mm > 0:
            chuva_info = f"🌂 Chuva leve: {chuva_mm:g}mm"
        else:
            chuva_info = "🌧️ Choveu (mm não informado)"
    else:
        chuva_info = "☀️ Sem chuva"

    # ── Sugestões como lista (separadas por " | ") ────────────────────────────
    sugestoes_fmt = ""
    if sug and sug != "—":
        itens = [s.strip() for s in sug.split("|") if s.strip()]
        if itens:
            sugestoes_fmt = "\n📌 *Sugestões:*\n" + "\n".join(f"  {it}" for it in itens)

    # ── Observações ───────────────────────────────────────────────────────────
    obs_fmt = f"\n📝 *Obs:* {obs}" if obs and obs != "—" else ""

    # ── Montagem final ────────────────────────────────────────────────────────
    linhas = [
        _cabecalho(),
        f"🏡 *Nova visita registrada!*",
        f"",
        f"👤 *Quem visitou:* {responsavel}",
        f"📅 *Data:* {data_str}",
        f"",
        f"🐄 *Gado:* {gado_info}",
        f"",
        f"🌾 *Condições do sítio:*",
        f"  {i_sal} Sal/Ração: {sal}",
        f"  {i_prot} Proteinado: {prot}",
        f"  {i_gram} Pastagem: {grama}",
        f"  {i_corr} Água/Córrego: {corrego}",
        f"  {i_cist} Cisterna: {cisterna}",
        f"  {i_mato} Vegetação/Mato: {mato}",
        f"  {i_quin} Quintal: {quintal}",
        f"  {chuva_info}",
    ]

    if sugestoes_fmt:
        linhas.append(sugestoes_fmt)
    if obs_fmt:
        linhas.append(obs_fmt)

    linhas += [
        f"",
        f"👉 *Aceder ao sistema:* {URL_SISTEMA}",
        f"_Sistema de Gestão de Gado — {sitio_nome()}_",
    ]
    return "\n".join(linhas)


# ── Itens do relatório ────────────────────────────────────────────────────────
# Cada item: {"chave", "urgente", "repetir", "texto"}.
#   urgente — entra na mensagem dos dias comuns (os demais só no resumo semanal)
#   repetir — um alerta urgente já enviado só volta depois de N dias, para a
#             família não receber a mesma coisa todo dia e parar de ler.
DIA_RESUMO_SEMANAL = 0          # 0 = segunda-feira
REPETIR_URGENTE_DIAS = 3
DIAS_SEM_VISITA_URGENTE = 14
BRUCELOSE_URGENTE_DIAS = 15     # faltando tantos dias para fechar a janela (240 d), vira urgente
BRUCELOSE_FIM_JANELA_DIAS = 240


def _agora_br() -> datetime:
    """Hora de Brasília (o servidor do PythonAnywhere roda em UTC)."""
    try:
        from zoneinfo import ZoneInfo
        return agora()
    except Exception:
        return agora()


def montar_itens(hoje: datetime | None = None) -> list[dict]:
    import pandas as pd
    hoje = hoje or _agora_br()
    itens = []

    def item(chave, texto, urgente=False, repetir=REPETIR_URGENTE_DIAS, valores=False):
        # valores=True: linha com R$, que some para quem desligou "valores"
        itens.append({"chave": chave, "texto": texto, "urgente": urgente,
                      "repetir": repetir, "valores": valores})

    try:
        dados  = carregar_todas()
        df_c, df_g, df_v = dados["Compras"], dados["Gastos"], dados["Vendas"]
        df_m, df_vis     = dados["Manejo"], dados["Visitas"]
        df_colchao = carregar_aba("Leite Colchão") if "Leite Colchão" in dados else None
    except Exception as e:
        logging.error(f"Erro ao carregar dados: {e}")
        item("erro:dados", f"❌ Erro ao ler dados do sistema: {e}", urgente=True)
        return itens

    # ── 1) Saúde: vacinas, vermifugação, pesagem… ────────────────────────────
    from saude import ultima_data, lembretes_sazonais
    hoje_d = datetime(hoje.year, hoje.month, hoje.day)
    for tipo, intervalo in get_alertas_saude().items():
        ult = ultima_data(df_m, tipo)
        if ult is None:
            continue   # "nenhum registro ainda" toda semana era ruído
        prevista = ult.to_pydatetime() + timedelta(days=intervalo)
        faltam = (prevista - hoje_d).days
        if faltam < 0:
            item(f"saude:{tipo}:atrasada",
                 f"⚠️ {tipo} ATRASADA — era para {prevista:%d/%m/%Y} "
                 f"(última: {ult:%d/%m/%Y}).", urgente=True)
        elif faltam <= 7:
            item(f"saude:{tipo}:vence",
                 f"⏰ {tipo} vence em {faltam} dia(s) — {prevista:%d/%m/%Y}.", urgente=True)
        elif faltam <= 21:
            item(f"saude:{tipo}:proxima", f"🗓️ {tipo} prevista para {prevista:%d/%m/%Y}.")

    # Campanhas (brucelose, vermifugação 5-7-9) duram meses: urgentes só nos dias
    # de lembrete; no resto do período aparecem no resumo semanal.
    dia_lembrete = hoje.day in (1, 15, 25) or (hoje.month in (1, 7) and hoje.day in (5, 9))
    for i, lemb in enumerate(lembretes_sazonais(df_m, hoje)):
        item(f"campanha:{hoje:%Y%m%d}:{i}", f"🗓️ {lemb['msg']}", urgente=dia_lembrete, repetir=1)

    # ── 1b) Agenda de tarefas: atrasadas e as dos próximos dias ──────────────
    try:
        import tarefas as T
        for t in T.pendentes(T.carregar(), hoje, limite_dias=7):
            if t["situacao"] == "atrasada":
                texto = f"⚠️ Tarefa ATRASADA ({-t['dias']} dia(s)): {t['titulo']}"
            elif t["situacao"] == "hoje":
                texto = f"📌 Tarefa de hoje: {t['titulo']}"
            else:
                texto = f"📋 {t['titulo']} — {t['data']:%d/%m} (em {t['dias']} dia(s))"
            if t["responsavel"]:
                texto += f" — {t['responsavel']}"
            item(f"tarefa:{t['id']}:{t['situacao']}", texto,
                 urgente=t["situacao"] in ("atrasada", "hoje"), repetir=1)
    except Exception as e:
        logging.error(f"Erro nas tarefas: {e}")

    # ── 1c) Reprodução: parto chegando e toque atrasado ──────────────────────
    try:
        import animais as A
        import reproducao as R
        df_an = A.carregar()
        for a in R.alertas(R.situacao(df_m, df_an, hoje), hoje):
            item(a["chave"], a["texto"], urgente=a["urgente"], repetir=1)
    except Exception as e:
        logging.error(f"Erro na reprodução: {e}")

    # ── 1d) Colchão: troca vencida ou próxima ────────────────────────────────
    try:
        from leite import historico_colchao
        if df_colchao is not None and not df_colchao.empty:
            historicos = historico_colchao(df_colchao, referencia=hoje_d)
            for local, hist in historicos.items():
                # Urgente: próxima troca <= 7 dias
                if hist and hist.get("status") == "urgente" and hist.get("dias_para_troca") is not None:
                    dias = hist["dias_para_troca"]
                    item(f"colchao:{local}:urgente",
                         f"🛏️ Colchão {local} vence em {dias} dia(s) — marque a troca",
                         urgente=True, repetir=2)
    except Exception as e:
        logging.error(f"Erro nos alertas de colchão: {e}")

    # ── 2) Insumos: previsão de estoque ──────────────────────────────────────
    try:
        from insumos import previsao_todos, texto_previsao
        for p in previsao_todos(df_vis, df_g, hoje):
            if p["status"] == "sem_dados":
                continue
            urg = p["status"] in ("urgente", "acabou")
            icone = "🚨" if urg else ("⚠️" if p["status"] == "proximo" else "🧂")
            item(f"insumo:{p['produto']}:{p['status']}", f"{icone} {texto_previsao(p)}", urgente=urg)
    except Exception as e:
        logging.error(f"Erro na previsão de insumos: {e}")

    # ── 3) Última visita ─────────────────────────────────────────────────────
    if not df_vis.empty and "Data" in df_vis.columns and df_vis["Data"].notna().any():
        df_s = df_vis.sort_values("Data", ascending=False, na_position="last")
        v = df_s.iloc[0]
        data_v = df_s["Data"].dropna().max()
        dias = (hoje_d - data_v.to_pydatetime()).days
        item("visita:resumo",
             f"🏡 *Última visita:* {data_v:%d/%m/%Y} por {_str_campo(v.get('Responsável'), '?')} "
             f"({dias}d atrás)")
        falt = int(_num_campo(v.get("Gado Faltando")))
        cnt = int(_num_campo(v.get("Gado Contado")))
        esp = int(_num_campo(v.get("Gado Esperado")))
        if falt > 0:
            item("visita:faltando", f"  🚨 Gado faltando: {falt} cab. (contado {cnt} / esperado {esp})")
        elif cnt > 0:
            item("visita:gado", f"  ✅ Gado: {cnt}/{esp} cab. conferidos")
        for campo, rotulo, ruins in (("Sal/Ração", "Sal", ("Vazio", "Baixo")),
                                     ("Proteinado", "Proteinado", ("Vazio", "Baixo")),
                                     ("Córrego/Água", "Água/Córrego", ("Seco", "Baixo")),
                                     ("Grama/Pastagem", "Pastagem", ("Escassa", "Amarelando/Secando")),
                                     ("Cisterna", "Cisterna", ("Vazia", "Baixo/Secando"))):
            val = _str_campo(v.get(campo), "")
            if val in ruins:
                item(f"visita:{campo}", f"  ⚠️ {rotulo}: {val}")
        if dias >= DIAS_SEM_VISITA_URGENTE:
            item("visita:sem", f"📅 Sem visita há {dias} dias — hora de ir ao sítio!",
                 urgente=True, repetir=7)
    else:
        item("visita:nenhuma", "📅 Nenhuma visita registrada ainda.")

    # ── 4) Financeiro (só no resumo semanal) ─────────────────────────────────
    try:
        if not df_c.empty:
            r = calcular_resumo_financeiro(df_c, df_g, df_v, df_m)
            item("fin:resumo",
                 f"💰 Rebanho: {r['estoque']} cab. · custo médio {fmt_r(r['ctcab'])}/cab. · "
                 f"break-even {fmt_r(r['break_even'])}/cab.", valores=True)
    except Exception as e:
        logging.error(f"Erro no resumo financeiro: {e}")

    # ── 4b) Brucelose por animal: fêmeas na janela de 3 a 8 meses ────────────
    try:
        import animais
        df_an = animais.carregar()
        for b in animais.janela_brucelose(df_an, df_m, hoje):
            a = b["animal"]
            nome = animais.fmt_brinco(a["Brinco Cor"], a["Brinco Nº"])
            if b["situacao"] == "na janela":
                faltam = BRUCELOSE_FIM_JANELA_DIAS - (hoje - a["Nascimento"]).days
                item(f"brucelose:{a['ID']}", f"💉 Brucelose: {nome} — {b['msg']}",
                     urgente=faltam <= BRUCELOSE_URGENTE_DIAS)
            else:
                item(f"brucelose:{a['ID']}", f"🗓️ Brucelose: {nome} {b['msg']}")
    except Exception as e:
        logging.error(f"Erro na brucelose por animal: {e}")

    # ── 5) Fotos: Drive parou de aceitar (token revogado, pasta sumiu…) ───────
    # As fotos ficam guardadas nos celulares; o aviso é para alguém consertar.
    try:
        import drive
        if drive.configurado() and drive.cliente() is not None:
            ok, msg = drive.cliente().testar()
            if not ok:
                item("drive:erro", f"📷 Fotos: o Google Drive não está aceitando envios — {msg}",
                     urgente=True, repetir=1)
    except Exception as e:
        logging.error(f"Erro ao testar o Drive: {e}")

    return itens


# ── Controle do que já foi enviado (para não repetir alerta todo dia) ────────

def _estado_path() -> Path:
    from db import DATA_DIR
    return Path(DATA_DIR) / "whatsapp_estado.json"


def _ler_estado() -> dict:
    try:
        return json.loads(_estado_path().read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def _gravar_estado(estado: dict) -> None:
    try:
        _estado_path().write_text(json.dumps(estado, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        logging.error(f"Não foi possível gravar o estado dos alertas: {e}")


def urgentes_a_enviar(itens: list[dict], hoje: datetime, estado: dict) -> list[dict]:
    """Urgentes que não foram enviados nos últimos `repetir` dias."""
    enviados = estado.get("enviados", {})
    out = []
    for it in itens:
        if not it["urgente"]:
            continue
        ult = enviados.get(it["chave"])
        try:
            if ult and (hoje.date() - datetime.strptime(ult, "%Y-%m-%d").date()).days < it["repetir"]:
                continue
        except ValueError:
            pass
        out.append(it)
    return out


def _marcar_enviados(itens: list[dict], hoje: datetime, estado: dict) -> dict:
    enviados = estado.setdefault("enviados", {})
    for it in itens:
        if it["urgente"]:
            enviados[it["chave"]] = hoje.strftime("%Y-%m-%d")
    # esquece registros com mais de 60 dias
    limite = (hoje - timedelta(days=60)).strftime("%Y-%m-%d")
    estado["enviados"] = {k: v for k, v in enviados.items() if v >= limite}
    return estado


# ── Mensagens ─────────────────────────────────────────────────────────────────

def _sem_valores(itens: list[dict], com_valores: bool) -> list[dict]:
    """Tira as linhas com R$ para quem desligou "valores". Item sem a chave
    (ex.: lista montada por outro código) conta como sem valores."""
    return itens if com_valores else [it for it in itens if not it.get("valores", False)]


def montar_msg_urgente(itens: list[dict], hoje: datetime | None = None,
                       com_valores: bool = True) -> str:
    hoje = hoje or _agora_br()
    itens = _sem_valores(itens, com_valores)
    linhas = [_cabecalho(), f"🚨 *Alertas — {hoje:%d/%m/%Y}*", ""]
    linhas += [it["texto"] for it in itens]
    linhas += ["", "_Resumo completo toda segunda-feira._"]
    return "\n".join(linhas)


def _soma(df, col) -> float:
    """Soma segura de uma coluna (texto/NaN viram 0), no padrão de resumo_mensal."""
    if df is None or df.empty or col not in df.columns:
        return 0.0
    return float(pd.to_numeric(df[col], errors="coerce").fillna(0).sum())


def _da_semana(df, hoje: datetime):
    """Linhas de (hoje-7 dias, hoje], comparando só a data. Sem data (NaT) fica de fora."""
    if df is None or df.empty or "Data" not in df.columns:
        return df.iloc[0:0] if df is not None else pd.DataFrame()
    datas = pd.to_datetime(df["Data"], errors="coerce", dayfirst=True).dt.normalize()
    fim = pd.Timestamp(hoje).normalize()
    return df[(datas > fim - pd.Timedelta(days=7)) & (datas <= fim)]


def resumo_semana(dados: dict, hoje: datetime) -> list[dict]:
    """O que aconteceu nos últimos 7 dias, uma linha por assunto (só se houver
    registro). Cada linha traz o texto com e sem R$ para quem desligou "valores"."""
    def aba(nome):
        return _da_semana(dados.get(nome), hoje)

    linhas: list[dict] = []

    def add(com, sem=None):
        linhas.append({"texto": com, "texto_sem_valores": sem or com})

    vis = aba("Visitas")
    if len(vis):
        nomes = []
        for n in vis.get("Responsável", []):
            n = str(n).strip()
            if n and n.lower() != "nan" and n not in nomes:
                nomes.append(n)
        t = f"🏡 Visitas: {len(vis)}" + (f" ({', '.join(nomes)})" if nomes else "")
        chuva = _soma(vis, "Chuva mm")
        if chuva > 0:
            t += f" · 🌧️ chuva {chuva:g} mm"
        add(t)

    gas = aba("Gastos")
    if len(gas):
        base = f"🧾 Gastos: {len(gas)} lançamentos"
        add(f"{base} — {fmt_r(_soma(gas, 'Valor Total (R$)'))}", base)

    for nome, emoji, rotulo in (("Compras", "🛒", "Compras"), ("Vendas", "💰", "Vendas")):
        df = aba(nome)
        if len(df):
            base = f"{emoji} {rotulo}: {int(_soma(df, 'Qtd Cabeças'))} cab."
            add(f"{base} — {fmt_r(_soma(df, 'Valor Total (R$)'))}", base)

    man = aba("Manejo")
    if len(man):
        tipos = man["Tipo"].astype(str).str.strip()
        especiais = ("Nascimento", "Morte/Perda")
        por_tipo = {}
        for t in tipos[~tipos.isin(especiais)].unique():
            if t and t.lower() != "nan":
                por_tipo[t] = int(_soma(man[tipos == t], "Qtd Cabeças"))
        if por_tipo:
            add("💉 Manejos: " + ", ".join(f"{t} ({q} cab.)" for t, q in por_tipo.items()))
        nasc = int(_soma(man[tipos == "Nascimento"], "Qtd Cabeças"))
        mortes = int(_soma(man[tipos == "Morte/Perda"], "Qtd Cabeças"))
        partes = ([f"🍼 Nascimentos: {nasc}"] if nasc else []) +                  ([f"⚰️ Mortes/perdas: {mortes}"] if mortes else [])
        if partes:
            add(" · ".join(partes))
    return linhas


def montar_msg_semanal(itens: list[dict], hoje: datetime | None = None,
                       com_valores: bool = True, semana: list[dict] | None = None) -> str:
    hoje = hoje or _agora_br()
    itens = _sem_valores(itens, com_valores)
    urg = [it["texto"] for it in itens if it["urgente"]]
    resto = [it["texto"] for it in itens if not it["urgente"]]
    linhas = [_cabecalho(), f"📅 *Resumo semanal — {hoje:%d/%m/%Y}*", ""]
    if urg:
        linhas += ["*⚠️ Atenção*"] + urg + [""]
    if semana is not None:   # None = quem chamou não calculou a semana
        chave = "texto" if com_valores else "texto_sem_valores"
        linhas += ["📆 *Na semana*"] + ([x[chave] for x in semana] or ["Semana sem registros."]) + [""]
    linhas += resto or ["✅ Nada pendente."]
    linhas += ["", "_Sistema de Gestão de Gado_"]
    return "\n".join(linhas)


# Compatibilidade: botão "enviar alertas agora" e chamadas antigas.
def montar_alertas() -> list[str]:
    return [it["texto"] for it in montar_itens()]


def montar_mensagem_alertas(alertas: list[str]) -> str:
    hoje_str = _agora_br().strftime("%d/%m/%Y")
    linhas = [_cabecalho(), f"📅 *Relatório — {hoje_str}*", ""]
    linhas += list(alertas)
    linhas += ["", "_Sistema de Gestão de Gado_"]
    return "\n".join(linhas)


def montar_mensagem(alertas):
    return montar_mensagem_alertas(alertas)


# ── Enviar para toda a família ────────────────────────────────────────────────

TIPOS_RECEBER = ("urgentes", "semanal", "visita", "eventos", "mensal", "valores")

# Login (minúsculo, chave do usuarios.json) -> membro: config.LOGIN_MEMBRO, o mesmo de
# routes_animais._membro_logado: quem registra loga como "geane" mas o aviso traz "Mae".
from config import LOGIN_MEMBRO as _LOGIN_MEMBRO  # noqa: E402


def _chave_pessoa(nome: str) -> str:
    if not isinstance(nome, str):
        return ""
    n = (nome or "").strip().lower()
    return _LOGIN_MEMBRO.get(n, n).lower()


def receber_de(cfg_whatsapp: dict) -> dict:
    """As 6 preferências de recebimento; o que não foi definido vale True, para quem
    nunca mexeu continuar recebendo tudo."""
    guardado = cfg_whatsapp.get("receber") if isinstance(cfg_whatsapp, dict) else None
    if not isinstance(guardado, dict):
        guardado = {}
    return {t: guardado.get(t) if isinstance(guardado.get(t), bool) else True
            for t in TIPOS_RECEBER}


def quer_receber(cfg_whatsapp: dict, tipo: str | None) -> bool:
    """alertas_ativos=False desliga tudo; com tipo=None só ele é considerado."""
    if isinstance(cfg_whatsapp, dict) and cfg_whatsapp.get("alertas_ativos") is False:
        return False
    if tipo is None:
        return True
    return receber_de(cfg_whatsapp).get(tipo, True)


def enviar_para_familia(msg: str, excluir_usuario: str = "", tipo: str | None = None,
                        msg_sem_valores: str | None = None, sitio: str | None = None,
                        destinatarios: list[str] | None = None) -> int:
    return enviar_para_familia_resultado(
        msg, excluir_usuario, tipo, msg_sem_valores, sitio, destinatarios
    )["enviados"]


def enviar_para_familia_resultado(
        msg: str, excluir_usuario: str = "", tipo: str | None = None,
        msg_sem_valores: str | None = None, sitio: str | None = None,
        destinatarios: list[str] | None = None) -> dict:
    """
    Envia e devolve o número de envios e logins que falharam.
    excluir_usuario: pular essa pessoa (membro ou login; ex: quem acabou de registrar).
    tipo: categoria do aviso, filtrada pelas preferências de cada um (None = sem filtro).
    msg_sem_valores: texto alternativo para quem desligou "valores".
    sitio: aviso de um sítio só vai para quem tem acesso a ele (None = sem filtro).
    destinatarios restringe uma tentativa de reenvio aos logins que falharam antes.
    """
    import sitios
    usuarios = carregar_usuarios()
    excluir = _chave_pessoa(excluir_usuario) if excluir_usuario else ""
    somente = {_chave_pessoa(nome) for nome in destinatarios} if destinatarios is not None else None
    enviados = 0
    falhas = []
    elegiveis = 0
    for nome, info in usuarios.items():
        if not isinstance(info, dict):
            continue
        if somente is not None and _chave_pessoa(nome) not in somente:
            continue
        if excluir and _chave_pessoa(nome) == excluir:
            continue
        if sitio and not sitios.tem_acesso(nome, sitio):
            continue
        cfg = info.get("whatsapp", {})
        if not isinstance(cfg, dict):
            continue
        telefone = _texto_whatsapp(cfg.get("telefone"))
        apikey = _texto_whatsapp(cfg.get("apikey"))
        if not telefone or not apikey or not quer_receber(cfg, tipo):
            continue
        elegiveis += 1
        texto = msg
        if tipo is not None and msg_sem_valores is not None and not receber_de(cfg)["valores"]:
            texto = msg_sem_valores
        try:
            enviado = enviar_whatsapp(telefone, apikey, texto)
        except Exception as e:
            logging.error("Erro inesperado ao enviar WhatsApp para %s*** (%s)",
                          telefone[:6], type(e).__name__)
            enviado = False
        if enviado:
            enviados += 1
        else:
            falhas.append(nome)
    return {"enviados": enviados, "falhas": falhas, "elegiveis": elegiveis}


# ── Avisos de visita pendentes ───────────────────────────────────────────────
# O aviso de visita nova é guardado num arquivo ANTES de responder ao celular e
# enviado logo depois. Se a conexão cair no meio (aba fechada, sinal ruim), o
# aviso continua no arquivo e sai na próxima requisição de visita ou na Task
# diária — não se perde mais.

def _pendentes_path() -> Path:
    from db import DATA_DIR
    return Path(DATA_DIR) / "avisos_pendentes.json"


def _trava_fila():
    """Reusa o lock interprocesso do diretório do sítio para operações da fila."""
    from db import _trava_escrita
    return _trava_escrita()


def _ler_fila(caminho: Path) -> list:
    if not caminho.exists():
        return []
    fila = json.loads(caminho.read_text(encoding="utf-8"))
    if not isinstance(fila, list):
        raise ValueError("A fila de avisos precisa ser uma lista JSON.")
    return fila


def _quarentenar_fila(caminho: Path, motivo: str) -> Path:
    stem = "avisos_pendentes" if caminho.name.startswith("avisos_enviando_") else caminho.stem
    destino = caminho.with_name(
        f"{stem}_corrompida_{agora():%Y%m%d_%H%M%S}_{uuid.uuid4().hex[:8]}{caminho.suffix}"
    )
    os.replace(caminho, destino)
    logging.error("Fila WhatsApp inválida preservada em %s: %s", destino, motivo)
    return destino


def _gravar_fila(caminho: Path, fila: list) -> None:
    tmp = caminho.with_name(f"{caminho.name}.{uuid.uuid4().hex}.tmp")
    try:
        tmp.write_text(json.dumps(fila, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, caminho)
    finally:
        if tmp.exists():
            tmp.unlink()


def guardar_aviso_pendente(msg: str, tipo: str = "visita", excluir: str = "",
                           msg_sem_valores: str | None = None) -> None:
    caminho = _pendentes_path()
    import sitios
    with _trava_fila():
        try:
            fila = _ler_fila(caminho)
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as e:
            if caminho.exists():
                _quarentenar_fila(caminho, str(e))
            fila = []
        fila.append({"msg": msg, "tipo": tipo, "excluir": excluir,
                     "msg_sem_valores": msg_sem_valores, "sitio": sitios.atual(),
                     "criado": agora().isoformat(timespec="seconds")})
        _gravar_fila(caminho, fila)


def avisar_manejo(tipo: str, qtd: int, brincos: str = "", de: str = "", descricao: str = "",
                  registrado_por: str = "") -> bool:
    """Põe na fila o aviso de Morte/Perda ou Nascimento (tipo "eventos"); quem
    registrou não recebe. Nunca levanta: o registro já foi gravado, o aviso é extra."""
    if tipo not in ("Nascimento", "Morte/Perda"):
        return False
    # Quem registrou é excluído pelo LOGIN: num sítio em que ele não é dono, o nome
    # de membro não existe e ele receberia o próprio aviso.
    from flask import has_request_context, session
    excluir = (session.get("usuario") if has_request_context() else "") or registrado_por
    try:
        from config import NOMES_MEMBROS
        rotulos = ", ".join(b.split(" #")[0].strip() for b in
                            str(brincos or "").replace(";", ",").split(",") if b.strip())
        quem = NOMES_MEMBROS.get(de, de) if de else ""
        sufixo_brincos = f" — {rotulos}" if rotulos else ""
        rodape = f"\n_registrado por {NOMES_MEMBROS.get(registrado_por, registrado_por)}_" if registrado_por else ""
        if tipo == "Nascimento":
            msg = f"🍼 *Nasceu* {qtd} bezerro(s){sufixo_brincos}" + (f" · de {quem}" if quem else "") + rodape
            guardar_aviso_pendente(msg, tipo="eventos", excluir=excluir, msg_sem_valores=msg)
            return True
        corpo = (f"🚨 *Morte/Perda:* {qtd} cab.{sufixo_brincos}"
                 + (f" · perda de {quem}" if quem else " · rateada entre todos")
                 + (f"\n{descricao.strip()}" if str(descricao or "").strip() else ""))
        valor = ""
        try:
            d = carregar_todas()
            r = calcular_resumo_financeiro(d["Compras"], d["Gastos"], d["Vendas"], d["Manejo"])
            valor = f"\n💸 ~{fmt_r(r['ctcab'])}/cab. (custo médio atual)"
        except Exception as e:
            logging.error(f"Aviso de perda sem valor: {e}")
        guardar_aviso_pendente(corpo + valor + rodape, tipo="eventos", excluir=excluir,
                               msg_sem_valores=corpo + rodape)
        return True
    except Exception as e:
        logging.error(f"Erro ao guardar aviso de {tipo}: {e}")
        return False


def enviar_avisos_pendentes(agora: datetime | None = None) -> int:
    """Processa a fila atomicamente; destinatários com falha ficam para nova tentativa."""
    agora = agora or agora()
    caminho = _pendentes_path()
    meu = caminho.with_name(f"avisos_enviando_{os.getpid()}_{uuid.uuid4().hex}.json")
    with _trava_fila():
        if not caminho.exists():
            return 0
        try:
            os.replace(caminho, meu)
        except OSError as e:
            logging.warning("Não foi possível reservar a fila WhatsApp: %s", e)
            return 0
    try:
        fila = _ler_fila(meu)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as e:
        if meu.exists():
            _quarentenar_fila(meu, str(e))
        return 0

    total = 0
    retentar = []
    for item in fila:
        if not isinstance(item, dict) or not isinstance(item.get("msg"), str) or not item["msg"].strip():
            retentar.append(item)
            logging.error("Aviso WhatsApp inválido preservado na fila: %r", item)
            continue
        destinatarios = item.get("destinatarios")
        if destinatarios is not None and (
                not isinstance(destinatarios, list)
                or any(not isinstance(nome, str) for nome in destinatarios)):
            retentar.append(item)
            logging.error("Destinatários inválidos em aviso WhatsApp; item preservado.")
            continue
        ultima = item.get("ultima_tentativa")
        if ultima:
            try:
                if agora - datetime.fromisoformat(ultima) < timedelta(minutes=15):
                    retentar.append(item)
                    continue
            except (TypeError, ValueError):
                logging.warning("Data de tentativa inválida em aviso pendente; tentando envio.")
        try:
            # Item gravado antes desta versão não tem "tipo": era sempre aviso de visita.
            resultado = enviar_para_familia_resultado(
                item["msg"], tipo=item.get("tipo") or "visita",
                excluir_usuario=item.get("excluir") or "",
                msg_sem_valores=item.get("msg_sem_valores"),
                sitio=item.get("sitio"),
                destinatarios=item.get("destinatarios"))
            total += resultado["enviados"]
            if resultado["falhas"]:
                pendente = dict(item)
                pendente["destinatarios"] = resultado["falhas"]
                pendente["tentativas"] = int(pendente.get("tentativas", 0)) + 1
                pendente["ultima_tentativa"] = agora.isoformat(timespec="seconds")
                retentar.append(pendente)
            elif resultado["elegiveis"] == 0:
                logging.warning("Aviso WhatsApp sem destinatários configurados ou habilitados; descartado.")
        except Exception as e:
            logging.error(f"Erro ao enviar aviso pendente: {e}")
            retentar.append(item)

    try:
        with _trava_fila():
            novas = _ler_fila(caminho)
            pendentes = novas + retentar
            if pendentes:
                _gravar_fila(caminho, pendentes)
            elif caminho.exists():
                caminho.unlink()
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as e:
        logging.exception("Não foi possível atualizar a fila de avisos: %s", e)
        return total
    try:
        meu.unlink()
    except OSError as e:
        logging.warning("Não foi possível remover a fila reservada %s: %s", meu, e)
    return total


# ── Execução principal (Task diária) ────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    """
    Task diária. Segunda-feira: resumo semanal completo. Outros dias: só os
    alertas URGENTES ainda não enviados nos últimos dias — sem urgência, não
    manda nada.
      --teste    mostra a mensagem que seria enviada, sem enviar
      --semanal  força o resumo semanal (ex.: para conferir o formato)
    """
    import sitios
    argv = sys.argv[1:] if argv is None else argv
    falhou = False
    for slug in sitios.cada_sitio():
        # Um sítio com problema (planilha quebrada) não impede os outros de receber.
        try:
            _main_sitio(argv, slug)
        except Exception as e:
            logging.error(f"[{slug}] Erro na Task do WhatsApp: {e}")
            falhou = True
    return 1 if falhou else 0


def _main_sitio(argv: list[str], slug: str) -> int:
    """A Task diária de um sítio (o ativo)."""
    teste, semanal = "--teste" in argv, "--semanal" in argv
    if not teste:
        n = enviar_avisos_pendentes()   # aviso de visita que ficou para trás
        if n:
            logging.info(f"{n} aviso(s) de visita pendente(s) enviado(s)")
    hoje = _agora_br()
    itens = montar_itens(hoje)
    estado = _ler_estado()

    if semanal or hoje.weekday() == DIA_RESUMO_SEMANAL:
        tipo, enviar_itens = "semanal", itens
        # Lê o .xlsx de novo só no caminho semanal; se falhar, o resumo sai sem a seção.
        try:
            semana = resumo_semana(carregar_todas(), hoje)
        except Exception as e:
            logging.error(f"Falha no resumo da semana: {e}")
            semana = None
        msg = montar_msg_semanal(itens, hoje, semana=semana)
        msg_sv = montar_msg_semanal(itens, hoje, com_valores=False, semana=semana)
    else:
        enviar_itens = urgentes_a_enviar(itens, hoje, estado)
        if not enviar_itens:
            logging.info("Nenhum alerta urgente novo hoje — sem envio.")
            if teste:
                print("(nenhum alerta urgente novo hoje — nada seria enviado)")
            return 0
        tipo = "urgentes"
        msg, msg_sv = (montar_msg_urgente(enviar_itens, hoje), montar_msg_urgente(enviar_itens, hoje, com_valores=False))

    if teste:
        print(msg)
        print("\n--- sem valores ---")
        print(msg_sv)
        return 0

    enviados = enviar_para_familia(msg, tipo=tipo, msg_sem_valores=msg_sv, sitio=slug)
    logging.info(f"[{slug}] Concluído: {enviados} mensagem(s) enviada(s)")
    if enviados:
        _gravar_estado(_marcar_enviados(enviar_itens, hoje, estado))
    return 0


if __name__ == "__main__":
    sys.exit(main())
