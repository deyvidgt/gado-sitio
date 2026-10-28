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
import calculos as C


def simular_ponto_corte(animal_id: str, preço_hoje: float, dias_simular: list = None,
                        gmd_esperado: float = None, custo_diario: float = None) -> dict:
    """
    Simula receita HOJE vs esperar N dias.

    Args:
        animal_id: ID do animal (ex: "A0001")
        preço_hoje: R$/kg ou R$/arroba (hoje)
        dias_simular: [0, 7, 14, 30] → dias futuros a simular
        gmd_esperado: kg/dia (se None, estima da tendência)
        custo_diario: R$/dia (se None, estima de gastos recentes)

    Returns:
        {
            "animal_id": "A0001",
            "peso_atual": 450,
            "gmd": 0.9,
            "custo_diario": 18,
            "preço_hoje": 30,
            "simulacao": [
                {
                    "dias": 0,
                    "peso_esperado": 450,
                    "receita": 13500,
                    "custo_continuado": 0,
                    "resultado": 12700,
                    "resultado_diario": 0,
                    "status": "HOJE — Melhor opção" ou "Espera"
                },
                ...
            ],
            "melhor_dia": 0,
            "melhor_resultado": 12700,
        }
    """
    if dias_simular is None:
        dias_simular = [0, 7, 14, 30]

    try:
        # 1. Buscar peso atual do animal
        pesos = pesagem.todas()
        if isinstance(pesos, pd.DataFrame):
            pesos_animal = pesos[pesos['Animal ID'] == animal_id]
            if pesos_animal.empty:
                return {"erro": f"Animal {animal_id} sem pesagem registrada"}
            peso_atual = pesos_animal.iloc[-1]['Peso (kg)']
        else:
            return {"erro": "Sem histórico de pesagens"}

        # 2. Estimar GMD se não foi passado
        if gmd_esperado is None:
            # Usar GMD dos últimos 60 dias do animal
            pesos_60d = pesagem.peso_animal(animal_id, dias=60)
            if pesos_60d and len(pesos_60d) >= 2:
                ganho = pesos_60d[-1] - pesos_60d[0]
                gmd_estimado = ganho / 60
            else:
                gmd_estimado = 0.9  # Default para corte em pasto
        else:
            gmd_estimado = gmd_esperado

        # 3. Estimar custo diário se não foi passado
        if custo_diario is None:
            # Buscar gastos dos últimos 30 dias
            gastos_recentes = C._build_gastos_timeline()
            if gastos_recentes:
                ultimos_30 = [g for g in gastos_recentes if g['dias_atras'] <= 30]
                if ultimos_30:
                    gasto_total = sum(g['valor'] for g in ultimos_30)
                    cabeças_vivas = C.calcular_estoque()['total']
                    custo_estimado = (gasto_total / 30) / max(cabeças_vivas, 1)
                else:
                    custo_estimado = 18  # Default
            else:
                custo_estimado = 18
        else:
            custo_estimado = custo_diario

        # 4. Buscar custo já investido no animal (média móvel)
        estoque_info = C.calcular_estoque_por_membro()
        custo_investido = 0  # Aproximação: não sabemos custo individual

        # 5. Simular cada dia
        simulacao = []
        for dia in dias_simular:
            peso_futuro = peso_atual + (gmd_estimado * dia)
            receita = peso_futuro * preço_hoje  # Simplificação: mesmo preço
            # Na realidade, preço cai ~2% por semana em mercado

            # Simular queda de preço futuro (-2% por semana)
            semanas = dia / 7
            taxa_queda = (1 - 0.02) ** semanas
            preço_futuro = preço_hoje * taxa_queda
            receita_real = peso_futuro * preço_futuro

            custo_continuado = custo_estimado * dia
            resultado = receita_real - custo_continuado
            resultado_por_dia = resultado / max(dia, 1)

            simulacao.append({
                "dias": dia,
                "peso_esperado": round(peso_futuro, 1),
                "preço_esperado": round(preço_futuro, 2),
                "receita": round(receita_real, 2),
                "custo_continuado": round(custo_continuado, 2),
                "resultado": round(resultado, 2),
                "resultado_por_dia": round(resultado_por_dia, 2),
                "status": "",
            })

        # 6. Identificar melhor dia
        melhor_sim = max(simulacao, key=lambda x: x['resultado'])
        melhor_dia = melhor_sim['dias']

        # Marcar status
        for sim in simulacao:
            if sim['dias'] == melhor_dia:
                if melhor_dia == 0:
                    sim['status'] = "✅ HOJE — Melhor opção!"
                else:
                    sim['status'] = f"✅ +{melhor_dia}d — Melhor opção (ganha R${melhor_sim['resultado']-simulacao[0]['resultado']:.2f})"
            else:
                ganho_vs_hoje = sim['resultado'] - simulacao[0]['resultado']
                if ganho_vs_hoje > 0:
                    sim['status'] = f"Espera {sim['dias']}d (+R${ganho_vs_hoje:.2f})"
                else:
                    sim['status'] = f"Espera {sim['dias']}d (perde R${abs(ganho_vs_hoje):.2f})"

        return {
            "animal_id": animal_id,
            "peso_atual": round(peso_atual, 1),
            "gmd": round(gmd_estimado, 2),
            "custo_diario": round(custo_estimado, 2),
            "preço_hoje": preço_hoje,
            "simulacao": simulacao,
            "melhor_dia": melhor_dia,
            "melhor_resultado": round(melhor_sim['resultado'], 2),
        }

    except Exception as e:
        return {"erro": str(e)}


def recomendacao_venda(resultado_sim: dict) -> str:
    """
    Retorna recomendação textual baseada na simulação.
    """
    if "erro" in resultado_sim:
        return f"❌ Erro: {resultado_sim['erro']}"

    melhor = resultado_sim['melhor_dia']
    animal = resultado_sim['animal_id']
    peso = resultado_sim['peso_atual']
    resultado = resultado_sim['melhor_resultado']

    if melhor == 0:
        return f"🎯 {animal}: Vender HOJE! Peso {peso}kg, resultado R${resultado:.2f}"
    else:
        return f"⏰ {animal}: Esperar {melhor} dias. Ganho extra R${resultado - resultado_sim['simulacao'][0]['resultado']:.2f}"
