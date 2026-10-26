# -*- coding: utf-8 -*-

def test_animais_filtra_por_busca_e_categoria(cliente):
    r = cliente.get("/animais?q=A0001&categoria=Garrote")
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    assert 'name="q"' in html
    assert 'name="categoria"' in html
