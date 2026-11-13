#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_simulador_engorda.py — Testes para o Simulador de Custo de Produção e Viabilidade de Engorda (v5.35)
"""
import pytest


def test_simulador_engorda_rota(cliente):
    """Testa se a página do simulador de engorda responde com sucesso."""
    assert cliente.get("/pecuaria/simulador-engorda").status_code in (200, 302)
