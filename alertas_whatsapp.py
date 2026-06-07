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
    caminho = BASE_DIR / "usuarios.json"
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

# ── Montagem dos alertas ──────────────────────────────────────────────────────

def montar_alertas() -> list[str]:
    """
    Verifica todas as condições e retorna lista de linhas de alerta.
    Retorna lista vazia se não há nada urgente.
    """
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

    # ── 1) Alertas de manejo (vacinação, vermifugação, pesagem) ──────────────
    for tipo, intervalo_dias in ALERTAS_SAUDE.items():
        import pandas as pd
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
        dias_passados = (hoje - ultima_ts.to_pydatetime()).days
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

    # ── 2) Alertas da última visita ───────────────────────────────────────────
    import pandas as pd
    if not df_vis.empty and "Data" in df_vis.columns:
        df_vis_s = df_vis.sort_values("Data", ascending=False, na_position="last")
        ultima_vis = df_vis_s.iloc[0]

        # Gado faltando
        faltando = int(ultima_vis.get("Gado Faltando") or 0)
        if faltando > 0:
            data_vis = ultima_vis.get("Data")
            data_str = data_vis.strftime("%d/%m/%Y") if pd.notna(data_vis) else "?"
            alertas.append(
                f"🚨 GADO FALTANDO: {faltando} cabeça(s) não localizada(s)\n"
                f"   (última visita em {data_str})"
            )

        # Sal/Ração
        sal = str(ultima_vis.get("Sal/Ração") or "OK")
        if sal in ("Vazio", "Baixo", "Meio Saco"):
            icone = "🚨" if sal == "Vazio" else "⚠️"
            alertas.append(f"{icone} Sal/Ração: {sal} — reabastecer!")

        # Proteinado
        prot = str(ultima_vis.get("Proteinado") or "OK")
        if prot in ("Vazio", "Baixo", "Meio Saco"):
            icone = "🚨" if prot == "Vazio" else "⚠️"
            alertas.append(f"{icone} Proteinado: {prot} — reabastecer!")

        # Córrego/Água
        corrego = str(ultima_vis.get("Córrego/Água") or "Normal")
        if corrego in ("Seco", "Baixo"):
            icone = "🚨" if corrego == "Seco" else "💧"
            alertas.append(f"{icone} Água/Córrego: {corrego} — verificar urgente!")

        # Grama/Pastagem
        grama = str(ultima_vis.get("Grama/Pastagem") or "Boa")
        if grama in ("Escassa", "Amarelando/Secando"):
            alertas.append(f"🌾 Pastagem: {grama} — considerar rotação de pasto.")

        # Cisterna
        cisterna = str(ultima_vis.get("Cisterna") or "OK")
        if cisterna in ("Vazia", "Baixo/Secando"):
            icone = "🚨" if cisterna == "Vazia" else "🪣"
            alertas.append(f"{icone} Cisterna: {cisterna} — reabastecer!")

        # Dias sem visita
        ultima_data = df_vis_s["Data"].dropna().max()
        if pd.notna(ultima_data):
            dias_sem_visita = (hoje - ultima_data.to_pydatetime()).days
            if dias_sem_visita >= 7:
                alertas.append(
                    f"📅 Sem visita há {dias_sem_visita} dia(s)\n"
                    f"   Última: {ultima_data.strftime('%d/%m/%Y')} — hora de visitar o sítio!"
                )
    else:
        alertas.append("📅 Nenhuma visita registrada — registre a primeira visita ao sítio.")

    # ── 3) Resumo financeiro rápido (só se houver dados) ─────────────────────
    try:
        if not df_c.empty:
            r = calcular_resumo_financeiro(df_c, df_g, df_v, df_m)
            estoque = r["estoque"]
            resultado = r["resultado_realizado"]

            if resultado < 0:
                alertas.append(
                    f"📉 Resultado realizado negativo: {fmt_r(resultado)}\n"
                    f"   Break-even do estoque: {fmt_r(r['break_even'])}/cabeça"
                )
            else:
                # Info positiva — só incluir se não há outros alertas críticos
                pass  # não encher a mensagem com info quando há urgências
    except Exception:
        pass

    return alertas


def montar_mensagem(alertas: list[str]) -> str:
    hoje_str = datetime.now().strftime("%d/%m/%Y")
    linhas = [
        f"🐄 *Sítio Santo Antonio*",
        f"📅 Alertas do dia {hoje_str}",
        "",
    ]
    for a in alertas:
        linhas.append(a)

    linhas += [
        "",
        f"_Total: {len(alertas)} alerta(s)_",
        "_Sistema de Gestão de Gado_",
    ]
    return "\n".join(linhas)


# ── Execução principal ────────────────────────────────────────────────────────

def main():
    logging.info("=" * 50)
    logging.info("Iniciando envio de alertas automáticos")

    alertas = montar_alertas()

    if not alertas:
        logging.info("Nenhum alerta ativo hoje — sem envio.")
        logging.info("=" * 50)
        return

    logging.info(f"{len(alertas)} alerta(s) encontrado(s)")
    msg = montar_mensagem(alertas)

    # Enviar para todos os usuários com WhatsApp configurado
    usuarios = carregar_usuarios()
    enviados = 0
    for nome, info in usuarios.items():
        cfg = info.get("whatsapp", {})
        telefone = cfg.get("telefone", "").strip()
        apikey   = cfg.get("apikey",   "").strip()
        ativo    = cfg.get("alertas_ativos", True)

        if not telefone or not apikey:
            logging.info(f"  {nome}: WhatsApp não configurado — pulando")
            continue
        if not ativo:
            logging.info(f"  {nome}: alertas pausados — pulando")
            continue

        logging.info(f"  Enviando para {nome} ({telefone[:6]}***)")
        ok = enviar_whatsapp(telefone, apikey, msg)
        if ok:
            enviados += 1

    logging.info(f"Concluído: {enviados}/{len(usuarios)} mensagem(s) enviada(s)")
    logging.info("=" * 50)


if __name__ == "__main__":
    main()
