# -*- coding: utf-8 -*-
"""Eventos operacionais reunidos das fontes existentes, sem gravar dados."""
from __future__ import annotations

import pandas as pd


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


def _adicionar(out, data, tipo, titulo, origem, detalhes="", status="proximo", url=None):
    d = _data(data)
    if pd.isna(d):
        return
    item = {"data": d, "tipo": tipo, "titulo": titulo or tipo,
            "status": status, "origem": origem, "detalhes": detalhes or ""}
    if url:
        item["url"] = url
    out.append(item)


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
            e["status"] = "atrasado"
    return sorted(out, key=lambda e: (e["data"], e["titulo"]))
