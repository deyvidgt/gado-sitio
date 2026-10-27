# -*- coding: utf-8 -*-


def test_menu_lateral_fica_acima_do_leaflet(cliente):
    html = cliente.get("/pastos").get_data(as_text=True)
    assert ".sidebar {" in html
    assert "z-index:1000" in html
    assert ".sidebar-overlay" in html
    assert "z-index:900" in html
