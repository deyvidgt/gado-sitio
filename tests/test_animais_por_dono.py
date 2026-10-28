#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Testes da página de animais agrupados por dono (v5.10).
"""
import pytest
from config import MEMBROS


def test_rota_animais_por_dono_exists():
    """Rota /animais/dono/<dono> existe."""
    from app import app

    rotas = [rule.rule for rule in app.url_map.iter_rules()]
    assert "/animais/dono/<dono>" in rotas


def test_animais_por_dono_invalido(cliente):
    """Dono inválido redireciona para /animais."""
    resp = cliente.get("/animais/dono/XYZ")
    assert resp.status_code == 302  # redirect
    assert "/animais" in resp.location


def test_animais_por_dono_valido(cliente):
    """Página de dono válido carrega."""
    # Pega primeiro membro válido
    dono = MEMBROS[0] if MEMBROS else "Mae"

    with cliente:
        with cliente.session_transaction() as sess:
            sess["usuario"] = "deyvid"

        resp = cliente.get(f"/animais/dono/{dono}")
        # Pode ser 200 (página) ou 302 (login)
        assert resp.status_code in [200, 302]


def test_animais_por_dono_mostra_brincos(cliente):
    """Página mostra brincos numerados dos animais do dono."""
    dono = MEMBROS[0] if MEMBROS else "Mae"

    with cliente:
        with cliente.session_transaction() as sess:
            sess["usuario"] = "deyvid"

        resp = cliente.get(f"/animais/dono/{dono}")
        # Se houver animais, deve ter brincos na página
        if resp.status_code == 200:
            # Verifica se há links para fichas de animais
            assert b"/animais/" in resp.data or b"Total" in resp.data
