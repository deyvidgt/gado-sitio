# Deploy v5.8.0 no PythonAnywhere

## Passo 1: Atualizar código no servidor

```bash
# SSH no PythonAnywhere (user: deyvidgt)
cd ~/gado
git pull origin main
```

## Passo 2: Reiniciar a app

No painel do PythonAnywhere:
1. Ir para **Web** → **Reload [timestamp]**
2. Ou via console: `mkvirtualenv --python=/usr/bin/python3.10 gado && pip install -r requirements.txt`

## Passo 3: Testar as rotas novas

```
GET  http://seu-dominio/api/pastos/animais        → Lista animais por pasto
GET  http://seu-dominio/api/alertas/count         → Contagem de alertas
GET  http://seu-dominio/api/tarefas/pendentes-count → Tarefas pendentes
GET  http://seu-dominio/animais/<id>/historico-peso → Gráfico de peso
```

## Passo 4: Verificar logs

```bash
tail -f ~/gado/gado-família.log
# ou
tail -f /var/log/pa_deyvidgt_pythonanywhere_com_wsgi.log
```

## Mudanças em v5.8.0

### Novas Features
- 🗺️ Animais no mapa (pastos.py: `animais_por_pasto()`)
- 🤰 Vacas prenhas no painel (routes_dashboard.py: `_vacas_prenhas()`)
- 📈 Gráfico BCS×Peso (bcs.py: novo módulo)
- 🐄 Planejamento de IA (reproducao.py: `planejamento_ia()`)
- 📊 Histórico de peso (routes_animais.py: `/animais/<id>/historico-peso`)

### Melhorias
- peso_foto.py: +historico_estimativas(), comparar_estimativa_vs_balanca()
- pastos.py: +animais_por_pasto() para rastreamento
- routes_dashboard.py: +import jsonify (fix)

### Bugs Corrigidos
- ✅ Route 'painel' → 'dashboard' (test fix)
- ✅ Falta jsonify import em routes_dashboard.py
- ✅ Pasta backups na raiz removida

## Rollback (se necessário)

```bash
cd ~/gado
git revert HEAD
git push origin main
# Reload no PythonAnywhere
```

## Status do Deploy

| Item | Status |
|------|--------|
| Código | ✅ Pronto (main branch) |
| Testes | ✅ 760 passed (local) |
| DB | ✅ Compatível (sem mudanças de schema) |
| Assets | ✅ CSS/JS novos linkados |

---

**Versão:** v5.8.0  
**Data:** 2026-10-27  
**Autor:** Claude Code
