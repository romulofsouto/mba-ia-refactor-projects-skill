# Heurísticas de Análise de Projeto (Fase 1)

Objetivo desta fase: produzir um retrato fiel da stack e da arquitetura atual, sem juízo de valor. Tudo aqui é observação, não crítica.

## 1. Detecção de linguagem

Conte extensões de arquivo-fonte na raiz do projeto e subpastas (ignore `node_modules/`, `.venv/`, `venv/`, `__pycache__/`, `.git/`, `dist/`, `build/`, `*.db`, `*.sqlite`). A extensão dominante é a linguagem principal.

| Extensão | Linguagem |
|---|---|
| `.py` | Python |
| `.js` / `.mjs` / `.cjs` | JavaScript (Node.js) |
| `.ts` | TypeScript |
| `.rb` | Ruby |
| `.go` | Go |
| `.java` | Java |
| `.php` | PHP |

Se houver mistura (ex: `.py` + `.html` de templates), a linguagem do **backend** é o que importa — olhe onde está a lógica de rota/servidor.

## 2. Detecção de framework e versão

Não adivinhe pelo nome do arquivo — leia o manifesto de dependências e/ou os imports no entrypoint.

| Sinal | Framework provável |
|---|---|
| `requirements.txt` com `flask==X` ou `import flask` | Flask (versão = a do requirements.txt) |
| `requirements.txt` com `django` | Django |
| `requirements.txt` com `fastapi` | FastAPI |
| `package.json` com `"express"` nas dependencies | Express (versão = a do package.json) |
| `package.json` com `"next"` | Next.js |
| `Gemfile` com `rails` | Ruby on Rails |
| `go.mod` com `gin-gonic/gin` | Gin |

Extraia a versão exata do manifesto (`requirements.txt`, `package.json`) em vez de reportar "Flask" sem número — isso importa para saber se há APIs deprecated na versão em uso (ver catálogo de anti-patterns).

Liste também as dependências relevantes além do framework web (ORM, driver de banco, lib de auth, etc.) — elas revelam decisões arquiteturais (ex: `flask-sqlalchemy` presente = já existe um ORM; ausência = acesso a banco provavelmente manual).

## 3. Detecção de banco de dados

- Procure strings de conexão (`sqlite3.connect(...)`, `sqlite3.Database(...)`, `SQLALCHEMY_DATABASE_URI`, `DATABASE_URL`, `mysql.createConnection`, `pg.Pool`).
- Procure `CREATE TABLE` (SQL cru) ou classes de modelo de ORM (`db.Model`, `Schema`, `Entity`) para levantar a lista de tabelas/entidades.
- Reporte o mecanismo (SQLite in-memory, SQLite em arquivo, Postgres, MySQL, etc.) e a lista de tabelas encontradas.

## 4. Detecção de domínio de negócio

Infira o domínio a partir de:
- Nomes de rotas (`/produtos`, `/pedidos` → e-commerce; `/tasks`, `/categories` → gerenciador de tarefas; `/api/checkout`, `/courses`, `/enrollments` → LMS/cursos).
- Nomes de tabelas/entidades.
- `package.json` → campo `description`, ou comentários no topo dos arquivos de entrypoint.

Descreva o domínio em uma frase curta (ex: "E-commerce API (produtos, pedidos, usuários)", "LMS com fluxo de checkout (cursos, matrículas, pagamentos)", "Task Manager (tarefas, categorias, usuários)").

## 5. Mapeamento da arquitetura atual

Classifique em uma das categorias abaixo (ou descreva um híbrido):

- **Monolito de poucos arquivos**: toda a lógica (rotas + regra de negócio + acesso a dados) concentrada em 1-4 arquivos na raiz, sem pastas dedicadas por camada.
- **Parcialmente organizado**: já existem pastas por responsabilidade (`routes/`, `models/`, `services/`, `utils/`), mas a separação não é limpa — regra de negócio ainda vaza para dentro das rotas, ou há duplicação entre arquivos.
- **Já em MVC/camadas claras**: Models, Controllers e Views/Routes já existem com responsabilidades bem isoladas (raro nos projetos-alvo desta skill, mas trate o caso).

Para chegar a essa classificação, verifique:
- Existe uma pasta/arquivo cujo nome sugere "faz tudo" (`AppManager.js`, `app.py` com rotas E lógica juntas)?
- As rotas chamam funções de um módulo separado, ou a lógica está escrita inline dentro do handler HTTP?
- O acesso ao banco está encapsulado em algum módulo (`database.py`, um Repository) ou o SQL aparece espalhado direto nos handlers/models?

## 6. Contagem de arquivos-fonte

Conte apenas arquivos-fonte da linguagem detectada (passo 1), excluindo os diretórios ignorados no passo 1 e arquivos de dados (`.db`, `.sqlite`, `.json` de fixtures). Esse número vai no resumo da Fase 1 e serve de referência para o tamanho do relatório da Fase 2 (projetos maiores tendem a ter mais findings).

## Saída esperada desta fase

Um bloco `PHASE 1: PROJECT ANALYSIS` (formato definido no `SKILL.md`) com todos os campos preenchidos com dados reais do projeto — nunca com placeholders genéricos.
