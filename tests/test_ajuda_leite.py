# -*- coding: utf-8 -*-


def test_ajuda_tem_secao_leiteira(cliente):
    html = cliente.get("/ajuda").get_data(as_text=True)
    assert 'id="leite"' in html and 'href="#leite"' in html
    for texto in ("Lançar uma ordenha", "não informado", "Individual", "Total",
                  "colchão", "carência"):
        assert texto in html
