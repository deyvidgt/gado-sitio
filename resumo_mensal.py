#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
resumo_mensal.py — Sítio Santo Antonio
======================================
No dia 1º de cada mês, manda pelo WhatsApp (CallMeBot) para a família um
resumo do mês que acabou: compras, vendas, gastos, nascimentos e mortes,
o rebanho no fim do mês e o resultado acumulado de cada dono.

Usa os mesmos contatos/chaves do WhatsApp configurados no site
(Configurações → WhatsApp) e só envia para quem está com alertas ativos.

Configure no PythonAnywhere em:
  Dashboard → Tasks → Add a new scheduled task
  Comando: python3 /home/deyvidgt16/gado/resumo_mensal.py
  Horário: Daily às 08:00
  (A Task roda todo dia, mas o script só envia no dia 1º.)

Opções:
  python3 resumo_mensal.py --teste    só mostra a mensagem na tela, não envia
  python3 resumo_mensal.py --forcar   envia hoje mesmo, sem esperar o dia 1º
"""

import sys
import logging
from datetime import datetime
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))

from calculos import (  # noqa: E402
    _ate, calcular_estoque, calcular_resumo_financeiro, calcular_todos_membros,
)
from config import MEMBROS, NOMES_MEMBROS, EMOJIS_MEMBROS  # noqa: E402

MESES = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho",
         "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]


def fmt_r(v) -> str:
    try:
        return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "—"


def mes_anterior(hoje: datetime) -> tuple[int, int]:
    return (hoje.year - 1, 12) if hoje.month == 1 else (hoje.year, hoje.month - 1)


def _do_mes(df: pd.DataFrame, ano: int, mes: int) -> pd.DataFrame:
    if df is None or df.empty or "Data" not in df.columns:
        return pd.DataFrame()
    d = df["Data"]
    return df[d.notna() & (d.dt.year == ano) & (d.dt.month == mes)]


def _soma(df: pd.DataFrame, col: str) -> float:
    if df.empty or col not in df.columns:
        return 0.0
    return float(pd.to_numeric(df[col], errors="coerce").fillna(0).sum())


def montar_resumo_mensal(dados: dict, ano: int, mes: int, com_valores: bool = True) -> str:
    """Monta o texto do resumo de um mês. Não envia nada (fácil de testar).
    com_valores=False: só cabeças e contagens, para quem desmarcou "valores"."""
    comp = _do_mes(dados["Compras"], ano, mes)
    gast = _do_mes(dados["Gastos"], ano, mes)
    vend = _do_mes(dados["Vendas"], ano, mes)
    man = _do_mes(dados["Manejo"], ano, mes)
    vis = _do_mes(dados.get("Visitas", pd.DataFrame()), ano, mes)

    nasc = mortes = 0
    if not man.empty and "Tipo" in man.columns:
        nasc = int(_soma(man[man["Tipo"] == "Nascimento"], "Qtd Cabeças"))
        mortes = int(_soma(man[man["Tipo"] == "Morte/Perda"], "Qtd Cabeças"))

    import sitios
    linhas = [
        f"🐄 *{sitios.nome(sitios.atual())}*",
        f"📊 *Resumo de {MESES[mes - 1]}/{ano}*",
        "",
        "*No mês*",
    ]
    teve_algo = False
    if not comp.empty:
        teve_algo = True
        linhas.append(f"🛒 Compras: {int(_soma(comp, 'Qtd Cabeças'))} cab"
                      + (f" — {fmt_r(_soma(comp, 'Valor Total (R$)'))}" if com_valores else ""))
    if not vend.empty:
        teve_algo = True
        linhas.append(f"💰 Vendas: {int(_soma(vend, 'Qtd Cabeças'))} cab"
                      + (f" — {fmt_r(_soma(vend, 'Valor Total (R$)'))}" if com_valores else ""))
    if not gast.empty and not com_valores:
        teve_algo = True
        linhas.append(f"🧾 Gastos: {len(gast)} lançamentos")
    elif not gast.empty:
        teve_algo = True
        linha = f"🧾 Gastos: {fmt_r(_soma(gast, 'Valor Total (R$)'))}"
        if "Tipo" in gast.columns and gast["Tipo"].notna().any():
            por_tipo = (gast.assign(_v=pd.to_numeric(gast["Valor Total (R$)"], errors="coerce"))
                        .groupby("Tipo")["_v"].sum().sort_values(ascending=False))
            if len(por_tipo):
                linha += f" (maior: {por_tipo.index[0]}, {fmt_r(por_tipo.iloc[0])})"
        linhas.append(linha)
    if nasc or mortes:
        teve_algo = True
        linhas.append(f"🍼 Nascimentos: {nasc}   ⚰️ Mortes/perdas: {mortes}")
    if not vis.empty:
        teve_algo = True
        linhas.append(f"🏡 Visitas ao sítio: {len(vis)}")
    if not teve_algo:
        linhas.append("Nenhuma movimentação registrada no mês.")

    # Situação no FIM do mês (mesmo motor de média móvel do painel)
    corte = pd.Period(year=ano, month=mes, freq="M").to_timestamp(how="end")
    c_, g_, v_, m_ = (_ate(dados[a], corte) for a in ("Compras", "Gastos", "Vendas", "Manejo"))
    resumo = calcular_resumo_financeiro(c_, g_, v_, m_)
    estoque = calcular_estoque(c_, v_, m_)

    linhas += [
        "",
        "*Rebanho no fim do mês*",
        f"🐄 {estoque} cabeças",
    ]
    if estoque > 0 and com_valores:
        linhas.append(f"💵 Custo médio: {fmt_r(resumo['ctcab'])}/cab")
        linhas.append(f"📦 Capital no rebanho: {fmt_r(resumo['capital_imobilizado'])}")

    membros = calcular_todos_membros(v_, c_, g_, m_)
    if com_valores and any(membros[m]["cabecas"] or membros[m]["perdas"] for m in MEMBROS):
        linhas += ["", "*Resultado acumulado por dono*"]
        for m in MEMBROS:
            r = membros[m]
            linhas.append(f"{EMOJIS_MEMBROS.get(m, '•')} {NOMES_MEMBROS.get(m, m)}: "
                          f"{fmt_r(r['resultado_liquido'])} ({r['cabecas']} cab vendidas)")

    linhas += ["", "_Sistema de Gestão de Gado_"]
    return "\n".join(linhas)


def main(argv: list[str]) -> int:
    teste = "--teste" in argv
    forcar = "--forcar" in argv
    hoje = datetime.now()

    if hoje.day != 1 and not (teste or forcar):
        return 0  # Task diária: só age no dia 1º

    import sitios
    from db import carregar_todas
    # Importa aqui: o módulo configura o log do WhatsApp ao ser carregado.
    import alertas_whatsapp
    ano, mes = mes_anterior(hoje)
    total, falhou = 0, False
    for slug in sitios.cada_sitio():
        # Um sítio com problema não impede o resumo dos outros.
        try:
            dados = carregar_todas()
            msg = montar_resumo_mensal(dados, ano, mes)
            msg_sv = montar_resumo_mensal(dados, ano, mes, com_valores=False)
            if teste:
                print(msg)
                print("\n── versão sem valores ──\n")
                print(msg_sv)
                continue
            enviados = alertas_whatsapp.enviar_para_familia(
                msg, tipo="mensal", msg_sem_valores=msg_sv, sitio=slug)
            total += enviados
            logging.info(f"[{slug}] Resumo mensal {mes:02d}/{ano}: {enviados} mensagem(ns) enviada(s)")
            print(f"[{slug}] Resumo de {mes:02d}/{ano} enviado para {enviados} pessoa(s).")
        except Exception as e:
            logging.error(f"[{slug}] Erro no resumo mensal: {e}")
            falhou = True
    if teste:
        return 0
    return 0 if total > 0 and not falhou else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
