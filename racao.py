# -*- coding: utf-8 -*-
"""
Calculador de ração para o módulo leiteiro.

Balanceamento simplificado de alimentos com base em necessidades nutricionais
por categoria produtiva. Cálculos orientativos — não substitui nutricionista.
"""

from typing import Optional, Dict, List, Tuple
from db import carregar_aba


# Fórmulas simplificadas para cálculo de necessidades —
# Baseadas em tabelas Embrapa e NRC (National Research Council)

class NecessidadesCategorias:
    """Necessidades base (MS em % do peso vivo, PB e Energia por kg de MS).

    Valores base por categoria (sem considerar produção de leite):
    - MS: porcentagem do peso vivo que deve ser consumida como matéria seca
    - PB: proteína bruta em % da matéria seca
    - Energia: Mcal de energia metabolizável por kg de MS
    """
    BASE = {
        "Lactação": {"ms_pct": 4.5, "pb_pct_ms": 15.0, "energia_mcal_kg_ms": 1.65},
        "Seca": {"ms_pct": 2.5, "pb_pct_ms": 10.0, "energia_mcal_kg_ms": 1.40},
        "Novilha": {"ms_pct": 3.0, "pb_pct_ms": 12.0, "energia_mcal_kg_ms": 1.50},
        "Bezerro": {"ms_pct": 4.0, "pb_pct_ms": 18.0, "energia_mcal_kg_ms": 1.60},
    }

    # Incremento por litro de leite em lactação (Embrapa simplificado)
    # Para vaca 500kg produzindo 20L — extra: ~3kg MS, 600g PB, 10 Mcal EM
    LACTACAO_POR_LITRO = {
        "ms_kg": 0.6,          # kg MS extra por litro
        "pb_g": 100.0,         # g PB extra por litro
        "energia_mcal": 0.5,   # Mcal EM extra por litro
    }


def calcular_necessidades(
    categoria: str,
    peso_vivo_kg: float,
    producao_litros_dia: float = 0.0,
) -> Dict[str, float]:
    """
    Calcula as necessidades diárias de uma vaca.

    Args:
        categoria: Lactação, Seca, Novilha ou Bezerro
        peso_vivo_kg: Peso vivo em kg
        producao_litros_dia: Produção de leite por dia (só para Lactação)

    Returns:
        Dict com:
        - ms_kg: Matéria seca total em kg
        - pb_g: Proteína bruta total em gramas
        - energia_mcal: Energia metabolizável total em Mcal
        - proteina_pct_ms: Proteína como % da MS (referência)
        - energia_kcal_kg_ms: Energia como kcal/kg MS (referência)
    """
    if categoria not in NecessidadesCategorias.BASE:
        raise ValueError(f"Categoria inválida: {categoria}")

    base = NecessidadesCategorias.BASE[categoria]

    # Necessidade base de MS
    ms_kg = peso_vivo_kg * base["ms_pct"] / 100.0

    # Necessidade base de PB (em gramas)
    pb_g = ms_kg * base["pb_pct_ms"] * 10  # % → g/kg

    # Necessidade base de Energia (em Mcal)
    energia_mcal = ms_kg * base["energia_mcal_kg_ms"]

    # Se for lactação, adiciona requisitos extras por litro
    if categoria == "Lactação" and producao_litros_dia > 0:
        lac = NecessidadesCategorias.LACTACAO_POR_LITRO
        ms_kg += lac["ms_kg"] * producao_litros_dia
        pb_g += lac["pb_g"] * producao_litros_dia
        energia_mcal += lac["energia_mcal"] * producao_litros_dia

    return {
        "ms_kg": round(ms_kg, 2),
        "pb_g": round(pb_g, 1),
        "energia_mcal": round(energia_mcal, 2),
        "proteina_pct_ms": round(base["pb_pct_ms"], 1),
        "energia_kcal_kg_ms": round(base["energia_mcal_kg_ms"] * 1000, 0),
    }


def carregar_ingredientes_ativos() -> List[Dict]:
    """
    Lê produtos da aba "Leite Alimentação" marcados como Ativo.

    Retorna:
        Lista de dicts com: nome, proteina_pct, ndt_pct, categoria
    """
    try:
        df = carregar_aba("Leite Alimentação")
    except Exception:
        return []

    if df.empty:
        return []

    ingredientes = []
    for _, linha in df.iterrows():
        ativo = str(linha.get("Ativo", "Sim")).strip().lower()
        if ativo != "sim":
            continue

        try:
            nome = str(linha.get("Produto", "")).strip()
            categoria = str(linha.get("Categoria", "")).strip()
            pb = float(str(linha.get("Proteína Bruta (%)", "0")).replace(",", "."))
            ndt = float(str(linha.get("NDT/Energia (%)", "0")).replace(",", "."))

            if nome and pb > 0 and ndt > 0:
                ingredientes.append({
                    "nome": nome,
                    "categoria": categoria,
                    "proteina_pct": pb,
                    "ndt_pct": ndt,
                })
        except (ValueError, TypeError):
            continue

    return ingredientes


def balancear_racao(
    necessidades: Dict[str, float],
    ingredientes: List[Dict],
    max_combinacoes: int = 3,
) -> Optional[Dict]:
    """
    Sugere uma combinação simples de ingredientes (2-3) que aproxima as necessidades.

    Algoritmo: força bruta — tenta todas as combinações de até max_combinacoes
    ingredientes e escolhe a que melhor aproxima PB e Energia mantendo MS razoável.

    Args:
        necessidades: Dict retornado por calcular_necessidades()
        ingredientes: Lista retornada por carregar_ingredientes_ativos()
        max_combinacoes: Máximo de ingredientes na sugestão (padrão 3)

    Returns:
        Dict com a melhor sugestão:
        {
            "ingredientes": [{"nome", "kg", "pb_contribuido_g", "energia_contribuida_mcal"}, ...],
            "ms_total_kg": float,
            "pb_total_g": float,
            "energia_total_mcal": float,
            "score": float (0-100, quanto maior melhor),
        }
        Ou None se não houver ingredientes.
    """
    if not ingredientes:
        return None

    ms_alvo = necessidades["ms_kg"]
    pb_alvo = necessidades["pb_g"]
    energia_alvo = necessidades["energia_mcal"]

    melhor_combo = None
    melhor_score = -1

    # Simplificação: tenta combos de 2-3 ingredientes com pesos fixos
    # Isso é aproximado, mas funciona bem para um calculador simplificado

    # Combo de 1 ingrediente (peso total = necessidade de MS)
    for ing in ingredientes:
        combo = _avaliar_combo(
            [ing],
            [ms_alvo],  # Use todo MS num ingrediente só
            pb_alvo,
            energia_alvo,
        )
        if combo["score"] > melhor_score:
            melhor_score = combo["score"]
            melhor_combo = combo

    # Combos de 2 ingredientes (50% cada, aproximadamente)
    for i, ing1 in enumerate(ingredientes):
        for ing2 in ingredientes[i+1:]:
            # Tenta 50/50
            kg1 = ms_alvo * 0.5
            kg2 = ms_alvo * 0.5
            combo = _avaliar_combo(
                [ing1, ing2],
                [kg1, kg2],
                pb_alvo,
                energia_alvo,
            )
            if combo["score"] > melhor_score:
                melhor_score = combo["score"]
                melhor_combo = combo

            # Tenta 60/40
            kg1 = ms_alvo * 0.6
            kg2 = ms_alvo * 0.4
            combo = _avaliar_combo(
                [ing1, ing2],
                [kg1, kg2],
                pb_alvo,
                energia_alvo,
            )
            if combo["score"] > melhor_score:
                melhor_score = combo["score"]
                melhor_combo = combo

    # Combos de 3 ingredientes (33/33/33, 40/40/20, etc.)
    if max_combinacoes >= 3 and len(ingredientes) >= 3:
        for i, ing1 in enumerate(ingredientes):
            for j, ing2 in enumerate(ingredientes[i+1:], start=i+1):
                for ing3 in ingredientes[j+1:]:
                    # Tenta 33/33/33
                    kg = ms_alvo / 3.0
                    combo = _avaliar_combo(
                        [ing1, ing2, ing3],
                        [kg, kg, kg],
                        pb_alvo,
                        energia_alvo,
                    )
                    if combo["score"] > melhor_score:
                        melhor_score = combo["score"]
                        melhor_combo = combo

    return melhor_combo


def _avaliar_combo(
    ingredientes: List[Dict],
    pesos_kg: List[float],
    pb_alvo: float,
    energia_alvo: float,
) -> Dict:
    """
    Avalia uma combinação específica de ingredientes.

    Returns:
        Dict com ms_total_kg, pb_total_g, energia_total_mcal, score (0-100).
    """
    ms_total = sum(pesos_kg)
    pb_total = 0.0
    energia_total = 0.0

    for ing, kg in zip(ingredientes, pesos_kg):
        # PB: %(PB) × kg × 10 = g
        pb_total += ing["proteina_pct"] * kg * 10
        # Energia: %(NDT) / 100 × kg × 1.36 Mcal/kg NDT ≈ Mcal
        # NDT é dado em %, convertemos para fração: %/100 × kg × fator de conversão
        # Simplificado: NDT% × kg × 0.0136 ≈ Mcal (aproximado)
        energia_total += (ing["ndt_pct"] / 100.0) * kg * 2.0  # fator ~2.0 para Mcal

    # Score: quanto perto de alvo em PB e Energia (MS naturalmente bate)
    # Penaliza desvios grandes
    desvio_pb = abs(pb_total - pb_alvo)
    desvio_energia = abs(energia_total - energia_alvo)

    # Normaliza desvios: máximo 100% de desvio = score 0
    score_pb = max(0, 100 - (desvio_pb / max(1, pb_alvo) * 100))
    score_energia = max(0, 100 - (desvio_energia / max(1, energia_alvo) * 100))

    # Score final: média ponderada (PB é mais crítico em leite)
    score = score_pb * 0.6 + score_energia * 0.4

    return {
        "ingredientes": [
            {
                "nome": ing["nome"],
                "kg": round(kg, 2),
                "pb_g": round(ing["proteina_pct"] * kg * 10, 1),
                "energia_mcal": round((ing["ndt_pct"] / 100.0) * kg * 2.0, 2),
            }
            for ing, kg in zip(ingredientes, pesos_kg)
        ],
        "ms_total_kg": round(ms_total, 2),
        "pb_total_g": round(pb_total, 1),
        "energia_total_mcal": round(energia_total, 2),
        "score": round(score, 1),
    }


def fazer_comparativo(necessidades: Dict, sugestao: Dict) -> List[Dict]:
    """
    Cria uma lista de comparação Necessário vs. Oferecido para a UI.

    Returns:
        Lista de dicts com: nutriente, necessario, oferecido, pct_atendimento, status
    """
    return [
        {
            "nutriente": "Matéria Seca (kg)",
            "necessario": necessidades["ms_kg"],
            "oferecido": sugestao["ms_total_kg"],
            "pct": round(100 * sugestao["ms_total_kg"] / max(1, necessidades["ms_kg"]), 1),
            "status": _avaliar_status(sugestao["ms_total_kg"], necessidades["ms_kg"]),
        },
        {
            "nutriente": "Proteína Bruta (g)",
            "necessario": necessidades["pb_g"],
            "oferecido": sugestao["pb_total_g"],
            "pct": round(100 * sugestao["pb_total_g"] / max(1, necessidades["pb_g"]), 1),
            "status": _avaliar_status(sugestao["pb_total_g"], necessidades["pb_g"]),
        },
        {
            "nutriente": "Energia (Mcal)",
            "necessario": necessidades["energia_mcal"],
            "oferecido": sugestao["energia_total_mcal"],
            "pct": round(100 * sugestao["energia_total_mcal"] / max(1, necessidades["energia_mcal"]), 1),
            "status": _avaliar_status(sugestao["energia_total_mcal"], necessidades["energia_mcal"]),
        },
    ]


def _avaliar_status(oferecido: float, necessario: float) -> str:
    """Retorna 'ok', 'aviso' ou 'ruim' baseado no atendimento (85-115% é ok)."""
    pct = 100 * oferecido / max(1, necessario)
    if 85 <= pct <= 115:
        return "ok"
    elif 70 <= pct <= 130:
        return "aviso"
    else:
        return "ruim"
