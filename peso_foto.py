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
from agora import agora

import re
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
_RE_BCS = re.compile(r"\bBCS\s+([1-9])\s+\(fator\s+(\d+(?:[.,]\d+)?)\)", re.I)


def estimar_bruto(comp_cm: float, prof_cm: float) -> float:
    perimetro = FATOR_PERIMETRO * prof_cm
    return perimetro ** 2 * comp_cm / CONST_SCHAEFFER


def _estimativas(df_man: pd.DataFrame) -> dict[str, list[tuple[pd.Timestamp, float, float]]]:
    """{ID: [(data, peso-base, fator-BCS)]}; mantém compatibilidade com registros antigos."""
    out: dict[str, list[tuple[pd.Timestamp, float, float]]] = {}
    if df_man is None or df_man.empty or "Tipo" not in df_man.columns:
        return out
    for _, row in df_man.iterrows():
        if row.get("Tipo") != P.TIPO_ESTIMADO:
            continue
        data = pd.to_datetime(row.get("Data"), dayfirst=True, errors="coerce")
        if pd.isna(data):
            continue
        descricao = str(row.get("Descrição") or "")
        bcs = _RE_BCS.search(descricao)
        fator_bcs = FATOR_BCS[int(bcs.group(1))] if bcs else 1.0
        for id_, kg in P.pesos_da_linha(row).items():
            out.setdefault(id_, []).append((data.normalize(), kg, fator_bcs))
    for lista in out.values():
        lista.sort(key=lambda item: item[0])
    return out


def fator_bcs(valor) -> float:
    if valor in (None, ""):
        return 1.0
    try:
        bcs = int(valor)
    except (ValueError, TypeError):
        raise ValueError("BCS inválido. Use um número de 1 a 9.")
    if not 1 <= bcs <= 9:
        raise ValueError("BCS deve estar entre 1 e 9.")
    return FATOR_BCS[bcs]


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
        except (ValueError, TypeError):
            raise ValueError("BCS inválido. Use um número de 1 a 9.")
        fator_bcs(bcs_val)

    return tuple(valores) + (bcs_val,)


def fator_calibracao(df_man: pd.DataFrame) -> tuple[float, int]:
    """(fator, nº de pares). Par = estimativa e balança do mesmo animal a ≤15 dias.
    Mediana (um par errado não estraga), limitada a 0,7–1,3; menos de 3 pares → 1."""
    estimados = _estimativas(df_man)
    balanca = P.todas(df_man)
    razoes = []
    for id_, lista in estimados.items():
        for data_e, bruto, fator_bcs in lista:
            perto = [(abs((data_b - data_e).days), kg) for data_b, kg in balanca.get(id_, [])
                     if abs((data_b - data_e).days) <= DIAS_PAR]
            peso_ajustado = bruto * fator_bcs
            if perto and peso_ajustado > 0:
                razoes.append(min(perto)[1] / peso_ajustado)
    if len(razoes) < MIN_PARES:
        return 1.0, len(razoes)
    return min(max(statistics.median(razoes), FATOR_MIN), FATOR_MAX), len(razoes)


from image_processor import processar_foto_animal

# ... (mantendo o resto do arquivo)

def registrar(id_: str, comp_cm=None, prof_cm=None, ref_cm=None, data=None, responsavel: str = "", bcs=None, caminho_foto=None) -> float:
    """Valida, calcula e grava a linha "Peso Estimado". Devolve o peso bruto."""

    if caminho_foto:
        medidas = processar_foto_animal(caminho_foto)
        if medidas:
            comp_cm = medidas['comprimento']
            prof_cm = medidas['profundidade']
            ref_cm = ref_cm or 100 # Fallback se necessário

    comp, prof, ref, bcs_val = validar(comp_cm, prof_cm, ref_cm, bcs)
    # ... resto da função original ...
    a = A.por_id(A.carregar(), id_)
    if a is None or a["Status"] != "Vivo":
        raise ValueError("Só dá para estimar o peso de um animal vivo.")
    bruto = round(estimar_bruto(comp, prof), 1)
    data_ts = A._data(data) if data else pd.NaT
    if pd.isna(data_ts):
        data_ts = pd.Timestamp(agora()).normalize()
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
    lista = _estimativas(df_man).get(id_)
    if not lista:
        return None
    data, bruto, fator_bcs = lista[-1]
    peso_ajustado = bruto * fator_bcs
    fator, n = fator_calibracao(df_man)
    return {"kg": peso_ajustado * fator, "bruto": bruto, "peso_bcs": peso_ajustado,
            "fator_bcs": fator_bcs, "data": data, "fator": fator,
            "n_pares": n, "faixa_pct": 10 if n >= MIN_PARES else 15}


def historico_estimativas(id_: str, df_man: pd.DataFrame, limite_dias: int = 180) -> list[dict]:
    """Retorna histórico de estimativas do animal (últimos N dias) com calibração aplicada.
    Útil para gráfico de evolução de peso estimado ao longo do tempo."""
    estimados = _estimativas(df_man).get(id_, [])
    if not estimados:
        return []

    fator, _ = fator_calibracao(df_man)
    agora = pd.Timestamp(agora())

    resultado = []
    for data, bruto, fator_bcs in estimados:
        dias_atras = (agora - data).days
        if dias_atras <= limite_dias and bruto > 0:
            peso_ajustado = bruto * fator_bcs
            resultado.append({
                "data": data,
                "bruto": round(bruto, 1),
                "peso_bcs": round(peso_ajustado, 1),
                "calibrado": round(peso_ajustado * fator, 1),
                "dias_atras": dias_atras,
                "fator": fator,
                "fator_bcs": fator_bcs,
            })

    return sorted(resultado, key=lambda x: x["data"])


def comparar_estimativa_vs_balanca(id_: str, df_man: pd.DataFrame) -> dict | None:
    """Compara a última estimativa com a última pesagem do mesmo animal (se houver).
    Retorna {'estimativa_kg', 'balanca_kg', 'diferenca_pct', 'dias_diferenca'} ou None."""
    estimados = _estimativas(df_man).get(id_, [])
    balanca = P.todas(df_man).get(id_, [])

    if not estimados or not balanca:
        return None

    data_e, bruto, fator_bcs = estimados[-1]
    fator, _ = fator_calibracao(df_man)
    estimativa_calibrada = bruto * fator_bcs * fator

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
