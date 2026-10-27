# -*- coding: utf-8 -*-
"""Testes da rota do calculador de ração."""

import pytest
from app import app


@pytest.fixture
def client():
    """Cliente Flask para testes."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        # Login
        client.post('/login', data={'login': 'deyvid', 'senha': 'sitio2025'})
        yield client


def test_get_calculador_leite(client):
    """GET /leite/calculador deve renderizar o formulário."""
    resp = client.get('/leite/calculador', follow_redirects=True)
    assert resp.status_code == 200
    # Verifica se o template foi renderizado (não é erro 404/500)
    assert b'form' in resp.data or b'Calcula' in resp.data
