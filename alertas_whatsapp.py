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

O script só envia mensagem se houver ALGUM alerta ativo —
dias sem nada urgente não geram notificação.
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

# ── Configuração ──────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
LOG_FILE = BASE_DIR / "backups" / "alertas_whatsapp.log"
Path(LOG_FILE).parent.mkdir(exist_ok=True)

logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%d/%m/%Y %H:%M:%S",
)

sys.path.insert(0, str(BASE_DIR))

# ── Imports do sistema ────────────────────────────────────────────────────────
try:
    from db import carregar_aba, carregar_todas
    from calculos import calcular_estoque, calcular_resumo_financeiro
    from config import ALERTAS_SAUDE
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

    gado_cnt  = int(row.get("Gado Contado")  or 0)
    gado_esp  = int(row.get("Gado Esperado") or estoque_esperado)
    gado_falt = int(row.get("Gado Faltando") or 0)

    sal      = _v("Sal/Ração",    "OK")
    prot     = _v("Proteinado",   "OK")
    mato     = _v("Mato/Vegetação", "Limpo")
    grama    = _v("Grama/Pastagem", "Boa")
    corrego  = _v("Córrego/Água", "Normal")
    quintal  = _v("Quintal",      "OK")
    cisterna = _v("Cisterna",     "OK")
    choveu   = _v("Choveu",       "Não")
    chuva_mm = float(row.get("Chuva mm") or 0)
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
            chuva_info = f"🌧️ Chuva forte: {chuva_mm:.0f}mm"
        elif chuva_mm >= 15:
            chuva_info = f"🌦️ Boa chuva: {chuva_mm:.0f}mm"
        elif chuva_mm > 0:
            chuva_info = f"🌂 Chuva leve: {chuva_mm:.0f}mm"
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


# ── Montagem dos alertas diários ──────────────────────────────────────────────

def montar_alertas() -> list[str]:
    """
    Verifica todas as condições e retorna lista de linhas de alerta.
    Retorna lista vazia se não há nada urgente.
    """
    import pandas as pd
    hoje = datetime.now()
    alertas = []

    try:
        dados  = carregar_todas()
        df_c   = dados["Compras"]
        df_g   = dados["Gastos"]
        df_v   = dados["Vendas"]
        df_m   = dados["Manejo"]
        df_vis = dados["Visitas"]
    except Exception as e:
        logging.error(f"Erro ao carregar dados: {e}")
        return [f"❌ Erro ao ler dados do sistema: {e}"]

    # ── 1) Alertas de manejo ─────────────────────────────────────────────────
    for tipo, intervalo_dias in ALERTAS_SAUDE.items():
        if df_m.empty or "Tipo" not in df_m.columns:
            alertas.append(f"📋 {tipo}: nenhum registro encontrado!")
            continue
        df_t = df_m[df_m["Tipo"] == tipo]
        if df_t.empty:
            alertas.append(f"📋 {tipo}: nenhum registro ainda — programe a primeira!")
            continue
        ultima_ts = df_t["Data"].dropna().max()
        if pd.isna(ultima_ts):
            continue
        dias_passados  = (hoje - ultima_ts.to_pydatetime()).days
        dias_restantes = intervalo_dias - dias_passados
        if dias_passados > intervalo_dias:
            alertas.append(
                f"⚠️ {tipo} ATRASADA!\n"
                f"   Última: {ultima_ts.strftime('%d/%m/%Y')} "
                f"({dias_passados}d atrás — limite {intervalo_dias}d)"
            )
        elif dias_restantes <= 14:
            alertas.append(
                f"⏰ {tipo} em {dias_restantes} dia(s)\n"
                f"   Prevista para: {(hoje + timedelta(days=dias_restantes)).strftime('%d/%m/%Y')}"
            )

    # ── 2) Informações da última visita (detalhadas) ─────────────────────────
    if not df_vis.empty and "Data" in df_vis.columns:
        df_vis_s  = df_vis.sort_values("Data", ascending=False, na_position="last")
        ultima_vis = df_vis_s.iloc[0]

        ultima_data = df_vis_s["Data"].dropna().max()
        dias_sem_visita = (hoje - ultima_data.to_pydatetime()).days if pd.notna(ultima_data) else 999

        resp_ult   = _str_campo(ultima_vis.get("Responsável"), "?")
        data_ult   = ultima_data.strftime("%d/%m/%Y") if pd.notna(ultima_data) else "?"

        # Sempre incluir resumo da última visita no alerta diário
        gado_cnt  = int(ultima_vis.get("Gado Contado")  or 0)
        gado_esp  = int(ultima_vis.get("Gado Esperado") or 0)
        gado_falt = int(ultima_vis.get("Gado Faltando") or 0)

        sal      = _str_campo(ultima_vis.get("Sal/Ração"),    "OK")
        prot     = _str_campo(ultima_vis.get("Proteinado"),   "OK")
        grama    = _str_campo(ultima_vis.get("Grama/Pastagem"), "Boa")
        corrego  = _str_campo(ultima_vis.get("Córrego/Água"), "Normal")
        cisterna = _str_campo(ultima_vis.get("Cisterna"),     "OK")
        choveu   = _str_campo(ultima_vis.get("Choveu"),       "Não")
        chuva_mm = float(ultima_vis.get("Chuva mm") or 0)

        # Linha de resumo da visita
        vis_header = (
            f"🏡 *Última visita:* {data_ult} por {resp_ult} "
            f"({dias_sem_visita}d atrás)"
        )
        alertas.append(vis_header)

        # Gado
        if gado_falt > 0:
            alertas.append(f"  🚨 GADO FALTANDO: {gado_falt} cab! (contado {gado_cnt} / esperado {gado_esp})")
        elif gado_cnt > 0:
            alertas.append(f"  ✅ Gado: {gado_cnt}/{gado_esp} cab conferidos")

        # Sal/Ração
        if sal in ("Vazio", "Baixo", "Meio Saco"):
            icone = "🚨" if sal == "Vazio" else "⚠️"
            alertas.append(f"  {icone} Sal/Ração: {sal} — reabastecer!")

        # Proteinado
        if prot in ("Vazio", "Baixo", "Meio Saco"):
            icone = "🚨" if prot == "Vazio" else "⚠️"
            alertas.append(f"  {icone} Proteinado: {prot} — reabastecer!")

        # Córrego/Água
        if corrego in ("Seco", "Baixo"):
            icone = "🚨" if corrego == "Seco" else "💧"
            alertas.append(f"  {icone} Água/Córrego: {corrego} — verificar urgente!")

        # Pastagem
        if grama in ("Escassa", "Amarelando/Secando"):
            alertas.append(f"  🌾 Pastagem: {grama} — monitorar.")

        # Cisterna
        if cisterna in ("Vazia", "Baixo/Secando"):
            icone = "🚨" if cisterna == "Vazia" else "🪣"
            alertas.append(f"  {icone} Cisterna: {cisterna} — reabastecer!")

        # Chuva
        if choveu == "Sim" and chuva_mm > 0:
            alertas.append(f"  🌧️ Chuva registrada: {chuva_mm:.0f}mm")

        # Dias sem visita
        if dias_sem_visita >= 7:
            alertas.append(
                f"📅 Sem visita há {dias_sem_visita} dia(s) — hora de ir ao sítio!"
            )
    else:
        alertas.append("📅 Nenhuma visita registrada — registre a primeira visita ao sítio.")

    # ── 3) Resumo financeiro rápido ───────────────────────────────────────────
    try:
        if not df_c.empty:
            r = calcular_resumo_financeiro(df_c, df_g, df_v, df_m)
            resultado = r["resultado_realizado"]
            if resultado < 0:
                alertas.append(
                    f"📉 Resultado realizado negativo: {fmt_r(resultado)}\n"
                    f"   Break-even do estoque: {fmt_r(r['break_even'])}/cabeça"
                )
    except Exception:
        pass

    return alertas


def montar_mensagem_alertas(alertas: list[str]) -> str:
    hoje_str = datetime.now().strftime("%d/%m/%Y")
    linhas = [
        f"🐄 *Sítio Santo Antonio*",
        f"📅 *Relatório diário — {hoje_str}*",
        f"",
    ]
    for a in alertas:
        linhas.append(a)
    linhas += [
        f"",
        f"_Total: {len(alertas)} item(s)_",
        f"_Sistema de Gestão de Gado_",
    ]
    return "\n".join(linhas)


# Alias para compatibilidade com chamadas antigas
def montar_mensagem(alertas):
    return montar_mensagem_alertas(alertas)


# ── Enviar para toda a família ────────────────────────────────────────────────

def enviar_para_familia(msg: str, excluir_usuario: str = "") -> int:
    """
    Envia msg para todos os usuários com WhatsApp configurado.
    excluir_usuario: pular esse usuário (ex: quem acabou de registrar).
    Retorna número de envios bem-sucedidos.
    """
    usuarios = carregar_usuarios()
    enviados = 0
    for nome, info in usuarios.items():
        if excluir_usuario and nome == excluir_usuario:
            continue
        cfg      = info.get("whatsapp", {})
        telefone = cfg.get("telefone", "").strip()
        apikey   = cfg.get("apikey",   "").strip()
        ativo    = cfg.get("alertas_ativos", True)
        if not telefone or not apikey or not ativo:
            continue
        ok = enviar_whatsapp(telefone, apikey, msg)
        if ok:
            enviados += 1
    return enviados


# ── Execução principal (alertas diários) ─────────────────────────────────────

def main():
    logging.info("=" * 50)
    logging.info("Iniciando envio de alertas automáticos")

    alertas = montar_alertas()

    if not alertas:
        logging.info("Nenhum alerta ativo hoje — sem envio.")
        logging.info("=" * 50)
        return

    logging.info(f"{len(alertas)} alerta(s) encontrado(s)")
    msg      = montar_mensagem_alertas(alertas)
    enviados = enviar_para_familia(msg)

    logging.info(f"Concluído: {enviados} mensagem(s) enviada(s)")
    logging.info("=" * 50)


if __name__ == "__main__":
    main()
