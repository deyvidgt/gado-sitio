# -*- coding: utf-8 -*-
"""Eventos operacionais reunidos das fontes existentes, sem gravar dados."""
from __future__ import annotations

from datetime import date, timedelta
import pandas as pd

import reproducao
import tarefas as t_mod
import leite
import saude


def _data(valor):
    d = pd.to_datetime(valor, dayfirst=True, errors="coerce")
    return pd.NaT if pd.isna(d) else d.normalize()


def _texto(valor):
    return "" if valor is None or pd.isna(valor) else str(valor).strip()


def _tipo_manejo(tipo):
    t = _texto(tipo).lower()
    if "vacina" in t or "vermif" in t or "brucelose" in t:
        return "saude"
    if t in {"cobertura", "diagnóstico de gestação"}:
        return "reproducao"
    return "manejo"


def _urgencia(dias):
    """Retorna 'urgente' (≤3), 'aviso' (≤7), 'normal'."""
    if dias is None:
        return "normal"
    if dias <= 3:
        return "urgente"
    if dias <= 7:
        return "aviso"
    return "normal"


def _adicionar(out, data, tipo, titulo, origem, detalhes="", urgencia="normal", url=None):
    d = _data(data)
    if pd.isna(d):
        return
    item = {"data": d, "tipo": tipo, "titulo": titulo or tipo,
            "urgencia": urgencia, "origem": origem, "detalhes": detalhes or ""}
    if url:
        item["url"] = url
    out.append(item)


def eventos_mes(dados, mes, ano, hoje=None):
    """Retorna { data: [eventos] } para o mês especificado (para grid de calendário)."""
    hoje = pd.Timestamp(hoje or date.today()).normalize()

    # Intervalo: 1º dia do mês a último dia do mês
    inicio = pd.Timestamp(year=ano, month=mes, day=1)
    fim = pd.Timestamp(year=ano, month=mes, day=1) + pd.DateOffset(months=1) - timedelta(days=1)

    # Estrutura: {data: [eventos]}
    resultado = {}

    # Manejo (saúde, reprodução)
    df_man = dados.get("Manejo", pd.DataFrame()) if dados else pd.DataFrame()
    if df_man is not None and not df_man.empty:
        for _, row in df_man.iterrows():
            d = _data(row.get("Data"))
            if pd.isna(d) or not (inicio <= d <= fim):
                continue
            tipo = _tipo_manejo(row.get("Tipo"))
            titulo = _texto(row.get("Tipo")) or "Manejo"
            detalhe = _texto(row.get("Descrição")) or _texto(row.get("Produto"))
            dias = (d - hoje).days
            urg = _urgencia(dias)
            resultado.setdefault(d.date(), []).append({
                "tipo": tipo, "titulo": titulo, "detalhes": detalhe,
                "urgencia": urg, "origem": "Manejo"
            })

    # Visitas
    df_vis = dados.get("Visitas", pd.DataFrame()) if dados else pd.DataFrame()
    if df_vis is not None and not df_vis.empty:
        for _, row in df_vis.iterrows():
            d = _data(row.get("Data"))
            if pd.isna(d) or not (inicio <= d <= fim):
                continue
            dias = (d - hoje).days
            urg = _urgencia(dias)
            resultado.setdefault(d.date(), []).append({
                "tipo": "visita", "titulo": "Visita", "detalhes": _texto(row.get("Responsável")),
                "urgencia": urg, "origem": "Visitas"
            })

    # Tarefas
    df_tar = dados.get("Tarefas", pd.DataFrame()) if dados else pd.DataFrame()
    if df_tar is not None and not df_tar.empty:
        for _, row in df_tar.iterrows():
            if _texto(row.get("Feito Em")):
                continue
            d = _data(row.get("Data"))
            if pd.isna(d) or not (inicio <= d <= fim):
                continue
            dias = (d - hoje).days
            urg = _urgencia(dias)
            resultado.setdefault(d.date(), []).append({
                "tipo": "tarefa", "titulo": _texto(row.get("Título")),
                "detalhes": _texto(row.get("Responsável")),
                "urgencia": urg, "origem": "Tarefas"
            })

    # Partos (reproducao)
    df_ani = dados.get("Animais", pd.DataFrame()) if dados else pd.DataFrame()
    try:
        situ = reproducao.situacao(df_man, df_ani, hoje=hoje)
        for vaca in situ:
            d = vaca.get("parto_previsto")
            if pd.isna(d) or not (inicio <= d <= fim):
                continue
            dias = vaca.get("dias_para_parto", 0)
            urg = _urgencia(dias)
            resultado.setdefault(d.date(), []).append({
                "tipo": "parto", "titulo": f"Parto: {vaca.get('nome', 'vaca')}",
                "detalhes": f"({dias} dias)", "urgencia": urg, "origem": "Reprodução"
            })
    except Exception:
        pass

    # Colchão (leite)
    df_colchao = dados.get("Leite Colchão", pd.DataFrame()) if dados else pd.DataFrame()
    try:
        colchoes = leite.historico_colchao(df_colchao, referencia=hoje)
        for local, info in colchoes.items():
            prox = info.get("proxima_troca")
            if not prox or pd.isna(prox):
                continue
            prox = pd.Timestamp(prox).normalize()
            if not (inicio <= prox <= fim):
                continue
            dias = info.get("dias_para_troca", 0)
            urg = _urgencia(dias)
            resultado.setdefault(prox.date(), []).append({
                "tipo": "colchao", "titulo": f"Colchão: {local}",
                "detalhes": f"({dias} dias)", "urgencia": urg, "origem": "Leite"
            })
    except Exception:
        pass

    return resultado


def eventos(dados, inicio=None, fim=None, tipo=None):
    """Retorna eventos ordenados; registros sem data válida são descartados."""
    out = []
    df = dados.get("Manejo", pd.DataFrame()) if dados else pd.DataFrame()
    if df is not None and not df.empty:
        for _, row in df.iterrows():
            grupo = _tipo_manejo(row.get("Tipo"))
            titulo = _texto(row.get("Tipo")) or "Manejo"
            detalhe = _texto(row.get("Descrição")) or _texto(row.get("Produto"))
            _adicionar(out, row.get("Data"), grupo, titulo, "Manejo", detalhe)

    visitas = dados.get("Visitas", pd.DataFrame()) if dados else pd.DataFrame()
    if visitas is not None and not visitas.empty:
        for _, row in visitas.iterrows():
            detalhe = _texto(row.get("Responsável"))
            _adicionar(out, row.get("Data"), "visita", "Visita ao sítio", "Visitas", detalhe)

    tarefas = dados.get("Tarefas", pd.DataFrame()) if dados else pd.DataFrame()
    if tarefas is not None and not tarefas.empty:
        for _, row in tarefas.iterrows():
            if _texto(row.get("Feito Em")):
                continue
            _adicionar(out, row.get("Data"), "tarefa", _texto(row.get("Título")), "Tarefas",
                       _texto(row.get("Responsável")))

    ini, fim_d = _data(inicio), _data(fim)
    if pd.notna(ini):
        out = [e for e in out if e["data"] >= ini]
    if pd.notna(fim_d):
        out = [e for e in out if e["data"] <= fim_d]
    if tipo:
        out = [e for e in out if e["tipo"] == tipo]
    hoje = pd.Timestamp.now().normalize()
    for e in out:
        if e["data"] < hoje:
            e["urgencia"] = "atrasado"
    return sorted(out, key=lambda e: (e["data"], e["titulo"]))
