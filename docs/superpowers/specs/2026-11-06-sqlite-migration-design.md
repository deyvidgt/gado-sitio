# Design da Migração: Flask + Excel para SQLite/SQLAlchemy

## Objetivo
Eliminar a dependência do sistema em arquivos `.xlsx` (Excel) e dados em memória, migrando 100% da lógica para um banco de dados SQLite utilizando SQLAlchemy.

## Princípios de Migração
- **Zero Data Loss:** Migração automatizada com validação pós-conversão.
- **Isolamento de Sítios:** SQLite com múltiplos arquivos (`sitios/<slug>/data.db`) ou uma tabela `sitio_id` com chaves estrangeiras rígidas.
- **Interoperabilidade Temporária:** Durante a migração, a camada de acesso a dados (`db.py`) atuará como uma fachada (Facade) que pode ler de ambos, com escrita exclusiva no SQL.

## Arquitetura do Banco de Dados
- **SQLAlchemy ORM:** Definição de modelos (`Animais`, `Transacoes`, `Manejo`, etc.).
- **Migrações:** Uso do `Alembic` para versionamento do esquema.

## Estratégias por Fase
1. **Modelagem:** Definir schemas SQL equivalentes às abas do Excel.
2. **Camada de Acesso (Repository Pattern):** Criar `services/db_manager.py` para abstrair o acesso, substituindo chamadas diretas a `carregar_aba`.
3. **Migração de Dados:** Scripts ETL (Extract, Transform, Load) que leem o Excel, validam tipos e gravam no SQL.

## Riscos
- Divergências nas fórmulas financeiras (média móvel).
- Complexidade de manter o legado durante a transição.

---
*Nota Ponytail: Este é o design de alto nível. Com sua aprovação, prosseguiremos para o plano de implementação detalhado.*
