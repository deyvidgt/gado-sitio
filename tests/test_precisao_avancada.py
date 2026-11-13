#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_precisao_avancada.py — Testes para os módulos avançados de rebanho e curral (v5.40)
"""
import pytest


def test_rotas_precisao_avancada(cliente):
    """Testa se as rotas avançadas respondem com sucesso."""
    assert cliente.get("/curral/manejo").status_code in (200, 302)
    assert cliente.get("/animais/estoque-peso").status_code in (200, 302)
    assert cliente.get("/relatorios/mortalidade-vendas").status_code in (200, 302)
