#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bcs.py — Body Condition Score (Escore de Condição Corporal) vs Peso

Score visual 1-5 (magra/normal/gorda) correlacionado com peso estimado.
Útil para diagnosticar problemas nutricionais ou reprodutivos.

BCS 1 = magra (subnutrida)
BCS 2 = magra-normal
BCS 3 = normal
BCS 4 = gorda
BCS 5 = muito gorda (risco reprodutivo)
"""
from __future__ import annotations

import pandas as pd
import peso_foto as PF
import animais as A


def bcs_historico(id_: str, df_man: pd.DataFrame, limite_dias: int = 180) -> list[dict]:
    """Retorna histórico de BCS visual + peso estimado do animal (últimos N dias).

    Útil para gráfico de evolução: correlaciona escore visual (1-5) com peso.
    Dados vêm do campo "Descrição" do Manejo onde o usuário marca o BCS.

    Formato esperado na Descrição: "BCS: 3" ou "Score: 2, BCS 4" etc.
    """
    estimativas = PF.historico_estimativas(id_, df_man, limite_dias)
    if not estimativas:
        return []

    # Procura registros com BCS na mesma data ou próximo
    manejo_animal = df_man[df_man["Brincos"].str.contains(id_, na=False, regex=False)]

    resultado = []
    for est in estimativas:
        data_est = est["data"]
        peso_cal = est["calibrado"]

        # Procura BCS na mesma data ou até 3 dias depois
        bcs_regs = manejo_animal[
            (manejo_animal["Data"] >= data_est) &
            (manejo_animal["Data"] <= data_est + pd.Timedelta(days=3)) &
            (manejo_animal["Descrição"].str.contains("BCS|Score", case=False, na=False))
        ]

        bcs = None
        desc = ""
        if not bcs_regs.empty:
            desc = bcs_regs.iloc[0]["Descrição"]
            # Extrai número após "BCS:" ou "Score:"
            import re
            match = re.search(r"(?:BCS|Score)[:\s]+(\d+)", desc, re.IGNORECASE)
            if match:
                bcs = int(match.group(1))

        resultado.append({
            "data": data_est,
            "peso_kg": peso_cal,
            "bcs": bcs,
            "observacao": desc
        })

    return resultado


def analise_tendencia(historico: list[dict]) -> dict:
    """Analisa tendência de peso vs BCS: {ganho_kg, dias, tendencia, avisos}"""
    if len(historico) < 2:
        return {"ganho_kg": 0, "dias": 0, "tendencia": "insuficiente", "avisos": []}

    primeiro = historico[0]
    ultimo = historico[-1]

    ganho = round(ultimo["peso_kg"] - primeiro["peso_kg"], 1)
    dias = (ultimo["data"] - primeiro["data"]).days

    avisos = []
    tendencia = "normal"

    # BCS baixo com peso estável = subnutrição
    if ultimo["bcs"] and ultimo["bcs"] <= 2 and abs(ganho) < 5:
        avisos.append("BCS baixo (magra) + peso estável — revisar alimentação")
        tendencia = "alerta"

    # BCS altos com ganho excessivo = risco reprodutivo
    if ultimo["bcs"] and ultimo["bcs"] >= 4 and ganho > 20:
        avisos.append("BCS alta (gorda) + ganho excessivo — risco reprodutivo")
        tendencia = "alerta"

    # Peso caindo com BCS em queda = problema sério
    if ganho < -10:
        avisos.append("Peso caindo rapidamente — possível doença ou desnutrição")
        tendencia = "critico"

    ganho_mes = round(ganho / (dias / 30), 1) if dias > 0 else 0

    return {
        "ganho_kg": ganho,
        "ganho_mes_kg": ganho_mes,
        "dias": dias,
        "tendencia": tendencia,
        "avisos": avisos
    }
