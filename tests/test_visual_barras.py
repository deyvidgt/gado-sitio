# -*- coding: utf-8 -*-
"""Barras e semáforos (v5.3): a largura tem que ficar entre 0% e 100%."""
import re

PAGINAS = ["/", "/pastos", "/tarefas"]


def _larguras(html):
    return [int(x) for x in re.findall(r'<i style="width:(\d+)%', html)]


def test_barras_nao_estouram_nem_quebram(cliente):
    for rota in PAGINAS:
        r = cliente.get(rota)
        assert r.status_code == 200, rota
        html = r.get_data(as_text=True)
        assert all(0 <= p <= 100 for p in _larguras(html)), rota


def test_semaforo_sempre_tem_palavra_junto_da_cor(cliente):
    """Sol forte e daltonismo: cor sozinha não informa nada."""
    html = cliente.get("/pastos").get_data(as_text=True)
    for etiqueta in re.findall(r'class="badge badge-\w+"[^>]*>([^<]*)<', html):
        assert etiqueta.strip(), "etiqueta de semáforo sem texto"
