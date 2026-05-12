#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ponto de entrada WSGI para PythonAnywhere.
Este arquivo é referenciado na configuração do Web App no painel do site.
"""

import sys, os

# Adiciona a pasta do projeto ao path do Python
# Altere o caminho abaixo para o seu usuário do PythonAnywhere:
# /home/SEU_USUARIO/gado/
PASTA_PROJETO = os.path.dirname(os.path.abspath(__file__))
if PASTA_PROJETO not in sys.path:
    sys.path.insert(0, PASTA_PROJETO)

from app import app as application  # noqa: F401
