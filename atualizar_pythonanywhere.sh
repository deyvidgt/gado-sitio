#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
#  atualizar_pythonanywhere.sh — Sítio Santo Antonio
#
#  USO: cole este script no console Bash do PythonAnywhere
#       e rode UMA VEZ para configurar tudo.
#       Nas próximas atualizações, use apenas: bash ~/atualizar.sh
#
#  O QUE FAZ:
#    1. Salva os dados (xlsx + usuarios.json) em ~/gado-dados/
#    2. Faz git pull com segurança (dados NÃO estão no repo)
#    3. Restaura os dados salvos
#    4. Corrige o .gitignore para nunca mais rastrear dados
# ═══════════════════════════════════════════════════════════════════

set -e  # parar em qualquer erro

REPO=~/gado
DADOS=~/gado-dados
DATA_ATUAL=$(date +"%Y%m%d_%H%M%S")

echo ""
echo "══════════════════════════════════════════════"
echo "  🐄 Atualizador Seguro — Sítio Santo Antonio"
echo "══════════════════════════════════════════════"
echo ""

# ── 1) Criar pasta de dados permanente (fora do repo) ────────────────
echo "📁 Criando pasta de dados permanente: $DADOS"
mkdir -p "$DADOS/backups"

# ── 2) Salvar dados atuais ────────────────────────────────────────────
echo ""
echo "💾 Salvando seus dados antes de atualizar..."

if [ -f "$REPO/gado_familia.xlsx" ]; then
    # Verificar se o arquivo tem dados (> 5KB)
    TAMANHO=$(stat -c%s "$REPO/gado_familia.xlsx" 2>/dev/null || echo 0)
    if [ "$TAMANHO" -gt 5000 ]; then
        cp "$REPO/gado_familia.xlsx" "$DADOS/gado_familia.xlsx"
        cp "$REPO/gado_familia.xlsx" "$DADOS/backups/backup_antes_update_${DATA_ATUAL}.xlsx"
        echo "   ✅ gado_familia.xlsx salvo ($TAMANHO bytes)"
    else
        echo "   ⚠️  gado_familia.xlsx muito pequeno ($TAMANHO bytes) — pode estar vazio"
        echo "      Procurando backup mais recente..."
        BACKUP_RECENTE=$(ls -t "$REPO/backups/"*.xlsx 2>/dev/null | head -1 || true)
        if [ -n "$BACKUP_RECENTE" ]; then
            cp "$BACKUP_RECENTE" "$DADOS/gado_familia.xlsx"
            echo "   ✅ Restaurado de backup: $(basename $BACKUP_RECENTE)"
        elif [ -f "$DADOS/gado_familia.xlsx" ]; then
            echo "   ✅ Usando versão salva anteriormente em $DADOS"
        else
            echo "   ❌ Nenhum dado encontrado para salvar!"
        fi
    fi
else
    echo "   ℹ️  gado_familia.xlsx não existe no repo (normal na primeira vez)"
fi

if [ -f "$REPO/usuarios.json" ]; then
    cp "$REPO/usuarios.json" "$DADOS/usuarios.json"
    echo "   ✅ usuarios.json salvo"
fi

# Copiar backups existentes para a pasta de dados
if [ -d "$REPO/backups" ] && [ "$(ls -A $REPO/backups/*.xlsx 2>/dev/null)" ]; then
    cp "$REPO/backups/"*.xlsx "$DADOS/backups/" 2>/dev/null || true
    echo "   ✅ Backups existentes copiados"
fi

# ── 3) Corrigir .gitignore ANTES do pull ─────────────────────────────
echo ""
echo "🔧 Corrigindo .gitignore..."

cd "$REPO"

# Remover o rastreamento dos arquivos de dados (sem apagar os arquivos)
git rm --cached gado_familia.xlsx 2>/dev/null && echo "   ✅ gado_familia.xlsx removido do Git" || echo "   ℹ️  gado_familia.xlsx já não estava no Git"
git rm --cached usuarios.json 2>/dev/null && echo "   ✅ usuarios.json removido do Git" || echo "   ℹ️  usuarios.json já não estava no Git"
git rm --cached -r backups/ 2>/dev/null && echo "   ✅ backups/ removido do Git" || echo "   ℹ️  backups/ já não estava no Git"
git rm --cached -r __pycache__/ 2>/dev/null || true

# Escrever .gitignore correto
cat > "$REPO/.gitignore" << 'GITIGNORE'
# ── Banco de dados e dados sensíveis ───────────────────
# NUNCA versionar — contém dados reais da família
gado_familia.xlsx
usuarios.json
backups/
*.bak
fotos/
relatorio_gado_*.xlsx

# ── Cache Python ────────────────────────────────────────
__pycache__/
*.py[cod]
*.pyo
*.pyc

# ── Ambiente virtual ────────────────────────────────────
.env
venv/
.venv/
*.egg-info/

# ── Build / compilação ──────────────────────────────────
dist/
build/
*.spec.bak
_internal/

# ── Sistema operacional ─────────────────────────────────
.DS_Store
Thumbs.db
desktop.ini

# ── Logs e temporários ──────────────────────────────────
*.log
*.tmp
GITIGNORE

echo "   ✅ .gitignore atualizado corretamente"

# Commitar a correção do .gitignore
git add .gitignore
git diff --staged --quiet || git commit -m "fix: .gitignore correto — dados nunca mais vão pro Git"
echo "   ✅ .gitignore commitado"

# ── 4) Fazer git pull com segurança ──────────────────────────────────
echo ""
echo "⬇️  Baixando atualização do código..."

git stash 2>/dev/null || true
git pull --rebase origin main

echo "   ✅ Código atualizado"

# ── 5) Restaurar dados ───────────────────────────────────────────────
echo ""
echo "♻️  Restaurando seus dados..."

if [ -f "$DADOS/gado_familia.xlsx" ]; then
    cp "$DADOS/gado_familia.xlsx" "$REPO/gado_familia.xlsx"
    TAMANHO=$(stat -c%s "$REPO/gado_familia.xlsx")
    echo "   ✅ gado_familia.xlsx restaurado ($TAMANHO bytes)"
fi

if [ -f "$DADOS/usuarios.json" ]; then
    cp "$DADOS/usuarios.json" "$REPO/usuarios.json"
    echo "   ✅ usuarios.json restaurado"
fi

mkdir -p "$REPO/backups"
if [ "$(ls -A $DADOS/backups/*.xlsx 2>/dev/null)" ]; then
    cp "$DADOS/backups/"*.xlsx "$REPO/backups/" 2>/dev/null || true
    echo "   ✅ Backups restaurados"
fi

# ── 6) Criar link simbólico para atualizações futuras ────────────────
echo ""
echo "🔗 Criando atalho para atualizações futuras..."

cat > ~/atualizar.sh << 'ATALHO'
#!/bin/bash
# Atualização rápida — Sítio Santo Antonio
# Uso: bash ~/atualizar.sh

REPO=~/gado
DADOS=~/gado-dados
DATA_ATUAL=$(date +"%Y%m%d_%H%M%S")

echo "🐄 Atualizando Sítio Santo Antonio..."

# Salvar dados
mkdir -p "$DADOS/backups"
[ -f "$REPO/gado_familia.xlsx" ] && cp "$REPO/gado_familia.xlsx" "$DADOS/gado_familia.xlsx" && echo "   💾 Dados salvos"
[ -f "$REPO/usuarios.json"    ] && cp "$REPO/usuarios.json"     "$DADOS/usuarios.json"     && echo "   💾 Usuários salvos"

# Atualizar código
cd "$REPO"
git pull origin main

# Restaurar dados
[ -f "$DADOS/gado_familia.xlsx" ] && cp "$DADOS/gado_familia.xlsx" "$REPO/gado_familia.xlsx" && echo "   ♻️  Dados restaurados"
[ -f "$DADOS/usuarios.json"    ] && cp "$DADOS/usuarios.json"     "$REPO/usuarios.json"     && echo "   ♻️  Usuários restaurados"

echo "✅ Pronto! Recarregue o Web App no painel do PythonAnywhere."
ATALHO

chmod +x ~/atualizar.sh
echo "   ✅ Atalho criado: ~/atualizar.sh"

# ── 7) Verificar integridade ─────────────────────────────────────────
echo ""
echo "🔍 Verificando integridade..."

if [ -f "$REPO/gado_familia.xlsx" ]; then
    TAMANHO=$(stat -c%s "$REPO/gado_familia.xlsx")
    if [ "$TAMANHO" -gt 5000 ]; then
        echo "   ✅ gado_familia.xlsx OK ($TAMANHO bytes)"
    else
        echo "   ⚠️  gado_familia.xlsx muito pequeno — verifique os dados"
    fi
else
    echo "   ℹ️  gado_familia.xlsx não existe — será criado no primeiro acesso"
fi

echo ""
echo "══════════════════════════════════════════════"
echo "  ✅ ATUALIZAÇÃO CONCLUÍDA COM SUCESSO!"
echo ""
echo "  Próximo passo: recarregue o Web App"
echo "  PythonAnywhere → Web → Reload"
echo ""
echo "  Nas próximas atualizações, use apenas:"
echo "    bash ~/atualizar.sh"
echo "══════════════════════════════════════════════"
echo ""
