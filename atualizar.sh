#!/bin/bash
# atualizar.sh — Sítio Santo Antonio
# Executar no PythonAnywhere após git pull:
#   cd ~/gado && git pull && bash ~/atualizar.sh
# Ou colocar em ~/atualizar.sh

PASTA_GADO=~/gado

echo "=== Atualizando Sistema de Gado ==="

# Criar pasta templates se não existir
mkdir -p "$PASTA_GADO/templates"

# Mover HTMLs da raiz para templates/
for html in "$PASTA_GADO"/*.html; do
    [ -f "$html" ] && cp "$html" "$PASTA_GADO/templates/"
done
echo "✅ Templates copiados para $PASTA_GADO/templates/"

# Criar pasta static se não existir
mkdir -p "$PASTA_GADO/static"

# Garantir que sw.js e manifest.json estão acessíveis
[ -f "$PASTA_GADO/sw.js" ]       && cp "$PASTA_GADO/sw.js"       "$PASTA_GADO/static/" 2>/dev/null || true
[ -f "$PASTA_GADO/manifest.json" ] && cp "$PASTA_GADO/manifest.json" "$PASTA_GADO/static/" 2>/dev/null || true

echo "✅ Static atualizado"
echo ""
echo "Agora clique em Reload na aba Web do PythonAnywhere."
