#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
consanguinidade.py — Cálculo de coeficiente de endogamia e análise de progênie (v5.10 Onda 4)
"""
import pandas as pd
from typing import Dict, List, Tuple
import animais


# Limite seguro de consanguinidade
LIMITE_ENDOGAMIA_SEGURO = 6.25  # %
LIMITE_ENDOGAMIA_ALERTA = 3.13  # %


def construir_pedigree() -> Dict:
    """
    Constrói árvore genealógica a partir de Animais.
    Formato: {animal_id: {pai: id, mae: id}}
    """
    try:
        df = animais.carregar()
        pedigree = {}

        for _, animal in df.iterrows():
            animal_id = str(animal.get('ID', '')).strip()
            pai = str(animal.get('Pai', '')).strip() or None
            mae = str(animal.get('Mãe', '')).strip() or None

            if animal_id:
                pedigree[animal_id] = {
                    "pai": pai,
                    "mae": mae,
                    "nome": f"{animal.get('Brinco Cor', '')} {animal.get('Brinco Nº', '')}",
                    "categoria": str(animal.get('Categoria', '')).lower()
                }

        return pedigree
    except Exception as e:
        print(f"Erro ao construir pedigree: {e}")
        return {}


def calcular_coeficiente_endogamia(animal_id: str, pedigree: Dict = None) -> float:
    """
    Calcula coeficiente de endogamia de Wright.
    Fórmula simplificada: F = (1/2)^n onde n = número de gerações até ancestral comum.
    Versão expandida: F = Σ[(1/2)^(n1+n2+1) * (1 + F_ancestral)]

    Para simplicidade, usa método de contagem: quanto mais próximos pai/mãe, maior F.
    """
    if pedigree is None:
        pedigree = construir_pedigree()

    if animal_id not in pedigree:
        return 0.0

    animal = pedigree[animal_id]
    pai = animal.get("pai")
    mae = animal.get("mae")

    if not pai or not mae:
        return 0.0

    # Verifica se pais têm ancestral comum (coeficiente de relação)
    ancestrais_pai = _obter_ancestrais(pai, pedigree, gerações=4)
    ancestrais_mae = _obter_ancestrais(mae, pedigree, gerações=4)

    # Ancestrais comuns
    comuns = set(ancestrais_pai.keys()) & set(ancestrais_mae.keys())

    if not comuns:
        return 0.0

    # Calcula F para cada ancestral comum
    f_total = 0.0
    for ancestral in comuns:
        # Distância em gerações
        geracao_pai = ancestrais_pai[ancestral]
        geracao_mae = ancestrais_mae[ancestral]

        # Coeficiente de relação: (1/2)^(n1+n2)
        coef_relacao = (0.5) ** (geracao_pai + geracao_mae)

        # Contribuição à endogamia
        f_total += coef_relacao

    # Retorna em porcentagem (multiplicado por 100 depois)
    return f_total * 100


def _obter_ancestrais(animal_id: str, pedigree: Dict, gerações: int = 4) -> Dict:
    """Retorna {ancestral_id: geração} até N gerações."""
    ancestrais = {}

    def _recursivo(aid, gen):
        if aid not in pedigree or gen == 0:
            return

        if aid not in ancestrais:
            ancestrais[aid] = gen

        animal = pedigree[aid]
        if animal.get("pai"):
            _recursivo(animal["pai"], gen - 1)
        if animal.get("mae"):
            _recursivo(animal["mae"], gen - 1)

    _recursivo(animal_id, gerações)
    return ancestrais


def analisar_progenie(animal_id: str) -> Dict:
    """
    Analisa progênie de um animal (filhos registrados).
    Retorna: média de peso, GMD, preço dos filhos.
    """
    try:
        df_animais = animais.carregar()

        # Encontra filhos (pai ou mãe = animal_id)
        filhos = df_animais[
            (df_animais.get('Pai', '').astype(str) == str(animal_id)) |
            (df_animais.get('Mãe', '').astype(str) == str(animal_id))
        ]

        if filhos.empty:
            return {
                "animal_id": animal_id,
                "total_filhos": 0,
                "media_peso": None,
                "media_preco": None
            }

        total = len(filhos)
        media_peso = filhos.get('Peso', []).astype(float, errors='ignore').mean()

        # Tenta pegar preço do último registro de venda
        media_preco = None

        return {
            "animal_id": animal_id,
            "total_filhos": total,
            "media_peso": round(media_peso, 1) if pd.notna(media_peso) else None,
            "media_preco": media_preco,
            "filhos": [
                {
                    "id": str(f.get('ID', '')),
                    "brinco": f"{f.get('Brinco Cor', '')} {f.get('Brinco Nº', '')}",
                    "peso": f.get('Peso', '')
                }
                for _, f in filhos.iterrows()
            ]
        }
    except Exception as e:
        print(f"Erro ao analisar progênie: {e}")
        return {"animal_id": animal_id, "total_filhos": 0}


def gerar_alertas_consanguinidade() -> List[Dict]:
    """Gera alertas para animais com endogamia elevada."""
    alertas = []
    pedigree = construir_pedigree()

    try:
        df_animais = animais.carregar()

        for _, animal in df_animais.iterrows():
            animal_id = str(animal.get('ID', '')).strip()
            categoria = str(animal.get('Categoria', '')).lower()

            # Apenas vacas em reprodução
            if not animal_id or 'vaca' not in categoria:
                continue

            f = calcular_coeficiente_endogamia(animal_id, pedigree)

            tipo_alerta = None
            motivo = ""

            if f > LIMITE_ENDOGAMIA_SEGURO:
                tipo_alerta = "urgente"
                motivo = f"Endogamia CRÍTICA: {f:.2f}% (limite seguro: 6.25%)"
            elif f > LIMITE_ENDOGAMIA_ALERTA:
                tipo_alerta = "aviso"
                motivo = f"Endogamia elevada: {f:.2f}% (recomendação: < 3.13%)"

            if tipo_alerta:
                brinco = f"{animal.get('Brinco Cor', '')} {animal.get('Brinco Nº', '')}"
                alertas.append({
                    "tipo": tipo_alerta,
                    "animal_id": animal_id,
                    "animal_desc": brinco,
                    "coeficiente": round(f, 2),
                    "motivo": motivo,
                    "recomendacao": "Acasalar com animal de linhagem diferente"
                })

    except Exception as e:
        print(f"Erro ao gerar alertas de consanguinidade: {e}")

    alertas.sort(key=lambda a: (-a['coeficiente']))
    return alertas


def sugerir_acasalamentos(vaca_id: str) -> List[Dict]:
    """
    Sugere touros compatíveis para uma vaca (menor endogamia).
    """
    pedigree = construir_pedigree()
    df_animais = animais.carregar()

    sugestoes = []

    try:
        # Obtém pedigree da vaca
        vaca_ancestrais = _obter_ancestrais(vaca_id, pedigree, gerações=4)

        # Procura touros
        touros = df_animais[df_animais.get('Categoria', '').astype(str).str.lower() == 'touro']

        for _, touro in touros.iterrows():
            touro_id = str(touro.get('ID', '')).strip()

            if not touro_id:
                continue

            # Calcula endogamia se este touro cobrisse a vaca
            touro_ancestrais = _obter_ancestrais(touro_id, pedigree, gerações=4)

            ancestrais_comuns = len(set(vaca_ancestrais.keys()) & set(touro_ancestrais.keys()))

            brinco = f"{touro.get('Brinco Cor', '')} {touro.get('Brinco Nº', '')}"

            sugestoes.append({
                "touro_id": touro_id,
                "touro_desc": brinco,
                "ancestrais_comuns": ancestrais_comuns,
                "score": 10 - ancestrais_comuns  # Quanto mais baixo melhor
            })

    except Exception as e:
        print(f"Erro ao sugerir acasalamentos: {e}")

    # Ordena: menor ancestrais comuns (melhor)
    sugestoes.sort(key=lambda s: s['ancestrais_comuns'])
    return sugestoes[:5]  # Top 5


if __name__ == '__main__':
    print("=== Análise de Consanguinidade ===")
    alertas = gerar_alertas_consanguinidade()
    print(f"Animais com endogamia elevada: {len(alertas)}")
    for a in alertas[:3]:
        print(f"  {a['animal_desc']}: {a['coeficiente']:.2f}%")
