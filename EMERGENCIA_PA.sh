#!/bin/bash
# EMERGENCIA_PA.sh — Rodar no Bash do PythonAnywhere
# Substitui todos os arquivos Python diretamente do GitHub

set -e
cd ~/gado

echo "=== Sincronizando com GitHub ==="
git fetch origin main
git reset --hard origin/main
echo "✅ Reset completo para versão do GitHub"

echo ""
echo "=== Verificando arquivos críticos ==="
python3 -c "
import sys
sys.path.insert(0, '.')
try:
    from app import app
    rotas = list(app.url_map.iter_rules())
    print(f'✅ App OK — {len(rotas)} rotas registradas')
except Exception as e:
    print(f'❌ ERRO: {e}')
"

echo ""
echo "=== Criando pasta templates ==="
mkdir -p ~/gado/templates
cp ~/gado/*.html ~/gado/templates/ 2>/dev/null && echo "✅ Templates copiados" || echo "⚠️ Nenhum HTML na raiz"

echo ""
echo "✅ Pronto! Clique em RELOAD na aba Web do PythonAnywhere."
