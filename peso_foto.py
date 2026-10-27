#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
peso_foto.py — peso estimado por foto (v5.1)

Sem IA treinada: a tela mede na foto de lado (com uma referência de tamanho
conhecido no mesmo plano) o comprimento ombro→nádega e a profundidade do peito.
    perímetro do peito ≈ FATOR_PERIMETRO × profundidade  (proporção típica de zebuíno)
    peso bruto (kg)    = perímetro² × comprimento / 10838 (Schaeffer, em cm)
    peso mostrado      = bruto × fator do sítio (calibração com a balança)

Grava no Manejo como "Peso Estimado" com o peso BRUTO na coluna Pesos — a
calibração melhora com o tempo e recalcula o que se mostra. Nunca entra no GMD
(pesagem.todas ignora esse tipo). Design: docs/superpowers/specs/2026-10-25-peso-por-foto-design.md
"""
from __future__ import annotations

import statistics

import pandas as pd

import animais as A
import db
import pesagem as P

FATOR_PERIMETRO = 2.6
CONST_SCHAEFFER = 10838
LIMITES = {"comprimento": (60, 260), "profundidade": (25, 110), "referência": (20, 500)}
DIAS_PAR = 15                 # estimativa e balança com até 15 dias de diferença
MIN_PARES = 3
FATOR_MIN, FATOR_MAX = 0.7, 1.3

# v5.9 — Body Condition Score (BCS 1-9): ajusta peso por condição corporal do animal
# 1-3: magro (subestima), 4-6: ideal (sem ajuste), 7-9: gordo (sobrestima)
FATOR_BCS = {
    1: 0.82, 2: 0.88, 3: 0.94, 4: 0.97, 5: 1.0, 6: 1.03, 7: 1.06, 8: 1.12, 9: 1.18
}


def estimar_bruto(comp_cm: float, prof_cm: float) -> float:
    perimetro = FATOR_PERIMETRO * prof_cm
    return perimetro ** 2 * comp_cm / CONST_SCHAEFFER


def validar(comp_cm, prof_cm, ref_cm, bcs=None) -> tuple[float, float, float, int | None]:
    """Medidas do formulário (aceita vírgula) → floats + BCS; ValueError com a mensagem."""
    valores = []
    for nome, v in (("comprimento", comp_cm), ("profundidade", prof_cm), ("referência", ref_cm)):
        try:
            x = float(str(v).replace(",", "."))
        except ValueError:
            raise ValueError(f"Medida de {nome} inválida.")
        lo, hi = LIMITES[nome]
        if not lo <= x <= hi:
            raise ValueError(f"{nome.capitalize()} de {x:g} cm não parece certo (de {lo} a {hi} cm). "
                             "Confira os toques na foto.")
        valores.append(x)
    if valores[1] > valores[0]:
        raise ValueError("O peito saiu mais fundo que o corpo é comprido — confira os toques na foto.")

    # Valida BCS (Body Condition Score 1-9)
    bcs_val = None
    if bcs is not None:
        try:
            bcs_val = int(bcs)
            if not 1 <= bcs_val <= 9:
                raise ValueError("BCS deve estar entre 1 e 9.")
        except (ValueError, TypeError):
            raise ValueError("BCS inválido. Use um número de 1 a 9.")

    return tuple(valores) + (bcs_val,)


def fator_calibracao(df_man: pd.DataFrame) -> tuple[float, int]:
    """(fator, nº de pares). Par = estimativa e balança do mesmo animal a ≤15 dias.
    Mediana (um par errado não estraga), limitada a 0,7–1,3; menos de 3 pares → 1."""
    estimados = P.todas(df_man, estimados=True)
    balanca = P.todas(df_man)
    razoes = []
    for id_, lista in estimados.items():
        for data_e, bruto in lista:
            perto = [(abs((data_b - data_e).days), kg) for data_b, kg in balanca.get(id_, [])
                     if abs((data_b - data_e).days) <= DIAS_PAR]
            if perto and bruto > 0:
                razoes.append(min(perto)[1] / bruto)
    if len(razoes) < MIN_PARES:
        return 1.0, len(razoes)
    return min(max(statistics.median(razoes), FATOR_MIN), FATOR_MAX), len(razoes)


def registrar(id_: str, comp_cm, prof_cm, ref_cm, data=None, responsavel: str = "", bcs=None) -> float:
    """Valida, calcula e grava a linha "Peso Estimado". Devolve o peso bruto."""
    comp, prof, ref, bcs_val = validar(comp_cm, prof_cm, ref_cm, bcs)
    a = A.por_id(A.carregar(), id_)
    if a is None or a["Status"] != "Vivo":
        raise ValueError("Só dá para estimar o peso de um animal vivo.")
    bruto = round(estimar_bruto(comp, prof), 1)
    data_ts = A._data(data) if data else pd.NaT
    if pd.isna(data_ts):
        data_ts = pd.Timestamp.now().normalize()
    desc = f"Foto: comprimento {comp:g} cm, peito {prof:g} cm, ref. {ref:g} cm"
    if bcs_val is not None:
        fator_bcs = FATOR_BCS[bcs_val]
        desc += f" · BCS {bcs_val} (fator {fator_bcs})"
    db.salvar_linha("Manejo", A._linha_manejo(
        data_ts, P.TIPO_ESTIMADO, 1, desc, responsavel,
        brincos=A.ref(a), pesos=P.fmt_pesos([(A.ref(a), bruto)])))
    return bruto


def ultima_estimativa(id_: str, df_man: pd.DataFrame) -> dict | None:
    """Última estimativa do animal, já com o fator do sítio aplicado."""
    lista = P.todas(df_man, estimados=True).get(id_)
    if not lista:
        return None
    data, bruto = lista[-1]
    fator, n = fator_calibracao(df_man)
    return {"kg": bruto * fator, "bruto": bruto, "data": data, "fator": fator,
            "n_pares": n, "faixa_pct": 10 if n >= MIN_PARES else 15}


def historico_estimativas(id_: str, df_man: pd.DataFrame, limite_dias: int = 180) -> list[dict]:
    """Retorna histórico de estimativas do animal (últimos N dias) com calibração aplicada.
    Útil para gráfico de evolução de peso estimado ao longo do tempo."""
    estimados = P.todas(df_man, estimados=True).get(id_, [])
    if not estimados:
        return []

    fator, _ = fator_calibracao(df_man)
    agora = pd.Timestamp.now()

    resultado = []
    for data, bruto in estimados:
        dias_atras = (agora - data).days
        if dias_atras <= limite_dias and bruto > 0:
            resultado.append({
                "data": data,
                "bruto": round(bruto, 1),
                "calibrado": round(bruto * fator, 1),
                "dias_atras": dias_atras,
                "fator": fator
            })

    return sorted(resultado, key=lambda x: x["data"])


def comparar_estimativa_vs_balanca(id_: str, df_man: pd.DataFrame) -> dict | None:
    """Compara a última estimativa com a última pesagem do mesmo animal (se houver).
    Retorna {'estimativa_kg', 'balanca_kg', 'diferenca_pct', 'dias_diferenca'} ou None."""
    estimados = P.todas(df_man, estimados=True).get(id_, [])
    balanca = P.todas(df_man).get(id_, [])

    if not estimados or not balanca:
        return None

    data_e, bruto = estimados[-1]
    fator, _ = fator_calibracao(df_man)
    estimativa_calibrada = bruto * fator

    # Procura a pesagem mais próxima da estimativa (até 30 dias)
    pares = [(abs((data_b - data_e).days), data_b, kg)
             for data_b, kg in balanca
             if abs((data_b - data_e).days) <= 30]

    if not pares:
        return None

    dias_dif, data_b, kg_balanca = min(pares)
    dif_pct = round((estimativa_calibrada - kg_balanca) / kg_balanca * 100, 1)

    return {
        "estimativa_kg": round(estimativa_calibrada, 1),
        "balanca_kg": round(kg_balanca, 1),
        "diferenca_pct": dif_pct,
        "dias_diferenca": dias_dif,
        "data_estimativa": data_e,
        "data_balanca": data_b,
        "precisa_calibracao": abs(dif_pct) > 10  # aviso se erro > 10%
    }
