# -*- coding: utf-8 -*-
"""
insumos.py — estoque e previsão de Sal, Proteinado e Ração
==========================================================
Fonte única usada pelo painel e pelo WhatsApp.

De onde vêm os números:
  • Visitas: o campo "Sacos" de cada insumo é o ESTOQUE contado no sítio naquele
    dia (sacos guardados). Campo vazio = não contou (a visita é ignorada).
  • Gastos: compras com Produto (Sal/Proteinado/Ração) e "Qtd Sacos".

Consumo entre duas contagens:
    consumo = estoque_antes + compras_no_intervalo − estoque_depois
Se der negativo, faltou lançar uma compra — o intervalo é descartado em vez de
virar consumo negativo. O consumo médio usa os intervalos dos últimos 120 dias.

Estoque estimado hoje:
    última contagem + compras depois dela − consumo médio × dias desde a contagem
"""
from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd

from config import INSUMOS

JANELA_DIAS = 120        # intervalos de contagem considerados no consumo médio
ANTECEDENCIA_DIAS = 5    # "compre até" = esta quantidade de dias antes de acabar
DIAS_URGENTE = 7         # acabando em até N dias → alerta urgente no WhatsApp


def _num(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if f == f else None


def _contagens(df_vis: pd.DataFrame, coluna: str) -> list[tuple[pd.Timestamp, float]]:
    """[(data, sacos)] das visitas em que o estoque foi contado, em ordem de data.
    Duas contagens no mesmo dia: vale a última registrada."""
    if df_vis is None or df_vis.empty or coluna not in df_vis.columns or "Data" not in df_vis.columns:
        return []
    por_dia = {}
    for _, r in df_vis[df_vis["Data"].notna()].iterrows():
        q = _num(r.get(coluna))
        if q is not None and q >= 0:
            por_dia[r["Data"].normalize()] = q
    return sorted(por_dia.items())


def _compras(df_gast: pd.DataFrame, produto: str) -> list[tuple[pd.Timestamp, float]]:
    if df_gast is None or df_gast.empty or "Produto" not in df_gast.columns:
        return []
    out = []
    for _, r in df_gast[df_gast["Data"].notna()].iterrows():
        if str(r.get("Produto") or "").strip() != produto:
            continue
        q = _num(r.get("Qtd Sacos"))
        if q and q > 0:
            out.append((r["Data"].normalize(), q))
    return out


def _comprado_entre(compras, inicio, fim) -> float:
    """Sacos comprados com data em (inicio, fim] — a contagem do dia já inclui
    o que foi comprado e guardado naquele mesmo dia."""
    return sum(q for d, q in compras if inicio < d <= fim)


def previsao_insumo(produto: str, df_vis: pd.DataFrame, df_gast: pd.DataFrame,
                    hoje: datetime | None = None) -> dict:
    """
    Situação de um insumo. Campos:
      contado_em / contado     — última contagem (data, sacos) ou None
      estoque                  — sacos estimados hoje (None sem contagem)
      consumo_dia              — sacos por dia (None se ainda não dá para calcular)
      dias_restantes, acaba_em, comprar_ate
      status                   — sem_dados | sem_consumo | ok | proximo | urgente | acabou
    """
    hoje = pd.Timestamp(hoje or datetime.now()).normalize()
    coluna = INSUMOS[produto]
    contagens = [(d, q) for d, q in _contagens(df_vis, coluna) if d <= hoje]
    compras = _compras(df_gast, produto)

    res = {"produto": produto, "contado_em": None, "contado": None, "estoque": None,
           "consumo_dia": None, "dias_restantes": None, "acaba_em": None,
           "comprar_ate": None, "status": "sem_dados"}
    if not contagens:
        return res

    ult_data, ult_q = contagens[-1]
    res["contado_em"], res["contado"] = ult_data, ult_q

    # Consumo médio: intervalos entre contagens dentro da janela.
    inicio_janela = hoje - timedelta(days=JANELA_DIAS)
    consumo_total = dias_total = 0.0
    for (d1, q1), (d2, q2) in zip(contagens, contagens[1:]):
        if d2 <= inicio_janela:
            continue
        consumo = q1 + _comprado_entre(compras, d1, d2) - q2
        dias = (d2 - d1).days
        if consumo < 0 or dias <= 0:
            continue   # compra não lançada (ou dado inconsistente): não vira consumo
        consumo_total += consumo
        dias_total += dias

    comprado_depois = _comprado_entre(compras, ult_data, hoje)
    if dias_total <= 0 or consumo_total <= 0:
        res["estoque"] = ult_q + comprado_depois
        res["status"] = "sem_consumo"
        return res

    por_dia = consumo_total / dias_total
    estoque = max(0.0, ult_q + comprado_depois - por_dia * (hoje - ult_data).days)
    dias_rest = int(estoque / por_dia)
    acaba = hoje + timedelta(days=dias_rest)
    res.update({
        "estoque": round(estoque, 1),
        "consumo_dia": por_dia,
        "dias_restantes": dias_rest,
        "acaba_em": acaba,
        "comprar_ate": max(hoje, acaba - timedelta(days=ANTECEDENCIA_DIAS)),
        "status": ("acabou" if estoque <= 0 else
                   "urgente" if dias_rest <= DIAS_URGENTE else
                   "proximo" if dias_rest <= 21 else "ok"),
    })
    return res


def comparar(opcoes: list[dict], cabecas: int = 0) -> list[dict]:
    """Compara marcas de proteinado/ração pelo que custam de verdade.

    Cada opção: nome, preco_saco, kg_saco, consumo_g (gramas por cabeça/dia).
    O saco mais barato nem sempre ganha — quem come menos por cabeça pode sair
    na frente. Linha sem nome, preço ou peso é ignorada. Nada é gravado."""
    out = []
    for o in opcoes:
        nome = str(o.get("nome") or "").strip()
        preco, kg, g = (_num(o.get(k)) or 0 for k in ("preco_saco", "kg_saco", "consumo_g"))
        if not nome or preco <= 0 or kg <= 0:
            continue
        custo_kg = preco / kg
        dia = custo_kg * (g / 1000) if g > 0 else None
        out.append({"nome": nome, "preco_saco": preco, "kg_saco": kg, "consumo_g": g,
                    "custo_kg": custo_kg, "custo_cab_dia": dia,
                    "custo_mes": dia * cabecas * 30 if dia and cabecas > 0 else None})
    # Ordena pelo custo diário por cabeça; sem consumo informado, só pelo R$/kg.
    out.sort(key=lambda o: (o["custo_cab_dia"] is None, o["custo_cab_dia"] or o["custo_kg"]))
    for i, o in enumerate(out):
        o["melhor"] = i == 0
        o["diferenca_mes"] = (o["custo_mes"] - out[0]["custo_mes"]
                              if o["custo_mes"] is not None and out[0]["custo_mes"] is not None
                              else None)
    return out


def ultimo_preco_saco(df_gast, produto: str):
    """(R$ por saco, data) da última compra lançada deste insumo, ou None.
    Serve de sugestão no comparador — é o preço que a família pagou mesmo."""
    if df_gast is None or df_gast.empty or "Produto" not in df_gast.columns:
        return None
    g = df_gast[(df_gast["Produto"].astype(str).str.strip() == produto) & df_gast["Data"].notna()]
    for _, r in g.sort_values("Data").iloc[::-1].iterrows():
        sacos, total = _num(r.get("Qtd Sacos")), _num(r.get("Valor Total (R$)"))
        if sacos and sacos > 0 and total and total > 0:
            return round(total / sacos, 2), r["Data"]
    return None


def previsao_todos(df_vis, df_gast, hoje=None) -> list[dict]:
    return [previsao_insumo(p, df_vis, df_gast, hoje) for p in INSUMOS]


def texto_previsao(p: dict) -> str:
    """Uma linha legível (painel e WhatsApp)."""
    nome = p["produto"]
    if p["status"] == "sem_dados":
        return f"{nome}: estoque ainda não contado nas visitas."
    est = f"{p['estoque']:g}".replace(".", ",")
    if p["status"] == "sem_consumo":
        return (f"{nome}: ~{est} saco(s) em estoque — conte de novo na próxima visita "
                f"para calcular o consumo.")
    if p["status"] == "acabou":
        return f"{nome}: estoque provavelmente ACABOU — comprar já."
    a_cada = 1 / p["consumo_dia"]
    ritmo = (f"1 saco a cada {a_cada:.0f} dia(s)" if a_cada >= 1.5
             else f"{p['consumo_dia']:.1f} sacos/dia".replace(".", ","))
    return (f"{nome}: ~{est} saco(s), {ritmo} — acaba por volta de "
            f"{p['acaba_em']:%d/%m}; compre até {p['comprar_ate']:%d/%m}.")
