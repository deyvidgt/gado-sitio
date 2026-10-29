# Recomendações de Organização do Código-Fonte

**Diagnóstico:** 2026-10-28

## Problema Atual

O projeto tem **85 arquivos Python na raiz**, causando:
- ❌ Difícil navegação e busca
- ❌ Sem separação clara entre rotas e lógica
- ❌ Importações complexas de caminhos relativos
- ❌ Risco de conflitos de nome entre arquivos
- ❌ Escalabilidade limitada para novos módulos

## Estrutura Proposta

```
programa-sitio/
├── app.py                          # Ponto de entrada
├── config.py                       # Configurações
├── extensions.py                   # Extensões Flask
├── db.py                           # Banco de dados
├── sitios.py                       # Múltiplos sítios
│
├── routes/                         # ✅ NOVO: Todas as rotas
│   ├── __init__.py
│   ├── auth.py                    # routes_auth.py
│   ├── dashboard.py               # routes_dashboard.py
│   ├── animais.py                 # routes_animais.py
│   ├── leite.py                   # routes_leite.py
│   ├── pastos.py                  # routes_pastos.py
│   ├── ...                        # outros routes_*.py
│   └── api.py                     # routes_api.py (consolidado)
│
├── domain/                         # ✅ NOVO: Lógica de negócio
│   ├── __init__.py
│   ├── animais.py                 # Modelos de animais
│   ├── leite.py                   # Lógica de leite
│   ├── pastos.py                  # Lógica de pastos
│   ├── reproducao.py              # Reprodução
│   ├── genetica.py                # Análise genética
│   ├── mastite.py                 # mastite_predicao.py
│   ├── doencas.py                 # doencas_carencia.py
│   ├── partos.py                  # partos_predicao.py
│   ├── conversao.py               # conversao_alimentar.py
│   ├── insumos.py                 # Gestão de insumos
│   ├── lotes.py                   # Análise de lotes (FIFO)
│   ├── financeiro.py              # calculos.py (renomeado)
│   └── ...                        # outros modelos
│
├── utils/                          # ✅ NOVO: Funções auxiliares
│   ├── __init__.py
│   ├── busca.py                   # busca_global
│   ├── export.py                  # exportar.py
│   ├── backup.py                  # backup_automatico.py
│   ├── alertas.py                 # alertas_whatsapp.py
│   ├── pdf.py                     # Geração de PDFs
│   ├── voz.py                     # comando_voz.py
│   ├── fotos.py                   # Manipulação de fotos
│   ├── drive.py                   # Google Drive
│   └── ...
│
├── static/                         # Assets (JS, CSS, imagens)
├── templates/                      # Templates Jinja2
├── tests/                          # Suite de testes
│
├── migrations/                     # ✅ NOVO: Migrações de schema
├── docs/                           # Documentação
└── scripts/                        # ✅ NOVO: Scripts utilitários
    ├── setup.py
    ├── configurar_drive.py
    └── ...
```

## Fase 1: Reorganização Mínima (0-1 sprint)

Apenas mover sem refatorar (backward compatible):

### Passo 1: Criar pastas
```bash
mkdir -p routes domain utils migrations scripts
```

### Passo 2: Mover arquivos (mantendo importações do topo)
```bash
# Routes
mv routes_*.py routes/
mv routes/__init__.py routes/

# Domain logic
mv animais.py domain/
mv leite.py domain/
...

# Utils
mv busca.py utils/
mv exportar.py utils/
...
```

### Passo 3: Atualizar app.py
```python
# Antes
from routes_auth import *
from routes_dashboard import *

# Depois
from routes.auth import *
from routes.dashboard import *
```

### Passo 4: Atualizar imports internos
```python
# Antes
from animais import carregar

# Depois
from domain.animais import carregar
```

## Fase 2: Consolidação de Rotas (1-2 sprints)

Mesclar `routes_api.py` + `routes_api_extras.py` em estrutura unificada:

```python
# routes/api/
├── __init__.py
├── leite.py         # /api/leite/*
├── animais.py       # /api/animais/*
├── pastos.py        # /api/pastos/*
└── financeiro.py    # /api/financeiro/*
```

## Fase 3: Organização de Testes (1 sprint)

```
tests/
├── unit/
│   ├── test_domain_leite.py
│   ├── test_domain_genetica.py
│   └── ...
├── integration/
│   ├── test_routes_leite.py
│   └── ...
└── conftest.py
```

## Benefícios

| Antes | Depois |
|-------|--------|
| 85 arquivos na raiz | 8 pastas lógicas |
| `from animais import` ambíguo | `from domain.animais import` claro |
| Difícil localizar lógica | Estrutura intuitiva |
| Risco: `animais.py` em 2 lugares | Sem conflitos de nome |
| Importações: `.` ou `../` complexas | Sempre relativas a raiz ou pasta |

## Timeline Estimado

- **Fase 1:** 1 sprint (baixo risco, backward compatible)
- **Fase 2:** 2 sprints (consolidação de APIs)
- **Fase 3:** 1 sprint (testes)
- **Total:** 4 sprints (~1 mês)

## Impacto em Produção

- ✅ **Zero impacto no usuário** (rotas não mudam)
- ✅ **Testes migram junto** (conftest.py atualizado)
- ✅ **Reversível** (git revert se necessário)
- ✅ **Incremental** (pode fazer fase por fase)

## Recomendação

**Implementar Fase 1 em breve** (antes de 50 rotas mais). Isso vai:
1. Facilitar onboarding de novos devs
2. Reduzir tempo de busca de código
3. Melhorar legibilidade de imports
4. Preparar para próximas ondas (🧬, 🍼, 📉)

---

**Responsável:** Arquitetura | **Prioridade:** Média | **Data:** 2026-10-28
