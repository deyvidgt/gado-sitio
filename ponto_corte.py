#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ponto_corte.py — Simulador: Quando vender o animal?

Compara receita HOJE vs esperar N dias, considerando:
- Peso atual + GMD esperado → peso futuro
- Preço hoje vs preço esperado futuro
- Custo diário continuado

Responde: "Vendo agora por R$X ou espero 30 dias por R$Y?"
"""

import pandas as pd
from datetime import datetime, timedelta
import pesagem
import animais as A


def simular_ponto_corte(animal_id: str, df_man: pd.DataFrame, df_animais: pd.DataFrame,
                        preço_arroba: float, rendimento: float = 0.52,
                        dias_simular: list = None,
                        gmd_esperado: float = None, custo_diario: float = None) -> dict:
    """
    Simula receita HOJE vs esperar N dias.

    Args:
        animal_id: ID do animal (ex: "A0001")
        df_man: aba Manejo (fonte das pesagens)
        df_animais: aba Animais (confere se o animal existe/está vivo)
        preço_arroba: R$/arroba hoje (de calculos.preco_arroba_config)
        rendimento: carcaça/vivo — 0,52 para Nelore
        dias_simular: [0, 7, 14, 30] → dias futuros a simular
        gmd_esperado: kg/dia (se None, estima da tendência)
        custo_diario: R$/dia (se None, usa o custo médio por cabeça/dia do rebanho)

    Returns:
        {
            "animal_id", "peso_atual", "gmd", "custo_diario", "preço_arroba",
            "simulacao": [{dias, peso_esperado, arrobas, receita,
                           custo_continuado, resultado, status}, ...],
            "melhor_dia", "melhor_resultado",
        }
        ou {"erro": "..."} quando não dá para simular.
    """
    if dias_simular is None:
        dias_simular = [0, 7, 14, 30]

    try:
        # 1. Peso atual do animal (só balança; estimativa por foto não entra no GMD)
        hist = pesagem.todas(df_man).get(animal_id)
        if not hist:
            return {"erro": f"{animal_id} sem pesagem registrada"}

        peso_atual = hist[-1][1]

        # 2. GMD: usa a tendência do animal; sem 2 pesagens, cai para o padrão de pasto
        if gmd_esperado is not None:
            gmd_estimado = gmd_esperado
        else:
            res = pesagem.resumo(hist)
            gmd_estimado = (res or {}).get("gmd_total") or 0.9

        # 3. Custo diário por cabeça: o mesmo indicador que o painel já calcula
        if custo_diario is None:
            from calculos import calcular_indicadores_extras
            from db import carregar_aba
            extra = calcular_indicadores_extras(
                carregar_aba("Compras"), carregar_aba("Gastos"),
                carregar_aba("Vendas"), df_man, 0.0, preço_arroba)
            custo_estimado = extra.get("custo_dia_cab") or 0.0
        else:
            custo_estimado = custo_diario

        # 4. Simular cada dia. O preço da arroba é mantido (não há previsão de
        # mercado no sistema); o que muda é o peso e o custo de manter o animal.
        simulacao = []
        for dia in dias_simular:
            peso_futuro = peso_atual + (gmd_estimado * dia)
            arrobas = peso_futuro * rendimento / 15.0
            receita = arrobas * preço_arroba
            custo_continuado = custo_estimado * dia
            resultado = receita - custo_continuado
            simulacao.append({
                "dias": dia,
                "peso_esperado": round(peso_futuro, 1),
                "arrobas": round(arrobas, 2),
                "receita": round(receita, 2),
                "custo_continuado": round(custo_continuado, 2),
                "resultado": round(resultado, 2),
                "status": "",
            })

        # 5. Melhor dia e rótulos
        melhor = max(simulacao, key=lambda x: x["resultado"])
        base = simulacao[0]["resultado"]
        for sim in simulacao:
            if sim is melhor:
                sim["status"] = ("✅ VENDER HOJE — melhor opção" if sim["dias"] == 0
                                 else f"✅ Melhor esperar {sim['dias']}d")
            elif sim["dias"] == 0:
                sim["status"] = "Vender hoje"
            else:
                delta = sim["resultado"] - base
                sim["status"] = (f"Esperar {sim['dias']}d (+R$ {delta:,.2f})" if delta > 0
                                 else f"Esperar {sim['dias']}d (−R$ {abs(delta):,.2f})")

        return {
            "animal_id": animal_id,
            "peso_atual": round(peso_atual, 1),
            "gmd": round(gmd_estimado, 2),
            "custo_diario": round(custo_estimado, 2),
            "preço_arroba": preço_arroba,
            "rendimento": rendimento,
            "simulacao": simulacao,
            "melhor_dia": melhor["dias"],
            "melhor_resultado": melhor["resultado"],
        }

    except Exception as e:
        return {"erro": str(e)}


def recomendacao_venda(resultado_sim: dict) -> str:
    """Uma linha pronta para o topo da tela."""
    if "erro" in resultado_sim:
        return f"❌ {resultado_sim['erro']}"

    animal = resultado_sim["animal_id"]
    peso = resultado_sim["peso_atual"]
    resultado = resultado_sim["melhor_resultado"]
    melhor = resultado_sim["melhor_dia"]

    if melhor == 0:
        return f"🎯 {animal}: vender HOJE — {peso} kg, R$ {resultado:,.2f}"
    ganho = resultado - resultado_sim["simulacao"][0]["resultado"]
    return (f"⏰ {animal}: esperar {melhor} dias rende R$ {ganho:,.2f} a mais "
            f"(total R$ {resultado:,.2f})")
