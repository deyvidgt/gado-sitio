@echo off
title Compilando Sistema de Gado...
echo ================================================
echo   COMPILADOR - Sistema de Gado v3.1
echo   Sitio Santo Antonio
echo ================================================
echo.

echo [1/4] Instalando dependencias de compilacao...
pip install pyinstaller flask pandas openpyxl ngrok requests beautifulsoup4 playwright pillow --quiet
echo       OK
echo.

echo [2/4] Verificando icone...
if exist "static\favicon.ico" (
    echo       Icone encontrado: static\favicon.ico
) else (
    echo       AVISO: static\favicon.ico nao encontrado.
    echo       O .exe sera gerado sem icone personalizado.
)
echo.

echo [3/4] Compilando o programa...
echo       (isso pode levar 2 a 5 minutos, aguarde)
echo.
pyinstaller gado.spec --clean --noconfirm
echo.

echo [4/4] Finalizando...
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
