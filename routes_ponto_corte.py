#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
routes_ponto_corte.py — Simulador "vender hoje ou esperar?" (v5.14)

Só leitura: roda ponto_corte.simular_ponto_corte() e mostra a tabela.
Nada é gravado na planilha.
"""
from flask import render_template, request

import animais as A
import pesagem
import ponto_corte as PC
from calculos import preco_arroba_config
from extensions import app, login_required, _get_dados_cache, _ler_sitio_config_disco


@app.route("/ponto-corte")
@login_required
def ponto_corte():
    """Simulação de venda por animal. Sem ?animal=, mostra a lista para escolher."""
    dados = _get_dados_cache()
    df_man = dados["Manejo"]
    animal_id = (request.args.get("animal") or "").strip() or None

    cfg = _ler_sitio_config_disco()
    preco = preco_arroba_config(cfg)
    try:
        rendimento = float(cfg.get("rendimento", 52) or 52) / 100.0
    except (TypeError, ValueError):
        rendimento = 0.52

    sim = None
    if animal_id:
        sim = PC.simular_ponto_corte(
            animal_id, df_man, A.carregar(), preco, rendimento,
            gmd_esperado=_num(request.args.get("gmd")),
            custo_diario=_num(request.args.get("custo")),
        )

    return render_template(
        "ponto_corte.html",
        sim=sim,
        animal_id=animal_id,
        ids_pesados=sorted(pesagem.todas(df_man)),
        preco_arroba=preco,
        rendimento=rendimento,
        recomendacao=PC.recomendacao_venda(sim) if sim else None,
    )


def _num(v):
    """Texto do formulário → float, ou None (aí o simulador estima sozinho)."""
    try:
        f = float(str(v).replace(",", "."))
        return f if f > 0 else None
    except (TypeError, ValueError):
        return None
