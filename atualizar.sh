#!/bin/bash
# atualizar.sh — Sítio Santo Antonio
# Salvar em ~/atualizar.sh (pasta home do usuário)
# 
# Como usar - no PythonAnywhere Bash:
#   cd ~/gado && git pull && bash ~/atualizar.sh
#
# Depois clicar em Reload na aba Web

# Detectar pasta do projeto automaticamente
if [ -f ~/gado/app.py ]; then
    PASTA_GADO=~/gado
elif [ -f ~/gado-sitio/app.py ]; then
    PASTA_GADO=~/gado-sitio
else
    PASTA_GADO=$(dirname "$(readlink -f "$0")")
fi

echo "=== Atualizando Sistema de Gado ==="
echo "📂 Pasta do projeto: $PASTA_GADO"

# 1) Templates vêm só do Git (pasta templates/). ANTES este passo copiava qualquer
#    .html da raiz POR CIMA de templates/ — um HTML velho esquecido na raiz
#    desfazia correções de tela a cada atualização. Agora só avisa.
if ls "$PASTA_GADO"/*.html >/dev/null 2>&1; then
    echo "⚠️  HTML antigo na raiz do projeto (não é usado — pode apagar):"
    ls "$PASTA_GADO"/*.html
fi

# 2) Pasta static/ (ícones) — sw.js e manifest.json são servidos direto da raiz.
mkdir -p "$PASTA_GADO/static"

# 4) Garantir que gado-dados/ existe (pasta de dados fora do repo)
mkdir -p ~/gado-dados/backups
echo "✅ ~/gado-dados/ verificado"

# 5) Verificar se o Excel de dados existe
if [ -f ~/gado-dados/gado_familia.xlsx ]; then
    echo "✅ gado_familia.xlsx encontrado em ~/gado-dados/"
elif [ -f "$PASTA_GADO/gado_familia.xlsx" ]; then
    echo "⚠️  Movendo gado_familia.xlsx para ~/gado-dados/ (fora do repo)..."
    cp "$PASTA_GADO/gado_familia.xlsx" ~/gado-dados/
    echo "✅ Dados movidos para ~/gado-dados/gado_familia.xlsx"
else
    echo "ℹ️  Nenhum gado_familia.xlsx encontrado - será criado no primeiro acesso"
fi

# 6) Verificar requirements
echo ""
echo "📦 Verificando dependências..."
pip install -q flask pandas openpyxl numpy bcrypt requests 2>/dev/null && \
    echo "✅ Dependências OK"

# 7) Testes automáticos — rodam numa CÓPIA temporária dos dados (nunca no arquivo real)
echo ""
echo "🧪 Rodando os testes..."
pip install -q pytest 2>/dev/null
if (cd "$PASTA_GADO" && python3 -m pytest -q 2>&1 | tail -3); then
    if (cd "$PASTA_GADO" && python3 -m pytest -q >/dev/null 2>&1); then
        echo "✅ Todos os testes passaram"
    else
        echo "❌ ATENÇÃO: algum teste falhou — NÃO dê Reload; veja a saída acima"
    fi
fi

# 8) Tarefas agendadas (Dashboard → Tasks) que devem existir:
echo ""
echo "📅 Confira em Tasks do PythonAnywhere (uma vez só):"
echo "   python3 $PASTA_GADO/backup_automatico.py   (diário 03:00)"
echo "   python3 $PASTA_GADO/alertas_whatsapp.py    (diário 07:00)"
echo "   python3 $PASTA_GADO/resumo_mensal.py       (diário 08:00 — só envia no dia 1º)"

echo ""
echo "================================================"
echo "✅ Atualização concluída!"
echo "👉 Agora clique em RELOAD na aba Web do PythonAnywhere"
echo "================================================"
