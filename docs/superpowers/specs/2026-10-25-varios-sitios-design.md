# Vários sítios (cada parente com o seu) — design

**Status:** aprovado em 2026-10-25 · fase 1 entregue · **Data:** 2026-10-25 · **Versão alvo:** 5.0

## Objetivo

Outros parentes usarem o sistema para o **próprio sítio**, com dados, donos, brincos,
WhatsApp e backups separados. Quem participa de mais de um (ex.: Deyvid) troca de sítio
num seletor no topo (como o "Propriedade: Todas" do PainelCorte nos exemplos).

## O que impede hoje

1. **Donos fixos no código** — `config.MEMBROS = ["Mae", "Deyvid", "Nilson"]` é usado em
   15 arquivos e vira **nome de coluna** (`Qtd Mae`, `Custo Nilson (R$)`…) em Compras e
   Vendas; o rateio é "em terços".
2. **Uma pasta de dados por processo** — `db.DATA_DIR`/`ARQUIVO_PATH` são globais (26 usos).
   Trocar o global por requisição não é seguro com vários usuários ao mesmo tempo.
3. **Login** — usuários e senhas valem para o site todo; não há "quem vê qual sítio".

## Decisão proposta: uma pasta por sítio, o mesmo site

```
~/gado-dados/                      ← continua sendo o Sítio Santo Antonio (nada muda nele)
~/gado-dados/sitios/<slug>/        ← cada sítio novo: gado_familia.xlsx, sitio_config.json,
                                     backups/, cache_fotos/, drive_token.json…
~/gado-dados/sitios.json           ← {slug: {nome, membros, usuarios}} e usuário → sítios
```

- **Nada se move** no sítio atual: ele vira o sítio padrão (`slug = "santo-antonio"`).
- **Donos por sítio** — `membros` vem do `sitios.json`; as colunas `Qtd <dono>` etc. são
  geradas a partir deles e **acrescentadas no fim** (regra de migração de sempre). O
  rateio "em terços" vira "em partes iguais" (1/n). Para o Santo Antonio o resultado é o
  mesmo, e as 3 invariantes contábeis continuam a régua.
- **Pasta por requisição** — `db.data_dir()` lê o sítio da sessão (`flask.g`); as Tasks
  (backup, WhatsApp, resumo mensal) rodam em laço sobre todos os sítios.
- **Acesso** — cada usuário tem a lista de sítios que pode abrir; um parente não vê os
  números do outro. Admin (Deyvid) cria o sítio nas Configurações.

### Alternativa mais barata (não recomendada como fim, serve de degrau)

Uma **instalação por sítio** (outra conta do PythonAnywhere com `GADO_DATA_DIR` próprio).
Só exige o passo 1 abaixo; não tem seletor e cada parente mantém o seu servidor.

## Fases

1. **Donos configuráveis** (sem mudar nada visível no Santo Antonio): `MEMBROS`,
   nomes, emojis e cores de brinco lidos da pasta de dados; colunas por dono geradas.
   Testes: invariantes com 2 e 4 donos, além dos dados reais.
2. **Pasta por requisição + seletor de sítio + acesso por usuário.**
3. **Tasks multi-sítio** (backup, WhatsApp, resumo mensal) e página de criar sítio.
4. **Painel "Família"** — soma dos sítios: rebanho, capital, resultado e cabeças por
   sítio, lado a lado e no total. Cada número vem do motor do próprio sítio
   (`calcular_resumo_financeiro` por pasta), então as invariantes valem por sítio e a
   soma bate. Só leitura: lançar continua sendo dentro de cada sítio.

## Riscos

- É a mudança mais invasiva desde a v4.0: mexe em finanças, relatórios e PDF. Cada fase
  sai separada, com smoke test nos dados reais e backup antes.
- Plano grátis do PythonAnywhere: um site só (ok para esta proposta) e espaço em disco
  dividido entre os sítios (fotos ficam no Drive de cada um).

## Decisões (respondidas em 2026-10-25)

- **Vários sócios por sítio, como aqui** → a fase 1 (donos configuráveis, rateio em
  partes iguais e colunas por dono geradas) é obrigatória e vem primeiro.
- **Todos da família veem os sítios somados** → entra a fase 4 (painel "Família").
  Qualquer usuário com acesso a pelo menos um sítio vê o total consolidado e o resumo
  de cada sítio; os lançamentos e as fichas continuam só para quem é do sítio.
