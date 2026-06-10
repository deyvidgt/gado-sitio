@echo off
title Compilando Sistema de Gado...
echo ================================================
echo   COMPILADOR — Sistema de Gado v3.5
echo   Sitio Santo Antonio
echo ================================================
echo.
echo [1/3] Instalando dependencias de compilacao...
pip install pyinstaller flask pandas openpyxl requests beautifulsoup4 --quiet
echo.
echo [2/3] Compilando o programa...
echo       (isso pode levar 2 a 5 minutos, aguarde)
echo.
pyinstaller gado.spec --clean --noconfirm
echo.
echo [3/3] Finalizando...

if exist "dist\GadoSitioSantoAntonio\GadoSitioSantoAntonio.exe" (
    echo.
    echo ================================================
    echo   COMPILACAO CONCLUIDA COM SUCESSO!
    echo.
    echo   O programa esta em:
    echo   dist\GadoSitioSantoAntonio\
    echo.
    echo   Para distribuir: copie a pasta inteira
    echo   "GadoSitioSantoAntonio" para outro computador.
    echo   Nao precisa de Python instalado para rodar.
    echo ================================================
    echo.
    echo Abrindo a pasta com o executavel...
    explorer dist\GadoSitioSantoAntonio
) else (
    echo.
    echo ================================================
    echo   ERRO NA COMPILACAO
    echo   Verifique as mensagens acima.
    echo ================================================
)
pause
