#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
genetica.py — Melhoramento genético: genealogia e endogamia (v5.10)

Funções simples:
- genealogia_animal() — retorna pai/mãe/genótipo de um animal
- calcular_endogamia() — aviso se pai == mãe (consanguinidade óbvia)
- compatibilidade_acasalamento() — verifica se dois animais podem cruzar
"""

import pandas as pd
from db import carregar_aba


def genealogia_animal(animal_id: str, dados: dict = None) -> dict:
    """Retorna genealogia (pai, mãe, genótipo) de um animal."""
    if dados is None:
        animais = carregar_aba("Animais")
    else:
        animais = dados.get("Animais", pd.DataFrame())

    if animais.empty:
        return {}

    linha = animais[animais.get("ID", "") == animal_id]
    if linha.empty:
        return {}

    row = linha.iloc[0]
    return {
        "animal_id": animal_id,
        "pai_id": row.get("Pai", ""),
        "mae_id": row.get("Mãe", ""),
        "genotipo": row.get("Genótipo", ""),
        "raca": row.get("Raça", ""),
        "brinco": f"{row.get('Brinco Cor', '')} {row.get('Brinco Nº', '')}",
    }


def calcular_endogamia_simples(pai_id: str, mae_id: str, dados: dict = None) -> dict:
    """
    Cálculo MUITO simples de endogamia:
    - Se pai_id == mae_id: consanguinidade óbvia (100%)
    - Senão: 0% (não faz cálculo genealógico completo)

    Retorna: {"risco": "nenhum" | "aviso" | "urgente", "coeficiente": float, "msg": str}
    """
    if not pai_id or not mae_id:
        return {
            "risco": "aviso",
            "coeficiente": 0,
            "msg": "Faltam dados de pai ou mãe"
        }

    if pai_id == mae_id:
        return {
            "risco": "urgente",
            "coeficiente": 100,
            "msg": f"❌ CONSANGUINIDADE: pai e mãe são o mesmo animal ({pai_id})"
        }

    # Se pais são diferentes, assumir coeficiente baixo
    # (cálculo completo precisaria de árvore genealógica completa)
    return {
        "risco": "nenhum",
        "coeficiente": 0,
        "msg": "✅ Pais diferentes: coeficiente de endogamia baixo"
    }


def compatibilidade_acasalamento(touro_id: str, vaca_id: str, dados: dict = None) -> dict:
    """Verifica se touro e vaca podem cruzar."""
    if not touro_id or not vaca_id:
        return {"compativel": False, "motivo": "Faltam IDs"}

    if touro_id == vaca_id:
        return {"compativel": False, "motivo": "Touro e vaca são o mesmo animal"}

    gen_touro = genealogia_animal(touro_id, dados)
    gen_vaca = genealogia_animal(vaca_id, dados)

    if not gen_touro or not gen_vaca:
        return {"compativel": False, "motivo": "Animal não cadastrado"}

    # Verificar se vaca é filha do touro (evitar pai-filha)
    if gen_vaca["pai_id"] == touro_id:
        return {"compativel": False, "motivo": "Risco: vaca é filha do touro"}

    # Verificar endogamia
    endogamia = calcular_endogamia_simples(touro_id, vaca_id, dados)
    if endogamia["risco"] == "urgente":
        return {"compativel": False, "motivo": endogamia["msg"]}

    return {
        "compativel": True,
        "motivo": f"✅ Acasalamento permitido",
        "endogamia": endogamia["coeficiente"]
    }


def avisos_genetica(dados: dict = None) -> list:
    """Retorna lista de avisos sobre endogamia/genealogia."""
    if dados is None:
        animais = carregar_aba("Animais")
    else:
        animais = dados.get("Animais", pd.DataFrame())

    avisos = []

    if animais.empty:
        return avisos

    # Procurar por animais com pai == mãe
    for _, animal in animais.iterrows():
        pai = animal.get("Pai", "")
        mae = animal.get("Mãe", "")
        animal_id = animal.get("ID", "")

        if pai and mae and pai == mae:
            avisos.append({
                "urgente": True,
                "texto": f"Animal {animal_id}: pai e mãe sao o mesmo ({pai})"
            })

    return avisos


def resumo_mensal_genetica(dados: dict = None) -> dict:
    """Retorna resumo de genetica para relatorio/WhatsApp."""
    avisos = avisos_genetica(dados)
    num_avisos = len([a for a in avisos if a.get("urgente")])

    return {
        "num_avisos": num_avisos,
        "mensagem": f"Genetica: {num_avisos} alerta(s) de endogamia detectado(s)" if num_avisos > 0 else "Genetica: Genealogia ok"
    }
