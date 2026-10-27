# CI/CD Setup — GitHub Actions

**Data:** 2026-10-27  
**Status:** Configuração completa para automação de testes

---

## 📋 O Que Foi Configurado

### 1. **GitHub Actions Workflow** (`.github/workflows/tests.yml`)

Executa automaticamente em cada `push` para `main`/`develop` e em **pull requests**:

#### Job 1: **Tests** (Multiplos Python versions)
- ✅ Python 3.10, 3.11, 3.12 (matrix strategy)
- ✅ Linting com `flake8`
- ✅ Type checking com `mypy`
- ✅ Testes com `pytest` + cobertura (`pytest-cov`)
- ✅ Upload de coverage para Codecov
- ✅ Cache de dependências (pip)
- ✅ Execução paralela de testes (`pytest-xdist`)

#### Job 2: **Security**
- ✅ Bandit: scan de segurança (bancos de dados, SQL injection, etc)
- ✅ Safety: check de vulnerabilidades conhecidas em dependências

#### Job 3: **Lighthouse** (Performance & Accessibility)
- ✅ Lighthouse CI: mede performance, acessibilidade, SEO
- ✅ Score mínimo: 80 (performance), 90 (accessibility)
- ✅ Testa 4 rotas principais

#### Job 4: **Build**
- ✅ Buildagem de pacote Python (wheel + sdist)
- ✅ Upload de artifacts para download

#### Job 5: **Notify**
- ✅ Comenta em PR com resumo de checks

---

## 🚀 Como Usar

### Primeiro Push
Após fazer commit e push para `main`:

```bash
git push origin main
```

Você verá na aba "Actions" do GitHub um run em progresso:
- 🟡 → 🟢 Se tudo passar
- 🟡 → 🔴 Se algum teste falhar

### Conferir Relatório
1. Vá para **GitHub** → Seu repo → **Actions**
2. Clique no último run
3. Veja os detalhes de cada job

### Pull Requests
Quando abrir um PR, o workflow roda automaticamente:
- ✅ Se **PASSED**: você vê ✅ e pode fazer merge
- ❌ Se **FAILED**: fix os erros locais e faça push novamente

### Ciclo Típico
```
1. Você mexe no código localmente
2. Roda `pytest tests/` localmente para validar
3. Faz push para `main` ou abre PR
4. GitHub Actions roda automaticamente
5. Você vê os resultados em GitHub
6. Se passou: aprova / faz merge
7. Se falhou: vê os logs, corrige, faz push novamente
```

---

## 📊 Métricas e Relatórios

### Coverage (Codecov)
- Badges automáticas no README
- Histórico de coverage ao longo do tempo
- Relatórios em PR mostrando mudanças

**Como ativar:**
1. Vá para https://codecov.io
2. Faça login com GitHub
3. Autorize o repo
4. Automaticamente o workflow faz upload

### Lighthouse
- Scores salvos em storage público (temporário)
- Link na aba "Lighthouse" do Actions
- Baixe JSON para analisar detalhes

### Performance
- Testes rodando **em paralelo** com `pytest-xdist`
- Duração total: ~5-10 minutos (dependendo de quantos tests)

---

## 🔧 Customizações Possíveis

### Adicionar mais Python versions
No arquivo `.github/workflows/tests.yml`:
```yaml
matrix:
  python-version: ['3.10', '3.11', '3.12']  # ← adicione versão
```

### Rodar apenas em branches específicas
```yaml
on:
  push:
    branches: [ main, develop, 'feature/*' ]
```

### Notificações via Slack/Email
Adicionar step final:
```yaml
- name: Notify Slack
  uses: slackapi/slack-github-action@v1
  with:
    webhook-url: ${{ secrets.SLACK_WEBHOOK }}
```

### Coverage mínimo obrigatório
```yaml
- name: Check coverage
  run: |
    pytest tests/ --cov=. --cov-fail-under=80
```

---

## 📚 Arquivos Adicionados

```
.github/workflows/tests.yml    # Workflow principal
lighthouserc.json              # Config do Lighthouse CI
docs/CI_CD_SETUP.md            # Este arquivo
```

---

## ✅ Checklist

- [x] GitHub Actions workflow criado
- [x] Testes em 3 versões Python
- [x] Linting (flake8) + Type checking (mypy)
- [x] Coverage com upload para Codecov
- [x] Security scan (Bandit + Safety)
- [x] Lighthouse CI para performance
- [x] Build de package
- [x] Notificação em PRs

---

## 🚨 Troubleshooting

### "Workflow failing on Ubuntu but passing locally"
- Diferença de SO: Linux vs Windows
- **Solução:** Teste em Linux ou use WSL localmente

### "Codecov upload fails"
- Falta autorizar repo no Codecov
- **Solução:** Vá para codecov.io, autorize GitHub

### "Lighthouse CI timeout"
- App levando tempo para iniciar
- **Solução:** Aumentar `sleep 5` para `sleep 10`

### "Type errors em mypy"
- `mypy` é rigoroso, temos `continue-on-error: true`
- **Solução:** Não falha o build, mas aviso aparece

---

## 📖 Referências

- [GitHub Actions Docs](https://docs.github.com/en/actions)
- [Codecov Setup](https://codecov.io/github)
- [Lighthouse CI](https://github.com/treosh/lighthouse-ci-action)
- [pytest-cov](https://pytest-cov.readthedocs.io/)

---

**Próximo:** Integrar com Slack para notificações em tempo real

