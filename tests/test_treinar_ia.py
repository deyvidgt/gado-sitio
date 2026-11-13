#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_treinar_ia.py — Teste para a rota de treino de IA
"""
import pytest


def test_treinar_ia_rota(cliente):
    """Testa se a rota /admin/treinar-ia lida com autenticação e exceções sem crashar (Erro 500)."""
    res = cliente.post("/admin/treinar-ia")
    # Sem estar logado como admin, deve retornar 302 (redirect para login) ou 403 (forbidden)
    assert res.status_code in (302, 403)
