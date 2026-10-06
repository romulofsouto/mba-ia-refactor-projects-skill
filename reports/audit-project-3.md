================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      Python 3
Framework:     Flask 3.0.0 (+ Flask-SQLAlchemy 3.1.1, Flask-CORS 4.0.0)
Dependencies:  flask-sqlalchemy (ORM), flask-cors, marshmallow 3.20.1 (declarada, nunca importada), requests 2.31.0 (declarada, nunca importada), python-dotenv 1.0.0 (declarada, nunca carregada)
Domain:        Task Manager (tarefas, categorias, usuários, relatórios de produtividade)
Architecture:  Parcialmente organizado — já existem models/ (SQLAlchemy), routes/ (3 blueprints), services/ e utils/, mas não há camada de Controller: validação, regra de negócio, serialização e queries ficam inline nos handlers; utils/helpers.py (validações prontas) e services/notification_service.py nunca são chamados; as rotas de /categories vivem em report_routes.py; não há autenticação em nenhuma rota
Source files:  17 files analyzed (~1158 LOC; 13 com lógica + 4 __init__.py)
DB tables:     users, categories, tasks (SQLite em arquivo `tasks.db` via SQLAlchemy)
================================

================================
ARCHITECTURE AUDIT REPORT
================================
Project: task-manager-api
Stack:   Python + Flask 3.0.0 (Flask-SQLAlchemy 3.1.1)
Files:   17 analyzed | ~1158 lines of code

## Summary
CRITICAL: 2 | HIGH: 4 | MEDIUM: 5 | LOW: 4

## Findings

### [CRITICAL] Hardcoded Credentials / Secrets
File: app.py:11-13, services/notification_service.py:9-10
Description: `app.config['SECRET_KEY'] = 'super-secret-key-123'` e a URI do banco ficam fixos no código-fonte, assim como as credenciais SMTP em `NotificationService.__init__` (`email_user = 'taskmanager@gmail.com'`, `email_password = 'senha123'`).
Impact: Quem tem acesso ao repositório consegue forjar qualquer dado assinado com a `SECRET_KEY` (sessões e, depois da correção abaixo, tokens de login) e entrar na conta de e-mail da aplicação.
Recommendation: Playbook #1 "Extrair Configuração": criar `config/settings.py` lendo `os.environ` (via python-dotenv, que já é dependência), com `.env.example` sem valores reais e `.env` no `.gitignore`.

### [CRITICAL] Vazamento do hash de senha em respostas da API
File: models/user.py:16-25 (linha 21: `'password': self.password`), consumido em routes/user_routes.py:33, routes/user_routes.py:85, routes/user_routes.py:129, routes/user_routes.py:209
Description: `User.to_dict()` serializa o campo `password` e é a resposta de `GET /users/<id>`, `POST /users`, `PUT /users/<id>` e até de `POST /login`. O hash é MD5 sem salt (ver finding abaixo), portanto trivialmente reversível.
Impact: Qualquer cliente anônimo que chame `GET /users/1` recebe o hash da senha do administrador e recupera a senha original em segundos com rainbow tables.
Recommendation: Remover `password` de `to_dict()` (correção de segurança intencional no contrato; todas as outras chaves continuam iguais).

### [HIGH] Endpoints destrutivos e de troca de privilégio sem autenticação (escalada de privilégio)
File: routes/user_routes.py:134-151, routes/user_routes.py:119-125, routes/user_routes.py:52, routes/user_routes.py:71-78, routes/user_routes.py:207-211
Description: Nenhuma rota verifica identidade. `DELETE /users/<id>` apaga qualquer usuário (e suas tasks) para um cliente anônimo; `PUT /users/<id>` aceita `{"role": "admin"}` e `{"active": false}` de qualquer um; `POST /users` aceita `"role": "admin"` no cadastro público — confirmado na app original: `PUT /users/2 {"role":"admin"}` e `POST /users {..., "role":"admin"}` sem token retornam 200/201. O "token" de `/login` é `'fake-jwt-token-' + str(user.id)`, previsível e nunca verificado.
Impact: Qualquer pessoa que conheça a URL vira administrador, desativa contas ou apaga usuários com todas as suas tarefas.
Recommendation: Playbook #9b: emitir um token assinado com `SECRET_KEY` (`itsdangerous`, já instalado com o Flask) e criar `middlewares/auth.py` com `require_auth`/`require_admin`, **aplicados** nas rotas citadas: `@require_admin` em `DELETE /users/<id>`; `@require_auth` em `PUT /users/<id>` com regra no controller (usuário comum só altera a si mesmo e nunca `role`/`active`; admin altera qualquer um); `POST /users` continua público para cadastro com `role` padrão `user`, mas `role` diferente de `user` exige token de admin.

### [HIGH] Senha armazenada com MD5
File: models/user.py:3, models/user.py:27-32
Description: `set_password` grava `hashlib.md5(pwd.encode()).hexdigest()` e `check_password` compara MD5 — sem salt e sem custo computacional.
Impact: Se o banco vazar (ou pelo finding CRITICAL acima), todas as senhas são recuperáveis por força bruta ou rainbow table.
Recommendation: Playbook #10: usar `werkzeug.security.generate_password_hash` / `check_password_hash` (Werkzeug já é dependência do Flask), com migração transparente dos hashes MD5 existentes no próximo login.

### [HIGH] Modo debug do Werkzeug exposto em todas as interfaces
File: app.py:34
Description: `app.run(debug=True, host='0.0.0.0', port=5000)` liga o debugger interativo do Werkzeug escutando em todas as interfaces. Confirmado: `POST /tasks` com `"priority": "2"` devolve a página "Werkzeug Debugger".
Impact: Qualquer exceção não tratada expõe stack trace e código-fonte, e o console do debugger permite execução remota de código se o PIN vazar.
Recommendation: Playbook #1/#10: `DEBUG` e `HOST` lidos de variável de ambiente, `debug=False` por padrão; servidor WSGI dedicado em produção.

### [HIGH] Fat Controller — regra de negócio dentro das rotas, sem camada de Controller
File: routes/task_routes.py:85-223, routes/report_routes.py:12-101, routes/user_routes.py:42-132
Description: Os handlers têm de 50 a 140 linhas misturando parse de HTTP, validação, regra de negócio (atraso, taxas de conclusão), consultas ao banco, serialização e commit. `summary_report` monta sozinho um relatório multi-tabela de 90 linhas. Não existe pasta `controllers/`.
Impact: Nada pode ser reaproveitado ou testado sem subir o servidor; qualquer ajuste em uma regra exige mexer em handlers HTTP.
Recommendation: Playbook #4 "Extrair Controller de dentro da Rota": criar `controllers/` (rotas só mapeiam HTTP → controller), mover regras para os Models e o relatório multi-tabela para `services/report_service.py`.

### [MEDIUM] Queries N+1 / consulta dentro de loop
File: routes/task_routes.py:41-57, routes/user_routes.py:22, routes/report_routes.py:53-68, routes/report_routes.py:161-164
Description: `GET /tasks` faz `User.query.get` e `Category.query.get` para cada task; `GET /users` acessa `len(u.tasks)` (lazy load por usuário); `summary_report` faz uma query de tasks por usuário; `GET /categories` faz um `count()` por categoria.
Impact: O número de queries cresce linearmente com o volume de dados (1 + 2N em `GET /tasks`).
Recommendation: Playbook #7 "Eliminar N+1": `joinedload` para user/category e `GROUP BY` com `func.count` para contagens por usuário/categoria.

### [MEDIUM] Lógica de "task atrasada" duplicada
File: routes/task_routes.py:30-39, routes/task_routes.py:71-80, routes/task_routes.py:283-287, routes/user_routes.py:171-180, routes/report_routes.py:34-37, routes/report_routes.py:132-135, models/task.py:50-60
Description: A regra "tem due_date no passado e não está done/cancelled" é reimplementada em 6 lugares, enquanto `Task.is_overdue()` existe e nunca é chamado. As contagens por status também são duplicadas entre `/tasks/stats` (task_routes.py:275-279) e `/reports/summary` (report_routes.py:19-22).
Impact: As cópias divergem com o tempo e endpoints diferentes passam a responder coisas diferentes para a mesma task.
Recommendation: Playbook #8 "Deduplicar Lógica de Negócio": todas as rotas usam `task.is_overdue()`; contagens por status em um único método do Model.

### [MEDIUM] Validação existente ignorada e reimplementada nas rotas
File: models/task.py:38-48, utils/helpers.py:19-23, utils/helpers.py:57-108, utils/helpers.py:110-116, routes/task_routes.py:110-114, routes/task_routes.py:176-184, routes/task_routes.py:260-264, routes/user_routes.py:61-72, routes/report_routes.py:196-197
Description: `Task.validate_status/validate_priority`, `helpers.validate_email`, `helpers.process_task_data` e as constantes `VALID_STATUSES/VALID_ROLES/MIN_TITLE_LENGTH` nunca são usados; as rotas reimplementam as checagens de forma incompleta. Confirmado: `POST /tasks` com `"priority": "2"` → 500 (`TypeError` em task_routes.py:113); `GET /tasks/search?priority=abc` → 500 (`int()` em task_routes.py:261); `PUT /categories/<id>` com corpo JSON `null` faz `'name' in None` (report_routes.py:197).
Impact: Código morto de um lado e validação inconsistente do outro; input inválido vira erro 500 em vez de 400.
Recommendation: Centralizar a validação nos Models (validadores únicos chamados pelos controllers), devolvendo 400 com as mesmas mensagens de hoje.

### [MEDIUM] Exceções genéricas / silenciosas
File: routes/task_routes.py:62-63, routes/task_routes.py:137, routes/task_routes.py:204, routes/task_routes.py:236, routes/user_routes.py:130, routes/user_routes.py:149, routes/report_routes.py:186, routes/report_routes.py:207, routes/report_routes.py:221, utils/helpers.py:46-49, utils/helpers.py:88
Description: Vários `except:` sem tipo e sem log. `GET /tasks` envolve o handler inteiro em `try/except:` devolvendo `'Erro interno'`, escondendo qualquer bug. Cada handler decide sozinho o formato do erro.
Impact: A causa raiz das falhas desaparece e o formato de erro varia entre rotas.
Recommendation: Handler de erro centralizado (`middlewares/error_handler.py`) com exceções de domínio tipadas (`ValidationError` → 400, `NotFoundError` → 404, `ConflictError` → 409), capturando só exceções específicas e logando as inesperadas.

### [MEDIUM] Serialização duplicada fora do Model
File: routes/task_routes.py:17-28, routes/user_routes.py:15-23, routes/user_routes.py:162-169, routes/report_routes.py:38-43
Description: Os handlers reconstroem o dict da task/usuário campo a campo, copiando `Task.to_dict()` e `User.to_dict()` em vez de reutilizá-los e estendê-los.
Impact: Uma coluna nova ou mudança de formato precisa ser replicada em 4 lugares; esquecer um gera payloads divergentes.
Recommendation: Playbook #6: o Model é dono da serialização (`to_dict()` e variações explícitas como `to_summary_dict()`); o controller só estende.

### [LOW] Logging via `print()`
File: routes/task_routes.py:149, routes/task_routes.py:153, routes/task_routes.py:219, routes/task_routes.py:234, routes/user_routes.py:83, routes/user_routes.py:89, routes/user_routes.py:147, services/notification_service.py:21, services/notification_service.py:24, utils/helpers.py:39-41
Description: A observabilidade depende de `print()` espalhados, sem nível nem formato.
Impact: Não dá para filtrar por severidade, nem desligar ou redirecionar em produção.
Recommendation: Módulo `logging` (`logger = logging.getLogger(__name__)`), configurado uma vez no composition root.

### [LOW] Magic numbers e literais repetidos
File: routes/task_routes.py:110, routes/task_routes.py:113, routes/task_routes.py:177, routes/task_routes.py:182, routes/user_routes.py:64, routes/user_routes.py:71, routes/user_routes.py:120, routes/report_routes.py:24-28, routes/report_routes.py:129
Description: A lista de status, a lista de roles, os limites de prioridade (1–5), o tamanho mínimo de senha (4) e o mapeamento prioridade → rótulo (`priority=1` = "critical"…) aparecem como literais soltos em vários handlers, embora as constantes existam em utils/helpers.py:110-116.
Impact: Alterar uma regra (ex.: novo status) exige caçar literais em vários arquivos.
Recommendation: Constantes nomeadas no Model dono da regra (`Task.VALID_STATUSES`, `User.VALID_ROLES`, `PRIORITY_LABELS`).

### [LOW] Código morto e imports não usados
File: app.py:7, routes/task_routes.py:7, routes/user_routes.py:6, routes/report_routes.py:7-8, utils/helpers.py:3-7, utils/helpers.py:31-34, requirements.txt:4-5
Description: Imports mortos (`os, sys, json` em app.py; `json, os, sys, time` em task_routes; `hashlib, json` em user_routes; `format_date, calculate_percentage, json` em report_routes); `generate_id` nunca chamado; `marshmallow` e `requests` declarados sem uso.
Impact: Ruído na leitura e dependências instaladas sem necessidade.
Recommendation: Remover imports, funções e dependências sem uso. `NotificationService` é mantido (feature latente), mas lendo credenciais da config.

### [LOW] Uso de APIs deprecated
File: models/task.py:15-16, models/task.py:52, models/user.py:14, models/category.py:11, routes/task_routes.py:42, routes/user_routes.py:29, routes/report_routes.py:105
Description: `datetime.utcnow()` (deprecated no Python 3.12) e `Model.query.get(id)` (API legada no SQLAlchemy 2.x) em todo o projeto — lista completa na seção abaixo.
Impact: Warnings hoje e quebra em versões futuras; `utcnow()` devolve datetime "naive", sujeito a erros de fuso.
Recommendation: Playbook #10 "Substituir APIs Deprecated": `datetime.now(timezone.utc)` e `db.session.get(Model, id)`.

## Deprecated APIs
- `datetime.utcnow()`, deprecated desde o Python 3.12 → `datetime.now(timezone.utc)`:
  models/task.py:15, 16, 52 · models/user.py:14 · models/category.py:11 · routes/task_routes.py:31, 72, 215, 285 · routes/user_routes.py:172 · routes/report_routes.py:35, 42, 45, 71, 133 · services/notification_service.py:35 · utils/helpers.py:38 · seed.py:66, 67, 69, 70, 74
- `Model.query.get(id)`, legado no SQLAlchemy 2.x (`LegacyAPIWarning`) → `db.session.get(Model, id)`:
  routes/task_routes.py:42, 51, 67, 117, 122, 158, 188, 195, 227 · routes/user_routes.py:29, 94, 136, 155 · routes/report_routes.py:105, 192, 213
- `hashlib.md5()` para hash de senha → `werkzeug.security.generate_password_hash` / `check_password_hash`: models/user.py:29, 32
- `app.run(debug=True)` como forma de servir → `debug` via env (default `False`) + servidor WSGI em produção: app.py:34

================================
Total: 15 findings
================================

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
