@echo off
title Sistema de Gado v3.5 — Sitio Santo Antonio
echo ================================================
echo   SISTEMA DE GESTAO DE GADO v3.5 - WEB
echo   Sitio Santo Antonio - Geane, Deyvid, Nilson
echo ================================================
echo.
echo Verificando dependencias...
pip install flask ngrok pandas playwright pyinstaller openpyxl matplotlib reportlab requests numpy bcrypt beautifulsoup4 --quiet
echo.
echo Abrindo no navegador em http://localhost:5000
echo Para encerrar: feche esta janela ou pressione Ctrl+C
echo ================================================
python app.py
pause
