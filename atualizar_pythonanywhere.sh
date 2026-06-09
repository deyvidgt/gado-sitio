#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
#  atualizar_pythonanywhere.sh — Sítio Santo Antonio (versão corrigida)
# ═══════════════════════════════════════════════════════════════════

REPO=~/gado
DADOS=~/gado-dados
DATA_ATUAL=$(date +"%Y%m%d_%H%M%S")

echo ""
echo "══════════════════════════════════════════════"
echo "  🐄 Atualizador Seguro — Sítio Santo Antonio"
echo "══════════════════════════════════════════════"
echo ""

mkdir -p "$DADOS/backups"
echo "📁 Pasta de dados: $DADOS"

# ── 2) Salvar dados atuais ────────────────────────────────────────────
echo ""
echo "💾 Salvando seus dados..."

if [ -f "$REPO/gado_familia.xlsx" ]; then
    TAMANHO=$(stat -c%s "$REPO/gado_familia.xlsx" 2>/dev/null || echo 0)
    if [ "$TAMANHO" -gt 5000 ]; then
        cp "$REPO/gado_familia.xlsx" "$DADOS/gado_familia.xlsx"
        cp "$REPO/gado_familia.xlsx" "$DADOS/backups/backup_antes_update_${DATA_ATUAL}.xlsx"
        echo "   ✅ gado_familia.xlsx salvo ($TAMANHO bytes)"
    else
        echo "   ⚠️  xlsx muito pequeno — usando versão salva anteriormente"
    fi
fi

if [ -f "$REPO/usuarios.json" ]; then
    cp "$REPO/usuarios.json" "$DADOS/usuarios.json"
    echo "   ✅ usuarios.json salvo"
fi

if ls "$REPO/backups/"*.xlsx 2>/dev/null 1>/dev/null; then
    cp "$REPO/backups/"*.xlsx "$DADOS/backups/" 2>/dev/null || true
    echo "   ✅ Backups copiados"
fi

# ── 3) Configurar Git e corrigir .gitignore ───────────────────────────
echo ""
echo "🔧 Corrigindo Git..."

cd "$REPO"

# Configurar identidade (necessário para commit)
git config user.email "sitio@santantonio.local"
git config user.name "Sitio Santo Antonio"

# Remover rastreamento dos arquivos de dados
git rm --cached gado_familia.xlsx 2>/dev/null || true
git rm --cached usuarios.json 2>/dev/null || true
git rm --cached -r backups/ 2>/dev/null || true
git rm --cached -r __pycache__/ 2>/dev/null || true

# Escrever .gitignore correto
cat > "$REPO/.gitignore" << 'GITIGNORE'
# Dados — ficam em ~/gado-dados/, FORA do repositório
gado_familia.xlsx
usuarios.json
backups/
*.bak
fotos/
relatorio_gado_*.xlsx

# Cache Python
__pycache__/
*.py[cod]
*.pyo
*.pyc

# Ambiente virtual
.env
venv/
.venv/
*.egg-info/

# Build
dist/
build/
*.spec.bak
_internal/

# Sistema operacional
.DS_Store
Thumbs.db
desktop.ini

# Logs
*.log
*.tmp
GITIGNORE

git add .gitignore

if git diff --staged --quiet; then
    echo "   ℹ️  .gitignore já correto"
else
    git commit -m "fix: .gitignore correto — dados nao vao mais pro Git"
    git push origin main 2>/dev/null && echo "   ✅ Push feito" || echo "   ⚠️  Push falhou (nao critico)"
fi

echo "   ✅ Git corrigido"

# ── 4) Git pull ───────────────────────────────────────────────────────
echo ""
echo "⬇️  Baixando código atualizado..."
git pull origin main 2>/dev/null || echo "   ℹ️  Sem novidades"

# ── 5) Restaurar dados ────────────────────────────────────────────────
echo ""
echo "♻️  Restaurando dados..."

if [ -f "$DADOS/gado_familia.xlsx" ]; then
    cp "$DADOS/gado_familia.xlsx" "$REPO/gado_familia.xlsx"
    echo "   ✅ gado_familia.xlsx restaurado"
fi

if [ -f "$DADOS/usuarios.json" ]; then
    cp "$DADOS/usuarios.json" "$REPO/usuarios.json"
    echo "   ✅ usuarios.json restaurado"
fi

mkdir -p "$REPO/backups"
if ls "$DADOS/backups/"*.xlsx 2>/dev/null 1>/dev/null; then
    cp "$DADOS/backups/"*.xlsx "$REPO/backups/" 2>/dev/null || true
    echo "   ✅ Backups restaurados"
fi

# ── 6) Criar atalho ~/atualizar.sh ───────────────────────────────────
cat > ~/atualizar.sh << 'ATALHO'
#!/bin/bash
REPO=~/gado
DADOS=~/gado-dados
echo ""
echo "🐄 Atualizando Sítio Santo Antonio..."
echo ""
mkdir -p "$DADOS/backups"

if [ -f "$REPO/gado_familia.xlsx" ]; then
    TAMANHO=$(stat -c%s "$REPO/gado_familia.xlsx" 2>/dev/null || echo 0)
    if [ "$TAMANHO" -gt 5000 ]; then
        cp "$REPO/gado_familia.xlsx" "$DADOS/gado_familia.xlsx"
        DATA_ATUAL=$(date +"%Y%m%d_%H%M%S")
        cp "$REPO/gado_familia.xlsx" "$DADOS/backups/backup_antes_update_${DATA_ATUAL}.xlsx"
        echo "   💾 Dados salvos ($TAMANHO bytes)"
    fi
fi
[ -f "$REPO/usuarios.json" ] && cp "$REPO/usuarios.json" "$DADOS/usuarios.json" && echo "   💾 Usuários salvos"

cd "$REPO"
git pull origin main
echo "   ✅ Código atualizado"

[ -f "$DADOS/gado_familia.xlsx" ] && cp "$DADOS/gado_familia.xlsx" "$REPO/gado_familia.xlsx" && echo "   ♻️  Dados restaurados"
[ -f "$DADOS/usuarios.json"    ] && cp "$DADOS/usuarios.json"     "$REPO/usuarios.json"     && echo "   ♻️  Usuários restaurados"

echo ""
echo "✅ Pronto! Clique em Reload no painel Web do PythonAnywhere."
echo ""
ATALHO

chmod +x ~/atualizar.sh

echo ""
echo "══════════════════════════════════════════════"
echo "  ✅ CONCLUÍDO!"
echo ""
echo "  Dados protegidos em: $DADOS/gado_familia.xlsx"
echo ""
echo "  Próximas atualizações:"
echo "    bash ~/atualizar.sh"
echo ""
echo "  Agora clique em Reload no painel Web."
echo "══════════════════════════════════════════════"
echo ""
