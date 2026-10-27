# -*- coding: utf-8 -*-
"""Comparativo de vacas leiteiras — análise lado-a-lado."""

from datetime import date, timedelta
import pandas as pd
from db import carregar_aba
from leite import _data, _numero


def comparar_vacas(ids_animais, periodo_dias=30):
    """
    Compara até 3 vacas leiteiras no período.

    Args:
        ids_animais: list de IDs (ex.: ["A0001", "A0002"])
        periodo_dias: dias para trás (padrão: 30)

    Returns:
        dict {id: {"producao_litros_dia", "custo_diario", "receita_diario", "margem_diario",
                   "ccs_ultimo", "cpp_ultimo", "ultimos_eventos"}}
    """
    hoje = date.today()
    inicio = hoje - timedelta(days=periodo_dias)

    df_producao = carregar_aba("Leite Produção")
    df_config = carregar_aba("Leite Configuração")
    df_tratamentos = carregar_aba("Leite Tratamentos")

    preco_litro = 0
    if df_config is not None and not df_config.empty:
        preco = _numero(df_config.iloc[0].get("Preço por Litro"))
        preco_litro = preco if preco else 0

    resultado = {}
    for vaca_id in ids_animais:
        vaca_id = str(vaca_id).strip()
        if df_producao is None or df_producao.empty:
            registros = pd.DataFrame()
        else:
            registros = df_producao[df_producao.get("Vaca ID", "").astype(str).str.strip() == vaca_id].copy()
            # Filtra por data com segurança contra tipos mistos
            if not registros.empty:
                datas_lista = [_data(d) for d in registros.get("Data", [])]
                mask = [d is not None and d >= inicio and d <= hoje for d in datas_lista]
                registros = registros[mask]

        if registros.empty:
            dias_com_registro = 1
            litros_total = 0.0
        else:
            datas_unicas = set(_data(d) for d in registros.get("Data", []) if _data(d) is not None)
            dias_com_registro = len(datas_unicas) or 1
            litros_total = float(registros.get("Litros", 0).sum() or 0)

        producao_dia = litros_total / dias_com_registro if dias_com_registro > 0 else 0
        custo_dia = 25.0
        receita_dia = producao_dia * preco_litro
        margem = receita_dia - custo_dia

        ccs = cpp = None
        if not registros.empty:
            ultima_linha = registros.iloc[-1]
            ccs = ultima_linha.get("CCS (células/mL)")
            cpp = ultima_linha.get("CPP (UFC/mL)")

        eventos = []
        if df_tratamentos is not None and not df_tratamentos.empty:
            trats = df_tratamentos[df_tratamentos.get("Vaca ID", "").astype(str).str.strip() == vaca_id]
            if not trats.empty:
                trats = trats.sort_values("Data", ascending=False).head(3)
                for _, t in trats.iterrows():
                    tipo = str(t.get("Tipo", "")).strip()
                    descricao = str(t.get("Descrição", "")).strip()
                    if tipo:
                        eventos.append(f"{tipo}: {descricao[:30]}" if descricao else tipo)

        resultado[vaca_id] = {
            "producao_litros_dia": round(producao_dia, 1),
            "custo_diario": round(custo_dia, 2),
            "receita_diario": round(receita_dia, 2),
            "margem_diario": round(margem, 2),
            "ccs_ultimo": ccs,
            "cpp_ultimo": cpp,
            "ultimos_eventos": eventos,
        }

    return resultado
