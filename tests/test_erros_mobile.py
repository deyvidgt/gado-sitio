# -*- coding: utf-8 -*-
"""Regressões encontradas nas capturas de uso em celular e desktop."""
import json

import db
import pastos as PA


def _postura_pasto():
    return {
        "type": "Polygon",
        "coordinates": [[
            [-48.280, -18.920], [-48.285, -18.920],
            [-48.285, -18.925], [-48.280, -18.925],
            [-48.280, -18.920],
        ]],
    }


def test_manejo_ordena_datas_cronologicamente_no_padrao(cliente, dados_restaurados):
    db.salvar_linha("Manejo", [
        "02/01/2024", "Outro", 1, "Registro mais novo", "Deyvid", "", "", "", "", ""
    ])
    db.salvar_linha("Manejo", [
        "28/12/2023", "Outro", 1, "Registro mais antigo", "Deyvid", "", "", "", "", ""
    ])

    html = cliente.get("/manejo").get_data(as_text=True)

    assert html.index("Registro mais novo") < html.index("Registro mais antigo")


def test_pastos_nao_renderizam_brinco_nan(cliente, dados_restaurados):
    pasto_id = PA.criar("Pasto sem nan", json.dumps(_postura_pasto()))
    db.salvar_linha("Manejo", [
        "29/10/2026", "Movimentação de Pasto", 1, "", "Deyvid", "", "",
        "", "nan, Amarelo 21", "",
    ])

    html = cliente.get("/pastos").get_data(as_text=True).lower()

    assert ">nan<" not in html
    assert "nan cab" not in html
    assert "nan, amarelo 21" not in html
    assert "pasto sem nan" in html.lower()


def test_comparativo_anual_tem_tabela_com_rolagem_horizontal(cliente):
    html = cliente.get("/comparativo-anual").get_data(as_text=True)

    assert "overflow-x:auto" in html.replace(" ", "")
    assert "table-wrap" in html or "table-responsiva" in html


def test_dashboard_nao_renderiza_fab_sobre_navegacao_inferior(cliente):
    html = cliente.get("/").get_data(as_text=True)

    assert "class=\"fab-container\"" not in html
    assert "Registrar nova visita" not in html


def test_pastos_renderizam_pin_por_animal_com_posicao_deterministica(cliente, dados_restaurados):
    PA.criar("Pasto dos animais", json.dumps(_postura_pasto()))
    db.salvar_linha("Manejo", [
        "29/10/2026", "Movimentação de Pasto", 2, "", "Deyvid", "", "",
        "", "Amarelo 21 #A0001, Azul 07 #A0002", "",
    ])

    html = cliente.get("/pastos").get_data(as_text=True)

    assert "p.animais_dados.forEach" in html
    assert "animalIndex" in html
    assert "p.geo.coordinates" in html
