#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
#  COLE ESTES COMANDOS NO CONSOLE DO PYTHONANYWHERE (um por vez)
#  Dashboard → Consoles → Bash
# ═══════════════════════════════════════════════════════════════════

cd ~/gado

# 1) Ver se há dados no stash (de antes do pull que sumiu tudo)
echo "=== Stash salvo ==="
git stash list

# 2) Tentar recuperar dados do stash
git stash pop

# 3) Ver backups disponíveis
echo "=== Backups disponíveis ==="
ls -lht ~/gado/backups/ | head -20

# 4) Se o xlsx ainda estiver vazio/errado, restaurar o backup mais recente:
# cp ~/gado/backups/$(ls -t ~/gado/backups/*.xlsx | head -1 | xargs basename) ~/gado/gado_familia.xlsx

# 5) Parar o Git de rastrear o xlsx para sempre
git rm --cached gado_familia.xlsx 2>/dev/null || true
git rm --cached usuarios.json 2>/dev/null || true
git rm --cached -r __pycache__/ 2>/dev/null || true

# 6) Renomear gitignore → .gitignore (o nome errado era o problema raiz!)
cp ~/gado/gitignore ~/gado/.gitignore

# 7) Confirmar que .gitignore está correto
echo "=== Conteúdo do .gitignore ==="
cat ~/gado/.gitignore

# 8) Commitar a correção
git add .gitignore
git commit -m "fix: renomear gitignore → .gitignore e parar de rastrear dados"
git push

# 9) Verificar que xlsx NÃO aparece mais no git status
echo "=== Git status (xlsx NAO deve aparecer) ==="
git status

echo "=== CONCLUÍDO — recarregue o web app ==="
