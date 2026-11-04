# -*- coding: utf-8 -*-
"""
Testes para v5.7 — integração incremental de Mobile Refinements, Dark Mode, Gestures
"""
import os

import pytest
from flask import session

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_mobile_css_loaded(cliente):
    """CSS mobile v5.7 é carregado na base"""
    resp = cliente.get("/")
    assert resp.status_code == 200
    html = resp.data.decode('utf-8')
    assert 'mobile.css' in html


def test_gestures_js_loaded(cliente):
    """JavaScript de gestos v5.7 é carregado na base"""
    resp = cliente.get("/")
    assert resp.status_code == 200
    html = resp.data.decode('utf-8')
    assert 'gestures.js' in html


def test_dark_mode_css_loaded(cliente):
    """CSS dark mode v5.7 é carregado na base"""
    resp = cliente.get("/")
    assert resp.status_code == 200
    html = resp.data.decode('utf-8')
    assert 'dark-mode.css' in html


def test_dark_mode_theme_script(cliente):
    """Script de tema escuro está na página"""
    resp = cliente.get("/")
    assert resp.status_code == 200
    html = resp.data.decode('utf-8')
    assert 'gado-theme' in html or 'data-theme' in html


def test_theme_toggle_exists(cliente):
    """Toggle de tema existe na sidebar (elemento original)"""
    resp = cliente.get("/")
    assert resp.status_code == 200
    html = resp.data.decode('utf-8')
    assert 'theme-chk' in html and 'theme-label' in html


@pytest.mark.parametrize("rota", ["/", "/voz", "/ajuda", "/leite"])
def test_tema_global_disponivel_em_todas_as_pagina_principais(cliente, rota):
    resposta = cliente.get(rota)
    html = resposta.get_data(as_text=True)

    assert resposta.status_code == 200
    assert 'id="theme-btn"' in html
    assert 'data-theme="light"' in html
    assert "dark-mode.css" in html


def test_ajuda_documenta_tema_global_e_permissoes_de_voz(cliente):
    html = cliente.get("/ajuda").get_data(as_text=True)

    assert "A escolha vale para todas as páginas" in html
    assert "permita o acesso ao microfone" in html
    assert "use o microfone do teclado" in html


def test_ajuda_documenta_paineis_atualizados(cliente):
    html = cliente.get("/ajuda").get_data(as_text=True)

    assert "Atalhos do leite" in html
    assert "Fluxo Animais" in html
    assert "saldo acumulado" in html
    assert "Misto" in html
    assert "0,0" in html
    assert "Registrar Novo Tratamento" in html


def test_ponte_de_tema_preserva_cores_dos_botoes_e_tokens_legados():
    import os

    caminho = os.path.join(RAIZ, "static", "css", "dark-mode.css")
    with open(caminho, encoding="utf-8") as arquivo:
        css = arquivo.read()

    assert "--surface-1: var(--surface)" in css
    assert "--border: var(--bg-2)" in css
    assert "button {" not in css


def test_main_pages_load(cliente):
    """Páginas principais carregam sem erro de 500"""
    pages = ["/", "/calendario", "/animais"]
    for page in pages:
        resp = cliente.get(page)
        assert resp.status_code in [200, 302, 401], f"Página {page} retornou erro: {resp.status_code}"


def test_css_files_exist():
    """Arquivos CSS v5.7 existem"""
    import os
    assert os.path.exists(os.path.join(RAIZ, "static", "css", "mobile.css")), "mobile.css não encontrado"
    assert os.path.exists(os.path.join(RAIZ, "static", "css", "dark-mode.css")), "dark-mode.css não encontrado"


def test_js_files_exist():
    """Arquivo JS v5.7 existe"""
    import os
    assert os.path.exists(os.path.join(RAIZ, "static", "js", "gestures.js")), "gestures.js não encontrado"


def test_base_html_includes_v57(cliente):
    """base.html inclui comentários v5.7"""
    with open(os.path.join(RAIZ, "templates", "base.html"), encoding="utf-8") as f:
        html = f.read()
    assert 'v5.7' in html, "Comentários v5.7 não encontrados em base.html"
