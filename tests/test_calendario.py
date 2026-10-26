# -*- coding: utf-8 -*-
import pandas as pd

import calendario


def _manejo(**kw):
    base = {"Data": "", "Tipo": "", "Descrição": "", "Produto": "", "Brincos": ""}
    base.update(kw)
    return base


def test_eventos_normaliza_fontes_e_ignora_data_invalida():
    dados = {
        "Manejo": pd.DataFrame([
            _manejo(Data="10/10/2026", Tipo="Pesagem", Descrição="Curral"),
            _manejo(Data="não é data", Tipo="Pesagem"),
            _manejo(Data="05/10/2026", Tipo="Movimentação de Pasto", Descrição="P01"),
        ]),
        "Visitas": pd.DataFrame([{"Data": "08/10/2026", "Responsável": "Deyvid"}]),
    }
    eventos = calendario.eventos(dados, inicio="01/10/2026", fim="31/10/2026")
    assert [e["data"].strftime("%d/%m") for e in eventos] == ["05/10", "08/10", "10/10"]
    assert all(e["origem"] in {"Manejo", "Visitas"} for e in eventos)


def test_eventos_filtra_por_tipo_e_mantem_vazio():
    assert calendario.eventos({}, tipo="saude") == []
    dados = {"Manejo": pd.DataFrame([_manejo(Data="10/10/2026", Tipo="Vacina Raiva")])}
    assert calendario.eventos(dados, tipo="saude")[0]["tipo"] == "saude"
