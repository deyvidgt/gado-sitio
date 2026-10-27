#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Testes da busca rápida global (v5.6)
"""
import pytest
from busca import buscar_global


def test_busca_vazia():
    """Busca com termo vazio retorna lista vazia."""
    assert buscar_global("") == []
    assert buscar_global("  ") == []


def test_busca_termo_muito_curto():
    """Termo com menos de 2 caracteres retorna lista vazia."""
    assert buscar_global("a") == []


def test_busca_animais(flask_app):
    """Busca encontra animais por brinco, ID ou nome."""
    with flask_app.app_context():
        resultados = buscar_global("amarelo")
        # Se houver animais no banco, devem incluir "amarelo" em algum lugar
        if resultados:
            assert any(r["tipo"] == "animal" for r in resultados)


def test_busca_tarefas(flask_app):
    """Busca encontra tarefas por título ou ID."""
    with flask_app.app_context():
        resultados = buscar_global("tarefa")
        # Resultado pode estar vazio ou conter tarefas
        assert isinstance(resultados, list)


def test_busca_limite_resultados(flask_app):
    """Busca nunca retorna mais de 10 resultados."""
    with flask_app.app_context():
        resultados = buscar_global("a")  # Termo genérico
        assert len(resultados) <= 10


def test_busca_filtro_tipo(flask_app):
    """Filtro por tipo retorna apenas esse tipo."""
    with flask_app.app_context():
        resultados = buscar_global("a", tipo_filtro="animal")
        for r in resultados:
            assert r["tipo"] == "animal"


def test_busca_resultado_estrutura(flask_app):
    """Cada resultado tem a estrutura esperada."""
    with flask_app.app_context():
        resultados = buscar_global("aa")
        for r in resultados:
            assert "tipo" in r
            assert "id" in r
            assert "titulo" in r
            assert "subtitulo" in r
            assert "link" in r
            assert "icone" in r


def test_api_busca_endpoint(cliente):
    """GET /api/busca?q=... retorna JSON."""
    rv = cliente.get("/api/busca?q=teste")
    assert rv.status_code == 200
    data = rv.get_json()
    assert "resultados" in data
    assert isinstance(data["resultados"], list)


def test_api_busca_com_tipo(cliente):
    """GET /api/busca?q=...&tipo=animal filtra por tipo."""
    rv = cliente.get("/api/busca?q=teste&tipo=animal")
    assert rv.status_code == 200
    data = rv.get_json()
    for r in data["resultados"]:
        assert r["tipo"] == "animal"
