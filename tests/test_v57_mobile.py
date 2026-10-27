# -*- coding: utf-8 -*-
"""
Testes para v5.7 — integração incremental de Mobile Refinements, Dark Mode, Gestures
"""
import pytest
from flask import session


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


def test_main_pages_load(cliente):
    """Páginas principais carregam sem erro de 500"""
    pages = ["/", "/calendario", "/animais"]
    for page in pages:
        resp = cliente.get(page)
        assert resp.status_code in [200, 302, 401], f"Página {page} retornou erro: {resp.status_code}"


def test_css_files_exist():
    """Arquivos CSS v5.7 existem"""
    import os
    assert os.path.exists("F:\\programa sitio\\static\\css\\mobile.css"), "mobile.css não encontrado"
    assert os.path.exists("F:\\programa sitio\\static\\css\\dark-mode.css"), "dark-mode.css não encontrado"


def test_js_files_exist():
    """Arquivo JS v5.7 existe"""
    import os
    assert os.path.exists("F:\\programa sitio\\static\\js\\gestures.js"), "gestures.js não encontrado"


def test_base_html_includes_v57(cliente):
    """base.html inclui comentários v5.7"""
    with open("F:\\programa sitio\\templates\\base.html", encoding="utf-8") as f:
        html = f.read()
    assert 'v5.7' in html, "Comentários v5.7 não encontrados em base.html"

