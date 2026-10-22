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

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

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

def fmt_r(v):
    try:
        return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "—"


def carregar_usuarios() -> dict:
    """
    Carrega usuarios.json do DATA_DIR (~/gado-dados/), que é onde o sistema
    salva as configurações de WhatsApp. Fallback para BASE_DIR em dev local.
    """
    from db import DATA_DIR
    candidatos = [
        Path(DATA_DIR) / "usuarios.json",   # produção: ~/gado-dados/
        BASE_DIR / "usuarios.json",         # desenvolvimento local
    ]
    for caminho in candidatos:
        if caminho.exists():
            try:
                return json.loads(caminho.read_text(encoding="utf-8"))
            except Exception:
                pass
    return {}


def enviar_whatsapp(telefone: str, apikey: str, msg: str) -> bool:
    """Envia mensagem via CallMeBot. Retorna True se enviou com sucesso."""
    try:
        import requests
        url = "https://api.callmebot.com/whatsapp.php"
        resp = requests.get(
            url,
            params={"phone": telefone, "text": msg, "apikey": apikey},
            timeout=20,
        )
        ok = resp.status_code == 200 and "message queued" in resp.text.lower()
        if ok:
            logging.info(f"WhatsApp enviado para {telefone[:6]}*** OK")
        else:
            logging.warning(f"WhatsApp para {telefone[:6]}*** falhou: {resp.text[:200]}")
        return ok
    except Exception as e:
        logging.error(f"Erro ao enviar WhatsApp para {telefone[:6]}***: {e}")
        return False


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
        data_str = datetime.now().strftime("%d/%m/%Y")

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
        f"🐄 *Sítio Santo Antonio*",
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
        f"_Sistema de Gestão de Gado — Sítio SA_",
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


def _agora_br() -> datetime:
    """Hora de Brasília (o servidor do PythonAnywhere roda em UTC)."""
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("America/Sao_Paulo")).replace(tzinfo=None)
    except Exception:
        return datetime.now()


def montar_itens(hoje: datetime | None = None) -> list[dict]:
    import pandas as pd
    hoje = hoje or _agora_br()
    itens = []

    def item(chave, texto, urgente=False, repetir=REPETIR_URGENTE_DIAS):
        itens.append({"chave": chave, "texto": texto, "urgente": urgente, "repetir": repetir})

    try:
        dados  = carregar_todas()
        df_c, df_g, df_v = dados["Compras"], dados["Gastos"], dados["Vendas"]
        df_m, df_vis     = dados["Manejo"], dados["Visitas"]
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
            item(f"saude:{tipo}:sem", f"📋 {tipo}: nenhum registro ainda.")
            continue
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
                 f"break-even {fmt_r(r['break_even'])}/cab.")
            if r["resultado_realizado"] < 0:
                item("fin:negativo", f"📉 Resultado realizado: {fmt_r(r['resultado_realizado'])}")
    except Exception as e:
        logging.error(f"Erro no resumo financeiro: {e}")

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

def montar_msg_urgente(itens: list[dict], hoje: datetime | None = None) -> str:
    hoje = hoje or _agora_br()
    linhas = ["🐄 *Sítio Santo Antonio*", f"🚨 *Alertas — {hoje:%d/%m/%Y}*", ""]
    linhas += [it["texto"] for it in itens]
    linhas += ["", "_Resumo completo toda segunda-feira._"]
    return "\n".join(linhas)


def montar_msg_semanal(itens: list[dict], hoje: datetime | None = None) -> str:
    hoje = hoje or _agora_br()
    urg = [it["texto"] for it in itens if it["urgente"]]
    resto = [it["texto"] for it in itens if not it["urgente"]]
    linhas = ["🐄 *Sítio Santo Antonio*", f"📅 *Resumo semanal — {hoje:%d/%m/%Y}*", ""]
    if urg:
        linhas += ["*⚠️ Atenção*"] + urg + [""]
    linhas += resto or ["✅ Nada pendente."]
    linhas += ["", "_Sistema de Gestão de Gado_"]
    return "\n".join(linhas)


# Compatibilidade: botão "enviar alertas agora" e chamadas antigas.
def montar_alertas() -> list[str]:
    return [it["texto"] for it in montar_itens()]


def montar_mensagem_alertas(alertas: list[str]) -> str:
    hoje_str = _agora_br().strftime("%d/%m/%Y")
    linhas = ["🐄 *Sítio Santo Antonio*", f"📅 *Relatório — {hoje_str}*", ""]
    linhas += list(alertas)
    linhas += ["", "_Sistema de Gestão de Gado_"]
    return "\n".join(linhas)


def montar_mensagem(alertas):
    return montar_mensagem_alertas(alertas)


# ── Enviar para toda a família ────────────────────────────────────────────────

TIPOS_RECEBER = ("urgentes", "semanal", "visita", "eventos", "mensal", "valores")

# Login (minúsculo, chave do usuarios.json) -> membro de config.MEMBROS. Mesmo mapa de
# routes_animais._membro_logado: quem registra loga como "geane" mas o aviso traz "Mae".
_LOGIN_MEMBRO = {"geane": "Mae", "mae": "Mae", "deyvid": "Deyvid", "nilson": "Nilson"}


def _chave_pessoa(nome: str) -> str:
    n = (nome or "").strip().lower()
    return _LOGIN_MEMBRO.get(n, n).lower()


def receber_de(cfg_whatsapp: dict) -> dict:
    """As 6 preferências de recebimento; o que não foi definido vale True, para quem
    nunca mexeu continuar recebendo tudo."""
    guardado = (cfg_whatsapp or {}).get("receber") or {}
    return {t: bool(guardado.get(t, True)) for t in TIPOS_RECEBER}


def quer_receber(cfg_whatsapp: dict, tipo: str | None) -> bool:
    """alertas_ativos=False desliga tudo; com tipo=None só ele é considerado."""
    if not (cfg_whatsapp or {}).get("alertas_ativos", True):
        return False
    if tipo is None:
        return True
    return receber_de(cfg_whatsapp).get(tipo, True)


def enviar_para_familia(msg: str, excluir_usuario: str = "", tipo: str | None = None,
                        msg_sem_valores: str | None = None) -> int:
    """
    Envia msg para todos os usuários com WhatsApp configurado.
    excluir_usuario: pular essa pessoa (membro ou login; ex: quem acabou de registrar).
    tipo: categoria do aviso, filtrada pelas preferências de cada um (None = sem filtro).
    msg_sem_valores: texto alternativo para quem desligou "valores".
    Retorna número de envios bem-sucedidos.
    """
    usuarios = carregar_usuarios()
    excluir = _chave_pessoa(excluir_usuario) if excluir_usuario else ""
    enviados = 0
    for nome, info in usuarios.items():
        if excluir and _chave_pessoa(nome) == excluir:
            continue
        cfg      = info.get("whatsapp", {})
        telefone = cfg.get("telefone", "").strip()
        apikey   = cfg.get("apikey",   "").strip()
        if not telefone or not apikey or not quer_receber(cfg, tipo):
            continue
        texto = msg
        if tipo is not None and msg_sem_valores is not None and not receber_de(cfg)["valores"]:
            texto = msg_sem_valores
        if enviar_whatsapp(telefone, apikey, texto):
            enviados += 1
    return enviados


# ── Avisos de visita pendentes ───────────────────────────────────────────────
# O aviso de visita nova é guardado num arquivo ANTES de responder ao celular e
# enviado logo depois. Se a conexão cair no meio (aba fechada, sinal ruim), o
# aviso continua no arquivo e sai na próxima requisição de visita ou na Task
# diária — não se perde mais.

def _pendentes_path() -> Path:
    from db import DATA_DIR
    return Path(DATA_DIR) / "avisos_pendentes.json"


def guardar_aviso_pendente(msg: str, tipo: str = "visita", excluir: str = "",
                           msg_sem_valores: str | None = None) -> None:
    caminho = _pendentes_path()
    try:
        fila = json.loads(caminho.read_text(encoding="utf-8")) if caminho.exists() else []
    except Exception:
        fila = []
    fila.append({"msg": msg, "tipo": tipo, "excluir": excluir,
                 "msg_sem_valores": msg_sem_valores,
                 "criado": datetime.now().isoformat(timespec="seconds")})
    tmp = caminho.with_suffix(".tmp")
    tmp.write_text(json.dumps(fila, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, caminho)


def enviar_avisos_pendentes() -> int:
    """Envia e esvazia a fila. Quem consegue renomear o arquivo primeiro é o único
    que envia (os.replace é atômico) — dois processos nunca mandam o mesmo aviso."""
    caminho = _pendentes_path()
    if not caminho.exists():
        return 0
    meu = caminho.with_name(f"avisos_enviando_{os.getpid()}_{id(caminho)}.json")
    try:
        os.replace(caminho, meu)
    except OSError:
        return 0
    try:
        fila = json.loads(meu.read_text(encoding="utf-8")) or []
    except Exception:
        fila = []
    total = 0
    for item in fila:
        try:
            # Item gravado antes desta versão não tem "tipo": era sempre aviso de visita.
            total += enviar_para_familia(
                item["msg"], tipo=item.get("tipo") or "visita",
                excluir_usuario=item.get("excluir") or "",
                msg_sem_valores=item.get("msg_sem_valores"))
        except Exception as e:
            logging.error(f"Erro ao enviar aviso pendente: {e}")
    try:
        meu.unlink()
    except OSError:
        pass
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
    argv = sys.argv[1:] if argv is None else argv
    teste, semanal = "--teste" in argv, "--semanal" in argv
    if not teste:
        n = enviar_avisos_pendentes()   # aviso de visita que ficou para trás
        if n:
            logging.info(f"{n} aviso(s) de visita pendente(s) enviado(s)")
    hoje = _agora_br()
    itens = montar_itens(hoje)
    estado = _ler_estado()

    if semanal or hoje.weekday() == DIA_RESUMO_SEMANAL:
        msg, enviar_itens = montar_msg_semanal(itens, hoje), itens
    else:
        enviar_itens = urgentes_a_enviar(itens, hoje, estado)
        if not enviar_itens:
            logging.info("Nenhum alerta urgente novo hoje — sem envio.")
            if teste:
                print("(nenhum alerta urgente novo hoje — nada seria enviado)")
            return 0
        msg = montar_msg_urgente(enviar_itens, hoje)

    if teste:
        print(msg)
        return 0

    enviados = enviar_para_familia(msg)
    logging.info(f"Concluído: {enviados} mensagem(s) enviada(s)")
    if enviados:
        _gravar_estado(_marcar_enviados(enviar_itens, hoje, estado))
    return 0


if __name__ == "__main__":
    sys.exit(main())
