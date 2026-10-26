# -*- coding: utf-8 -*-

def test_dashboard_exibe_blocos_operacionais(cliente):
    html = cliente.get("/").get_data(as_text=True)
    for texto in ("Estado do sítio", "Ações rápidas", "Atenção agora", "Ocorrências recentes", "Tendência de peso"):
        assert texto in html


def test_calendario_abre_e_aparece_no_menu(cliente):
    assert cliente.get("/calendario").status_code == 200
    html = cliente.get("/").get_data(as_text=True)
    assert "Calendário" in html
