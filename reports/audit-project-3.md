================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      Python 3
Framework:     Flask 3.0.0 (+ Flask-SQLAlchemy 3.1.1, Flask-CORS 4.0.0)
Dependencies:  flask-sqlalchemy (ORM), flask-cors, marshmallow 3.20.1 (declarada, nunca importada), requests 2.31.0 (declarada, nunca importada), python-dotenv 1.0.0 (declarada, nunca carregada)
Domain:        Task Manager (tarefas, categorias, usuários, relatórios de produtividade)
Architecture:  Parcialmente organizado — já existem models/ (SQLAlchemy), routes/ (3 blueprints), services/ e utils/, mas não há camada de Controller: validação, regra de negócio, serialização e queries ficam inline nos handlers; services/notification_service.py e utils/helpers.py (validações prontas) nunca são chamados; rotas de /categories vivem em report_routes.py
Source files:  15 files analyzed (~1158 LOC)
DB tables:     users, categories, tasks (SQLite em arquivo `tasks.db` via SQLAlchemy)
================================

================================
ARCHITECTURE AUDIT REPORT
================================
Project: task-manager-api
Stack:   Python + Flask 3.0.0 (Flask-SQLAlchemy 3.1.1)
Files:   15 analyzed | ~1158 lines of code

## Summary
CRITICAL: 2 | HIGH: 4 | MEDIUM: 6 | LOW: 3

## Findings

### [CRITICAL] Hardcoded Credentials / Secrets
File: app.py:13, services/notification_service.py:7-10
Description: `app.config['SECRET_KEY'] = 'super-secret-key-123'` fica fixo no código-fonte, assim como as credenciais SMTP em `NotificationService.__init__` (`email_user = 'taskmanager@gmail.com'`, `email_password = 'senha123'`). A URI do banco (`app.py:11`) também está hardcoded.
Impact: Quem tem acesso ao repositório consegue forjar cookies de sessão assinados pelo Flask e entrar na conta de e-mail usada pela aplicação.
Recommendation: Playbook #1 "Extrair Configuração": criar `config/settings.py` lendo `os.environ` (via python-dotenv, que já é dependência), mais `.env.example` sem valores reais e `.env` no `.gitignore`.

### [CRITICAL] Vazamento do hash de senha em todas as respostas de usuário
File: models/user.py:16-25 (linha 21: `'password': self.password`), consumido em routes/user_routes.py:33, 85, 129, 209
Description: `User.to_dict()` serializa o campo `password` e é usado como resposta de `GET /users/<id>`, `POST /users`, `PUT /users/<id>` e até de `POST /login`. Como o hash é MD5 sem salt (ver finding abaixo), ele é trivialmente reversível.
Impact: Qualquer cliente anônimo que chame `GET /users/1` recebe o hash da senha do administrador e pode recuperar a senha original em segundos com rainbow tables.
Recommendation: Remover `password` de `to_dict()` (correção de segurança intencional no contrato). Todas as outras chaves continuam iguais.

### [HIGH] Endpoints destrutivos/administrativos sem autenticação e token falso
File: routes/user_routes.py:207-211, routes/user_routes.py:119-122, routes/user_routes.py:134-151
Description: `/login` devolve `'token': 'fake-jwt-token-' + str(user.id)`, um token previsível que nenhuma rota verifica. Qualquer cliente anônimo pode `DELETE /users/<id>` (o que também apaga as tasks do usuário) ou promover qualquer conta a admin com `PUT /users/<id>` enviando `{"role": "admin"}`.
Impact: Escalada de privilégio e destruição de dados só por conhecer a URL.
Recommendation: Playbook #9 "Proteger Endpoints Perigosos": emitir um token assinado com `SECRET_KEY` (`itsdangerous`, que já vem com o Flask) e aplicar um middleware `require_auth`/`require_admin` nas rotas de escrita de usuário. *Nota de escopo:* como exigir auth muda o contrato público, isso fica pendente para decisão humana. A Fase 3 troca o token falso por um token assinado e disponibiliza o middleware.

### [HIGH] Senha armazenada com MD5
File: models/user.py:29, models/user.py:32
Description: `set_password` grava `hashlib.md5(pwd.encode()).hexdigest()` e `check_password` compara MD5, sem salt e sem custo computacional.
Impact: Se o banco vazar (ou pelo finding CRITICAL acima), todas as senhas são recuperáveis por força bruta ou rainbow table.
Recommendation: Playbook #10: usar `werkzeug.security.generate_password_hash` / `check_password_hash` (o Werkzeug já é dependência do Flask).

### [HIGH] Modo debug do Werkzeug exposto em todas as interfaces
File: app.py:34
Description: `app.run(debug=True, host='0.0.0.0', port=5000)` liga o debugger interativo do Werkzeug escutando em todas as interfaces de rede.
Impact: O console do debugger permite executar código Python arbitrário no servidor para qualquer pessoa que alcance a porta e provoque uma exceção. Isso é fácil aqui, já que vários handlers estouram `TypeError` com input inválido.
Recommendation: Playbook #1/#10: ler `DEBUG`, `HOST` e `PORT` de variáveis de ambiente, com `debug=False` por padrão. Em produção, servir com um WSGI dedicado (gunicorn).

### [HIGH] Fat Controller — regra de negócio, validação e serialização dentro das rotas
File: routes/task_routes.py:85-154, routes/task_routes.py:156-223, routes/report_routes.py:12-101, routes/user_routes.py:42-90
Description: `create_task` (70 linhas) e `update_task` (68 linhas) fazem parse, validação, checagem de FK, conversão de data e de tags e persistência inline. `summary_report` (90 linhas) monta um relatório multi-tabela direto no handler. Não existe camada de Controller e as rotas acessam `Task.query`/`db.session` diretamente.
Impact: Nada disso pode ser reusado nem testado sem subir o Flask. Qualquer mudança de regra obriga a mexer em handlers HTTP.
Recommendation: Playbook #3/#4: criar `controllers/` (task, user, category, report) e `services/report_service.py` para o relatório multi-tabela, deixando nas rotas apenas o mapeamento HTTP → controller.

### [MEDIUM] Lógica de "tarefa atrasada" duplicada 6 vezes (e o método do Model ignorado)
File: routes/task_routes.py:30-39, routes/task_routes.py:71-80, routes/task_routes.py:283-287, routes/user_routes.py:171-180, routes/report_routes.py:33-36, routes/report_routes.py:132-135
Description: A regra `due_date < utcnow() and status not in (done, cancelled)` é reescrita inline em seis handlers, enquanto `Task.is_overdue()` (models/task.py:50-60) já implementa exatamente isso e nunca é chamado.
Impact: Se uma cópia for corrigida e as outras não, `/tasks`, `/users/<id>/tasks` e `/reports/*` passam a divergir sobre a mesma tarefa.
Recommendation: Playbook #8 "Deduplicar Lógica": `Task.is_overdue()` passa a ser a única fonte de verdade, chamada por todos os pontos.

### [MEDIUM] Queries N+1 em listagens e relatórios
File: routes/task_routes.py:41-57, routes/report_routes.py:55-56, routes/report_routes.py:161-163, routes/user_routes.py:22
Description: `GET /tasks` executa `User.query.get` e `Category.query.get` para cada task. `summary_report` executa `Task.query.filter_by(user_id=...)` por usuário, `GET /categories` faz um `count()` por categoria e `GET /users` faz lazy-load de `u.tasks` por usuário. `summary_report` também dispara 13 `count()` separados (report_routes.py:15-28).
Impact: O número de round-trips cresce linearmente com o volume de dados. Com 1000 tasks, `GET /tasks` faz ~2001 queries.
Recommendation: Playbook #7 "Eliminar N+1": usar `joinedload`/relacionamentos já definidos (`Task.user`, `Task.category`) e agregações `GROUP BY` (`func.count`) em vez de queries por item.

### [MEDIUM] Validação existente ignorada e reimplementada nas rotas
File: models/task.py:38-48, utils/helpers.py:19-23, utils/helpers.py:57-116, routes/task_routes.py:96-114, routes/task_routes.py:166-184, routes/user_routes.py:61-72, routes/report_routes.py:196-197
Description: `Task.validate_status/validate_priority`, `helpers.validate_email`, `helpers.process_task_data` e as constantes `VALID_STATUSES/VALID_ROLES/MIN_TITLE_LENGTH` existem e nunca são usadas. As rotas reimplementam as checagens inline e de forma incompleta: `priority` como string gera `TypeError` → 500 (task_routes.py:113). Em `/tasks/search`, `int(priority)` e `int(user_id)` com valor não numérico também dão 500 (task_routes.py:261, 264). `update_category` faz `'name' in data` sem checar se `data` é `None` (report_routes.py:196-197).
Impact: Existe código morto de um lado e validação inconsistente do outro, e input inválido vira erro 500 em vez de 400.
Recommendation: Centralizar a validação em um único módulo (`models/validators.py`) usado pelos controllers, devolvendo 400 com a mesma mensagem de hoje.

### [MEDIUM] Serialização duplicada fora do Model
File: routes/task_routes.py:17-28, routes/user_routes.py:15-23, routes/user_routes.py:162-169, routes/report_routes.py:38-43
Description: Os handlers reconstroem o dict da task/usuário campo a campo, copiando `Task.to_dict()` e `User.to_dict()` em vez de reusá-los e estendê-los.
Impact: Uma coluna nova ou uma mudança de formato (ex.: datas) precisa ser replicada em 4 lugares, e esquecer um gera payloads divergentes.
Recommendation: Playbook #6: o Model é dono da serialização (`to_dict()` com variações explícitas, ex.: `to_summary_dict()`), e o controller só a estende.

### [MEDIUM] Exceções genéricas/silenciosas
File: routes/task_routes.py:62, routes/task_routes.py:137, routes/task_routes.py:204, routes/task_routes.py:236, routes/user_routes.py:130, routes/user_routes.py:149, routes/report_routes.py:186, routes/report_routes.py:207, routes/report_routes.py:221, utils/helpers.py:46-49, utils/helpers.py:88
Description: Vários `except:` sem tipo e sem log. `GET /tasks` envolve o handler inteiro em `try/except:` devolvendo `'Erro interno'`, o que esconde qualquer bug.
Impact: A causa raiz das falhas some e fica impossível diagnosticar em produção. Também captura `KeyboardInterrupt`/`SystemExit`.
Recommendation: Criar um error handler central (`middlewares/error_handler.py`) que loga a exceção e devolve JSON padronizado. Capturar apenas exceções específicas (`ValueError`, `SQLAlchemyError`).

### [MEDIUM] Uso de APIs deprecated (`datetime.utcnow`, `Query.get`)
File: models/task.py:15-16, models/task.py:52, models/user.py:14, models/category.py:11, routes/task_routes.py:67, routes/user_routes.py:29, routes/report_routes.py:105 (lista completa na seção Deprecated APIs)
Description: `datetime.utcnow()` é deprecated desde o Python 3.12 (o ambiente roda 3.12.3). `Model.query.get(id)` é API legada no SQLAlchemy 2.x e emite `LegacyAPIWarning`.
Impact: Gera warnings hoje e quebra em versões futuras. `utcnow()` devolve datetime naive, o que causa erros sutis de comparação de fuso.
Recommendation: Playbook #10: `datetime.now(timezone.utc)` (gravando naive-UTC para manter o formato atual das colunas) e `db.session.get(Model, id)`.

### [LOW] Rotas de categoria dentro do blueprint de relatórios
File: routes/report_routes.py:157-223
Description: O CRUD de `/categories` está definido em `report_routes.py`, sob o blueprint `reports`.
Impact: Fica difícil achar o código, e o arquivo muda por dois motivos independentes (relatórios e categorias).
Recommendation: Mover para `routes/category_routes.py` + `controllers/category_controller.py`.

### [LOW] Logging via `print()`
File: routes/task_routes.py:149, routes/task_routes.py:153, routes/task_routes.py:219, routes/task_routes.py:234, routes/user_routes.py:83, routes/user_routes.py:89, routes/user_routes.py:147, services/notification_service.py:21, services/notification_service.py:24, utils/helpers.py:39-41
Description: A observabilidade depende de `print()` espalhados, sem nível nem formato.
Impact: Não dá para filtrar por severidade nem desligar ou redirecionar em produção.
Recommendation: Usar o módulo `logging` (`logger = logging.getLogger(__name__)`), configurado uma vez no composition root.

### [LOW] Código morto e imports não usados
File: app.py:7, routes/task_routes.py:7, routes/user_routes.py:6, routes/report_routes.py:7-8, utils/helpers.py:3-7, utils/helpers.py:31-34, services/notification_service.py:4-48, requirements.txt:4-5
Description: Há imports mortos (`os, sys, json` em app.py; `json, os, sys, time` em task_routes; `hashlib, json` em user_routes; `format_date, calculate_percentage, json` em report_routes). `NotificationService` nunca é instanciado e `generate_id` nunca é chamado. `marshmallow` e `requests` estão no requirements sem uso.
Impact: Ruído que atrapalha a leitura e dependências instaladas sem necessidade.
Recommendation: Remover imports e dependências não usados. Manter `NotificationService`, só que lendo credenciais de config (ele é feature latente, não lixo).

## Deprecated APIs
- `datetime.utcnow()`, deprecated desde o Python 3.12 → `datetime.now(timezone.utc)`:
  models/task.py:15, 16, 52 · models/user.py:14 · models/category.py:11 · routes/task_routes.py:31, 72, 215, 285 · routes/user_routes.py:172 · routes/report_routes.py:35, 42, 45, 71, 133 · services/notification_service.py:35 · utils/helpers.py:38 · seed.py:66, 67, 69, 70, 74
- `Model.query.get(id)`, legado no SQLAlchemy 2.x (`LegacyAPIWarning`) → `db.session.get(Model, id)`:
  routes/task_routes.py:42, 51, 67, 117, 122, 158, 188, 195, 227 · routes/user_routes.py:29, 94, 136, 155 · routes/report_routes.py:105, 192, 213
- `hashlib.md5()` para hash de senha → `werkzeug.security.generate_password_hash` / `check_password_hash`: models/user.py:29, 32
- `app.run(debug=True)` como forma de servir → `debug` via env (default `False`) + gunicorn em produção: app.py:34

================================
Total: 15 findings
================================

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
