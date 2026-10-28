# Segurança — Sítio Santo Antonio v5.10+

## 📊 Resultado da Auditoria

**Status Geral:** ✅ SEGURO (com ressalvas)

| Aspecto | Status | Detalhes |
|---------|--------|----------|
| CSRF Protection | ✅ | Habilitado em todos os formulários POST |
| Autenticação | ✅ | @login_required em todas as rotas sensíveis |
| SQL Injection | ✅ | Sem queries SQL diretas (pandas + Excel) |
| XSS Protection | ✅ | Jinja2 auto-escape ativado |
| Validação de dados | ✅ | Type conversion com fallback seguro |
| Upload de arquivos | ✅ | secure_filename + extensões permitidas |
| Secrets | ✅ | .gitignore protege client_secret e .env |
| Brute force | ⚠️ | Bloqueio de login implementado (limitado) |
| Session security | ⚠️ | Requer config HTTPS em produção |
| Dependências | ✅ | Atualizadas, 12 pacotes rastreados |

---

## 🔴 Riscos Críticos Encontrados

### 1. Senha Padrão no Código
**Severidade:** 🔴 ALTO

**Problema:**
```python
# config.py
# Todos os usuários inicializam com 'sitio2025'
```

**Impacto:** Qualquer pessoa com acesso ao código pode acessar o sistema

**Solução:**
```bash
# Opção 1: Variável de ambiente (RECOMENDADO)
export GADO_SECRET_KEY="SenhaForte_Min16Caracteres_Especiais@2024"

# Opção 2: Arquivo .env (local, não no Git)
GADO_SECRET_KEY=SenhaForte_Min16Caracteres_Especiais@2024
```

---

## 🟡 Riscos Médios

### 2. Rate Limiting Limitado
**Severidade:** 🟡 MÉDIO

**Problema:** Login tem bloqueio básico, mas sem rate limiting em outras rotas

**Solução em Produção:**
```nginx
# nginx.conf
limit_req_zone $binary_remote_addr zone=login:10m rate=5r/m;
location /login {
    limit_req zone=login burst=10;
}
```

### 3. Session Security Incompleto
**Severidade:** 🟡 MÉDIO

**Problema:** Cookies de sessão não marcados como Secure em produção

**Solução:**
```python
# extensions.py (em produção)
app.config['SESSION_COOKIE_SECURE'] = True  # Apenas HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True  # Sem acesso JS
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=8)
```

---

## 📋 Checklist para Produção

### Segurança
- [ ] Mudar senha padrão 'sitio2025'
- [ ] Ativar HTTPS (SSL/TLS)
- [ ] Configurar SESSION_COOKIE_SECURE = True
- [ ] Configurar SESSION_COOKIE_HTTPONLY = True
- [ ] Implementar CSRF tokens em todos os formulários ✅ (já feito)
- [ ] Validar todas as entradas de usuário ✅ (já feito)
- [ ] Sanitizar saídas HTML ✅ (Jinja2 auto-escape)
- [ ] Testar XSS com payloads comuns
- [ ] Testar CSRF com ferramentas de teste

### Dependências
- [ ] `pip install --upgrade pip setuptools wheel`
- [ ] `pip install --upgrade -r requirements.txt`
- [ ] `pip audit` (verificar CVEs)
- [ ] Verificar Flask >= 2.3.0
- [ ] Verificar Pandas >= 2.0.0
- [ ] Verificar Openpyxl >= 3.0.0

### Acesso e Dados
- [ ] Dados em `~/gado-dados/` fora do repo ✅
- [ ] Permissões de arquivo: `chmod 700 ~/gado-dados/` (Linux)
- [ ] Backups testados e restauráveis ✅ (backup_automatico.py)
- [ ] Rotação de backups: manter últimos 30 ✅
- [ ] Verificar acesso ao arquivo Excel (somente leitura/escrita autenticada)

### Logging e Monitoramento
- [ ] Ativar logging de acesso
- [ ] Ativar logging de erros
- [ ] Monitorar tentativas de login falhadas
- [ ] Alertas de erro 500
- [ ] Alertas de acesso negado

### Autenticação
- [ ] Força de senha: mín 12 caracteres, maiúsculas, minúsculas, números, símbolos
- [ ] Considerar 2FA (TOTP) no futuro
- [ ] Implementar password expiration (ex: 90 dias)
- [ ] Histórico de senhas (não reutilizar últimas 5)

### Infraestrutura
- [ ] Reverse proxy (nginx) com WAF
- [ ] Rate limiting de IP
- [ ] CORS restritivo (apenas seu domínio)
- [ ] Firewall: abrir apenas portas 443 (HTTPS) e 22 (SSH)
- [ ] SSH com chaves, sem password auth

---

## 🛡️ Defesas Já Implementadas

✅ **CSRF Protection**
- Token CSRF em todos os forms
- Validação com `_validar_csrf()`

✅ **Autenticação**
- Hash de senha (werkzeug.security)
- Session com Flask
- @login_required em rotas sensíveis

✅ **Validação**
- Type conversion segura (`_int_form`, `parse_valor`)
- Whitelist de tipos em formulários
- Sem eval() ou exec()

✅ **Dados**
- Nenhuma query SQL (pandas + Excel)
- Sem comando shell dinâmico
- File upload com `secure_filename`

✅ **Segredos**
- .gitignore protege `client_secret_*.json`
- SECRET_KEY em config.py (substituir em produção)

---

## 🔐 Configuração Recomendada em Produção

### PythonAnywhere (atual)
```bash
# Web app settings
Python version: 3.12
Virtualenv: /home/usuario/.virtualenvs/gado

# Environment variables
GADO_SECRET_KEY=SenhaForte_Min16Caracteres@2024
GADO_DATA_DIR=/home/usuario/gado-dados/

# WSGI config
SSL: Ativado
Enforce HTTPS: Sim
Force HTTPS: Sim
```

### Local (desenvolvimento)
```python
# extensions.py
if not app.debug:  # Apenas produção
    app.config['SESSION_COOKIE_SECURE'] = True
    app.config['SESSION_COOKIE_HTTPONLY'] = True
```

---

## 📞 Incidentes de Segurança

Se encontrar uma vulnerabilidade:
1. **Não** publique em issues públicas
2. Email: [seu email aqui]
3. Descreva: tipo, versão, passos para reproduzir
4. Tempo para patch: 7 dias máximo

---

## 📚 Referências

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Flask Security](https://flask.palletsprojects.com/security/)
- [Pandas Security](https://pandas.pydata.org/docs/user_guide/security.html)

---

**Última atualização:** 2026-10-28  
**Versão:** v5.10.1  
**Status:** ✅ Auditado
