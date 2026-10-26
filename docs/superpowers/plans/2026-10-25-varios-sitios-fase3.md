# Vários sítios — Fase 3: administração, Tasks por sítio e tela de sítios — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Só administradores gerenciam usuários e sítios; cada um só vê as pessoas do seu sítio; backup, WhatsApp diário e resumo mensal rodam para todos os sítios; admin cria sítio e libera acesso pela tela.

**Architecture:** `sitios.json` ganha `"admins": [login, …]`. `sitios.e_admin(login)` e `sitios.logins_do_sitio(slug, logins)` decidem permissão e visibilidade. As Tasks usam `sitios.cada_sitio()` (ativa um por vez — são processos próprios, sem a trava do site). A tela "🏡 Sítios" em Configurações grava `sitios.json` e `sitios/<slug>/sitio_config.json` por `sitios.criar()`/`sitios.salvar_acesso()`.

**Tech Stack:** Python 3 / Flask / pytest; Jinja + JS puro.

**Spec:** `docs/superpowers/specs/2026-10-25-varios-sitios-design.md`

## Global Constraints

- Sem `sitios.json`: todo login é admin e vê todos (igual a hoje).
- Com `sitios.json` e sem `"admins"`: admin = quem tem acesso ao primeiro sítio (o Santo Antonio) — ninguém de fora vira admin por esquecimento.
- Só admin: adicionar/excluir usuário, redefinir senha de outro, criar sítio, mudar acessos. Trocar a própria senha e o próprio WhatsApp: qualquer um.
- Lista de usuários e `/api/config-whatsapp-todos`: não-admin vê só quem tem acesso ao sítio atual.
- Mensagens das Tasks começam com `🐄 *<nome do sítio>*`; aviso de um sítio vai só para quem é dele (`sitio=slug`).
- Backup: cada sítio na sua `backups/`; `usuarios.json` e `sitios.json` só no backup da raiz.
- `criar()`: slug `[a-z0-9-]{1,40}` novo; pasta `sitios/<slug>`; donos validados por `config.ler_membros` (inválido → ValueError, nada gravado); gravação atômica (tmp + `os.replace`). Ao criar o primeiro `sitios.json`, todo login existente ganha acesso ao Santo Antonio (ninguém perde acesso).

## Review Focus

- **Relativo tenta redefinir a senha do Deyvid** → 403, senha intacta. Teste em Task 1 (`test_nao_admin_nao_gerencia_usuarios`).
- **Primeiro sítio novo criado pela tela** → Geane/Nilson continuam entrando. Teste em Task 3 (`test_criar_primeiro_sitio_mantem_acessos`).
- **Donos inválidos na tela** → erro, nenhum arquivo criado. Teste em Task 3 (`test_criar_sitio_invalido_nao_grava`).
- **Erro num sítio na Task** → os outros sítios ainda rodam; saída ≠ 0. Teste em Task 2 (`test_task_erro_num_sitio_nao_para_os_outros`).
- **Admin se tira de admin/acesso** → recusado (sempre fica ≥1 admin). Teste em Task 3 (`test_nao_remove_ultimo_admin`).

---

### Task 1: Administradores e privacidade entre sítios

**Files:** Modify `sitios.py` (`e_admin(login) -> bool`, `logins_do_sitio(slug, logins) -> list`), `routes_usuarios.py` (guarda nas 3 rotas; lista filtrada; `e_admin` no template), `routes_api_extras.py` (`/api/config-whatsapp-todos` filtrado), `templates/configuracoes.html` (formulários de gestão só para admin); Test `tests/test_sitios.py`.

- [ ] Testes `test_admin_padrao`, `test_nao_admin_nao_gerencia_usuarios`, `test_lista_so_do_sitio`; implementar; PASS; commit `Fase 3: so administradores gerenciam usuarios; cada sitio ve so os seus`.

### Task 2: Tasks por sítio

**Files:** Modify `sitios.py` (`cada_sitio()` → itera slugs ativando), `alertas_whatsapp.py` (`main` por sítio; cabeçalho com o nome; `sitio=`), `resumo_mensal.py` (idem; `montar_resumo_mensal(..., nome_sitio=)`), `backup_automatico.py` (laço por sítio); Tests `tests/test_sitios.py`.

- [ ] Testes `test_task_whatsapp_por_sitio`, `test_resumo_mensal_por_sitio`, `test_backup_por_sitio`, `test_task_erro_num_sitio_nao_para_os_outros`; implementar; PASS; commit `Fase 3: backup, WhatsApp e resumo mensal para cada sitio`.

### Task 3: Tela de sítios

**Files:** Modify `sitios.py` (`criar(nome, slug, membros, acesso_logins) -> str`, `salvar_acesso(acesso, admins)`), `routes_usuarios.py` (`POST /configuracoes/sitios/criar`, `POST /configuracoes/sitios/acesso`), `templates/configuracoes.html` (seção 🏡 Sítios, só admin).

- [ ] Testes `test_criar_sitio_pela_tela`, `test_criar_primeiro_sitio_mantem_acessos`, `test_criar_sitio_invalido_nao_grava`, `test_mudar_acesso`, `test_nao_remove_ultimo_admin`; implementar; PASS; commit `Fase 3: tela para criar sitio e liberar acesso`.

### Task 4: Documentação

- [ ] CHANGELOG, CLAUDE.md, Ajuda (seção Configurações → Sítios), spec (fase 3 entregue); PASS; commit `Docs: fase 3 dos varios sitios`.
