================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      Python
Framework:     Flask 3.1.1 (+ flask-cors 5.0.1)
Dependencies:  flask, flask-cors, sqlite3 (stdlib — sem ORM, SQL cru)
Domain:        E-commerce API (produtos, usuários, pedidos/itens de pedido, relatório de vendas)
Architecture:  Monolito de poucos arquivos — 4 arquivos na raiz, sem pastas por camada. app.py registra rotas mas também define 2 endpoints admin com SQL inline; controllers.py mistura HTTP, validação e regra de negócio; models.py é um conjunto de funções que montam SQL por concatenação e devolvem dicts; database.py mantém uma conexão global singleton, cria o schema e faz seed.
Source files:  4 files analyzed (app.py, controllers.py, models.py, database.py — 780 linhas)
DB tables:     produtos, usuarios, pedidos, itens_pedido (SQLite em arquivo, loja.db)
================================

================================
ARCHITECTURE AUDIT REPORT
================================
Project: code-smells-project
Stack:   Python + Flask 3.1.1
Files:   4 analyzed | ~780 lines of code

## Summary
CRITICAL: 4 | HIGH: 5 | MEDIUM: 6 | LOW: 3

## Findings

### [CRITICAL] SQL Injection
File: models.py:28-297 (queries concatenadas em 28, 48-49, 58-60, 68, 92, 110, 127-128, 140, 149-150, 155, 158-160, 164-165, 174, 188, 192, 220, 224, 280, 291-297)
Description: Praticamente toda query é montada por concatenação com dados vindos da requisição, ex.: `login_usuario` (models.py:110) `"SELECT * FROM usuarios WHERE email = '" + email + "' AND senha = '" + senha + "'"` e a busca (models.py:291) `"... nome LIKE '%" + termo + "%' ..."`.
Impact: Bypass de login com `email = "' OR '1'='1' --"`, leitura/alteração/exclusão de qualquer tabela via `/produtos/busca?q=`, `POST /produtos`, `PUT /pedidos/<id>/status` etc.
Recommendation: Parametrizar todas as queries com placeholders `?` (playbook #2) dentro de uma camada de persistência dedicada (playbook #5).

### [CRITICAL] Endpoint Perigoso Sem Autenticação — execução de SQL arbitrário
File: app.py:59-78
Description: `POST /admin/query` executa `cursor.execute(query)` com `query = dados.get("sql", "")` vindo direto do body, sem nenhuma checagem de identidade, e faz `commit` de qualquer escrita.
Impact: Qualquer pessoa que conheça a URL pode ler a tabela de usuários (com senhas), alterar preços ou dar `DROP TABLE` — controle total do banco sem credencial.
Recommendation: Remover a capacidade de executar SQL livre — não é requisito de negócio legítimo (playbook #9).

### [CRITICAL] Hardcoded Credentials / Secrets
File: app.py:7-8
Description: `app.config["SECRET_KEY"] = "minha-chave-super-secreta-123"` e `app.config["DEBUG"] = True` fixos no código; senhas de seed também literais em database.py:164-166 (`"admin123"`, `"123456"`, `"senha123"`).
Impact: Quem tem acesso ao repositório tem a chave de assinatura de sessão e a senha do usuário admin.
Recommendation: Extrair para variáveis de ambiente via `config/settings.py` + `.env.example` (playbook #1).

### [CRITICAL] Senhas em texto plano armazenadas e expostas pela API
File: models.py:83, 99, 110, 127-128; database.py:119
Description: A coluna `senha TEXT` guarda a senha pura, o login compara a senha em texto plano no SQL (models.py:110) e `get_todos_usuarios`/`get_usuario_por_id` devolvem o campo `"senha"` (models.py:83, 99) nas respostas de `GET /usuarios` e `GET /usuarios/<id>`.
Impact: Qualquer cliente anônimo obtém as senhas de todos os usuários com um único GET; um vazamento do arquivo loja.db expõe todas as credenciais.
Recommendation: Hashear com `werkzeug.security.generate_password_hash`/`check_password_hash` (playbook #10) e nunca serializar a senha na resposta (entidade `Usuario.to_dict()` sem o campo — playbook #6).

### [HIGH] Endpoint Perigoso Sem Autenticação — reset do banco
File: app.py:47-57
Description: `POST /admin/reset-db` executa `DELETE` em `itens_pedido`, `pedidos`, `produtos` e `usuarios` sem qualquer checagem de autenticação/autorização.
Impact: Um único request anônimo apaga todos os dados da loja.
Recommendation: Proteger com middleware de autenticação de admin (`@require_admin`, token via variável de ambiente) e mover a operação para Controller/Model (playbook #9).

### [HIGH] Vazamento de segredo no endpoint público /health
File: controllers.py:285-289
Description: `/health` devolve `"secret_key": "minha-chave-super-secreta-123"`, `"debug": True`, `"db_path": "loja.db"` e `"ambiente": "producao"` a qualquer chamador. Classificado acima do LOW típico do catálogo porque expõe a chave de assinatura, não só metadados.
Impact: A chave de sessão da aplicação fica disponível publicamente, sem nem precisar de acesso ao código.
Recommendation: Reduzir a resposta a status/conectividade/contagens, removendo segredos e configuração interna (catálogo #15).

### [HIGH] Modo debug do Werkzeug exposto na rede (API deprecated para produção)
File: app.py:88
Description: `app.run(host="0.0.0.0", port=5000, debug=True)` serve a aplicação com o servidor de desenvolvimento e o debugger interativo ativado, escutando em todas as interfaces.
Impact: O debugger interativo do Werkzeug permite execução de código Python remoto a partir de uma página de erro; o servidor de dev não é feito para produção.
Recommendation: `DEBUG` lido de variável de ambiente com default `false`; em produção usar gunicorn/uwsgi (seção APIs Deprecated / playbook #1).

### [HIGH] Fat Controller / Lógica de Negócio no Controller
File: controllers.py:24-62, 188-220, 237-255
Description: `criar_produto` tem ~30 linhas de regra de domínio inline (preço/estoque não negativos, tamanho do nome, `categorias_validas` na linha 52); `criar_pedido` orquestra notificações (208-210); `atualizar_status_pedido` decide transições válidas e efeitos colaterais (242-250). Todos leem `request` diretamente.
Impact: Regras de negócio não podem ser reutilizadas nem testadas sem subir um servidor HTTP.
Recommendation: Mover validação/regra para entidades de domínio (Model) e deixar o controller só traduzindo HTTP ⇄ chamada (playbook #4).

### [HIGH] Estado Global Mutável — conexão singleton compartilhada
File: database.py:4-10
Description: `db_connection` é global de módulo (`global db_connection`), aberta com `check_same_thread=False` e compartilhada por todas as requisições/threads; importada diretamente por app.py, controllers.py e models.py.
Impact: Requisições concorrentes compartilham o mesmo estado de transação (um `commit` de uma request confirma a escrita pendente de outra); impossível testar com banco isolado.
Recommendation: Conexão por requisição via `flask.g` + `teardown_appcontext`, com caminho do banco vindo da config (playbook #1/#5).

### [MEDIUM] SQL fora da camada de Model (ausência de camada de persistência)
File: app.py:49-55; controllers.py:266-274
Description: Além de models.py, o SQL aparece direto em rota (`reset_database`, app.py:51-54) e no controller (`health_check`, controllers.py:268-274 `SELECT COUNT(*) FROM ...`).
Impact: O acesso ao banco não está encapsulado; mudanças de schema exigem caçar SQL em todas as camadas.
Recommendation: Concentrar todo SQL nos Models/Repositories (playbook #5).

### [MEDIUM] Model Anêmico/Procedural
File: models.py:4-314
Description: `models.py` é uma lista de funções soltas que devolvem `dict` cru; a regra "tem estoque suficiente" vive procedural no meio de `criar_pedido` (models.py:144) e o mapeamento linha→dict de produto é copiado 3 vezes (12-21, 31-40, 304-313).
Impact: Mudança de coluna se propaga por vários lugares; regras de domínio espalhadas.
Recommendation: Entidades `Produto`, `Usuario`, `Pedido` com `to_dict()` e métodos de regra (playbook #6).

### [MEDIUM] Queries N+1
File: models.py:171-201, 203-233
Description: `get_pedidos_usuario` e `get_todos_pedidos` fazem 1 query por pedido para itens (188/220) e 1 query por item para o nome do produto (192/224).
Impact: Listar 100 pedidos com 5 itens cada = ~600 queries.
Recommendation: Uma query com `LEFT JOIN` entre `pedidos`, `itens_pedido` e `produtos`, agrupando em memória (playbook #7).

### [MEDIUM] Lógica Duplicada
File: models.py:171-201 vs 203-233; controllers.py:28-50 vs 72-90
Description: As duas listagens de pedido são cópias idênticas que só diferem no `WHERE`; a validação de produto é reimplementada em `atualizar_produto` e já divergiu — a atualização não valida categoria nem tamanho do nome (controllers.py:81-90).
Impact: `PUT /produtos/<id>` aceita categoria inválida que `POST /produtos` rejeita — endpoints inconsistentes para o mesmo dado.
Recommendation: Uma única função de validação de produto e uma única função de montagem de pedidos (playbook #8).

### [MEDIUM] Validação ausente nas rotas
File: controllers.py:169-170, 195-201, 239-240; models.py:139-146
Description: `login` e `atualizar_status_pedido` chamam `dados.get(...)` sem checar se o body existe; `criar_pedido` não valida `quantidade` (inteiro > 0) nem `produto_id` — `quantidade` negativa passa na checagem de estoque (models.py:144) e **aumenta** o estoque em models.py:164; `atualizar_status_pedido` não verifica se o pedido existe.
Impact: Manipulação de estoque via pedido com quantidade negativa; erros 500 em vez de 400/404.
Recommendation: Validar formato no controller e invariantes na entidade (`Pedido`/`Produto`), retornando 400/404 (playbook #4/#6).

### [MEDIUM] Exceção Genérica expondo detalhes internos
File: controllers.py:10-12 (padrão repetido em 21-22, 60-62, 95-96, 108-109, 125-126, 133-134, 143-144, 164-165, 185-186, 218-220, 226-227, 234-235, 254-255, 261-262, 291-292); app.py:77-78
Description: Todo handler faz `except Exception as e: return jsonify({"erro": str(e)}), 500`, sem logar stack trace e devolvendo a mensagem crua da exceção (inclusive erros de SQL) ao cliente.
Impact: Causa raiz invisível nos logs; mensagens de erro do SQLite ajudam a explorar a SQL Injection.
Recommendation: Handler de erro centralizado (`middlewares/error_handler.py`) que loga a exceção e devolve mensagem genérica.

### [LOW] Logging via print()
File: controllers.py:8, 11, 57, 61, 106, 161, 179, 182, 208-210, 219, 248, 250; app.py:56, 83-86
Description: Toda observabilidade é `print()`, incluindo o "envio" de e-mail/SMS/push (controllers.py:208-210) e e-mails de login.
Impact: Sem nível, sem filtro, sem destino configurável.
Recommendation: `logging.getLogger(__name__)` com níveis adequados.

### [LOW] Dados órfãos no delete de produto
File: models.py:65-70
Description: `deletar_produto` faz `DELETE FROM produtos` sem tratar `itens_pedido` que referenciam o produto — o próprio código já mascara isso com o fallback `"Desconhecido"` (models.py:196).
Impact: Histórico de pedidos perde referência ao produto vendido.
Recommendation: Tratar dependentes explicitamente (ou soft delete via coluna `ativo`, já existente).

### [LOW] Magic numbers / listas mágicas
File: models.py:257-262; controllers.py:52, 242
Description: Faixas de desconto (`10000`/`0.1`, `5000`/`0.05`, `1000`/`0.02`), lista de categorias válidas e lista de status válidos são literais inline no meio da lógica.
Impact: Regra de negócio difícil de localizar e alterar.
Recommendation: Constantes nomeadas no Model de domínio correspondente.

## Deprecated APIs
- app.py:88 — `app.run(host="0.0.0.0", port=5000, debug=True)` como forma de servir a aplicação: prática deprecated pela documentação do Flask para produção. Substituir por servidor WSGI (gunicorn/uwsgi) e `debug` controlado por variável de ambiente, default `False` (finding HIGH acima).
- models.py:110, 127-128 — senha armazenada/comparada sem nenhum hash (pior que o `hashlib.md5` listado no catálogo). Substituir por `werkzeug.security.generate_password_hash` / `check_password_hash` (finding CRITICAL acima).
- `datetime.utcnow()` e `@app.before_first_request`: não encontrados.

================================
Total: 18 findings
================================

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
