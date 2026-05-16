@echo off
title Sistema de Gado v3.0 — Sitio Santo Antonio
echo ================================================
echo   SISTEMA DE GESTAO DE GADO v3.0 - WEB
echo   Sitio Santo Antonio - Geane, Deyvid, Nilson
echo ================================================
echo.
echo Verificando dependencias...
pip install flask pandas openpyxl matplotlib requests --quiet
echo.
echo Abrindo no navegador em http://localhost:5000
echo Para encerrar: feche esta janela ou pressione Ctrl+C
echo ================================================
python app.py
pause
