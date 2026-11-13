#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_curral.py — Testes para Manejos de Curral e Apontamentos Rápidos
"""
import pytest
import pandas as pd


def test_curral_rotas_carregam(cliente):
    """Testa se as páginas do painel de curral e formulários respondem corretamente."""
    res = cliente.get("/curral")
    assert res.status_code in (200, 302)

    res_pesagem = cliente.get("/curral/pesagem")
    assert res_pesagem.status_code in (200, 302)

    res_sanitario = cliente.get("/curral/sanitario")
    assert res_sanitario.status_code in (200, 302)

    res_morte = cliente.get("/curral/mortalidade")
    assert res_morte.status_code in (200, 302)

    res_nasc = cliente.get("/curral/nascimento")
    assert res_nasc.status_code in (200, 302)

    res_troca = cliente.get("/curral/troca-lote")
    assert res_troca.status_code in (200, 302)
