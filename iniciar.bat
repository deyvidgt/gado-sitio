@echo off
title Sistema de Gado v3.1 — Sitio Santo Antonio
echo ================================================
echo   SISTEMA DE GESTAO DE GADO v3.1 - WEB
echo   Sitio Santo Antonio - Geane, Deyvid, Nilson
echo ================================================
echo.
echo Verificando dependencias...
pip install flask pandas ngrok openpyxl matplotlib requests beautifulsoup4 playwright --quiet
echo.
echo Verificando navegador para cotacoes IMEA...
python -m playwright install chromium --quiet 2>nul
echo.
echo Abrindo no navegador em http://localhost:5000
echo Para encerrar: feche esta janela ou pressione Ctrl+C
echo ================================================
python app.py
pause
