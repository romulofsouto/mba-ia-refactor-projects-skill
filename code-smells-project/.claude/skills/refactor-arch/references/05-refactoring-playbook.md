# Playbook de Refatoração (Fase 3)

Cada padrão abaixo resolve um item do catálogo de anti-patterns (`02-antipattern-catalog.md`). Use o exemplo mais próximo da stack do projeto (Python ou JS) como referência de forma, não copie literalmente — adapte aos nomes reais do projeto.

---

## 1. Extrair Configuração (resolve #1 — Hardcoded Credentials)

**Antes (Python):**
```python
app.config["SECRET_KEY"] = "minha-chave-super-secreta-123"
app.config["DEBUG"] = True
```

**Depois:**
```python
# config/settings.py
import os

SECRET_KEY = os.environ["SECRET_KEY"]
DEBUG = os.environ.get("DEBUG", "false").lower() == "true"
```
```python
# app.py
from config import settings
app.config["SECRET_KEY"] = settings.SECRET_KEY
app.config["DEBUG"] = settings.DEBUG
```

**Antes (Node.js):**
```javascript
const config = {
    dbPass: "senha_super_secreta_prod_123",
    paymentGatewayKey: "pk_live_1234567890abcdef",
};
```

**Depois:**
```javascript
// config/index.js
module.exports = {
    dbPass: process.env.DB_PASS,
    paymentGatewayKey: process.env.PAYMENT_GATEWAY_KEY,
};
```
Crie `.env.example` listando `DB_PASS=`, `PAYMENT_GATEWAY_KEY=` sem valores reais, e garanta que `.env` está no `.gitignore`.

---

## 2. Parametrizar Queries SQL (resolve #2 — SQL Injection)

**Antes:**
```python
cursor.execute("SELECT * FROM usuarios WHERE email = '" + email + "' AND senha = '" + senha + "'")
```

**Depois:**
```python
cursor.execute("SELECT * FROM usuarios WHERE email = ? AND senha_hash = ?", (email, senha_hash))
```

Regra: todo valor que vem de fora (`request.args`, `request.json`, `req.body`) entra na query como parâmetro bindado (`?`, `%s`, `$1`, ou via ORM), nunca por f-string/concatenação/template literal.

---

## 3. Separar God File em Model/Controller/Routes (resolve #3 — God Class)

**Antes (`AppManager.js`, uma classe fazendo tudo):**
```javascript
class AppManager {
    initDb() { /* cria tabelas */ }
    setupRoutes(app) {
        app.post('/api/checkout', (req, res) => { /* SQL + regra de negócio + resposta HTTP, tudo aqui */ });
    }
}
```

**Depois:**
```javascript
// models/enrollmentModel.js
async function createEnrollment(db, userId, courseId) { /* só acesso a dados */ }

// controllers/checkoutController.js
async function checkout(req, res) {
    const result = await checkoutService.process(req.body);
    res.status(200).json(result);
}

// routes/index.js
router.post('/api/checkout', checkoutController.checkout);
```

Cada arquivo passa a ter um motivo só para mudar (SRP).

---

## 4. Extrair Controller de dentro da Rota (resolve #5 — Fat Controller)

**Antes:**
```python
@task_bp.route('/tasks', methods=['POST'])
def create_task():
    data = request.get_json()
    if not data.get('title') or len(data['title']) < 3:
        return jsonify({'error': '...'}), 400
    # ... 30 linhas de regra de negócio direto no handler
```

**Depois:**
```python
# controllers/task_controller.py
def create_task(payload):
    task, error = TaskService.create(payload)
    if error:
        return {"error": error}, 400
    return task.to_dict(), 201

# routes/task_routes.py
@task_bp.route('/tasks', methods=['POST'])
def create_task_route():
    body, status = task_controller.create_task(request.get_json())
    return jsonify(body), status
```

---

## 5. Introduzir Camada de Persistência (resolve #7 — Ausência de Repository)

**Antes:** SQL cru espalhado pelos handlers/controllers.
```python
# controllers.py — o handler HTTP fala direto com o banco
def buscar_produto(id):
    cursor = get_db().cursor()
    cursor.execute("SELECT * FROM produtos WHERE id = ?", (id,))
    row = cursor.fetchone()
    if not row:
        return jsonify({"erro": "Produto não encontrado"}), 404
    return jsonify(dict(row)), 200
```
```javascript
// AppManager.js — mesma coisa em Express
app.get('/api/courses/:id', (req, res) => {
    this.db.get("SELECT * FROM courses WHERE id = ?", [req.params.id], (err, course) => res.json(course));
});
```

**Depois:**
```python
# models/produto_repository.py
def find_by_id(db, produto_id):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM produtos WHERE id = ?", (produto_id,))
    return cursor.fetchone()

# controllers/produto_controller.py — sem SQL
def buscar_produto(id):
    row = produto_repository.find_by_id(get_db(), id)
    if not row:
        return {"erro": "Produto não encontrado"}, 404
    return dict(row), 200
```
Controllers e Models de domínio chamam o Repository; nenhum outro módulo monta SQL diretamente.

---

## 6. Substituir Model Procedural por Entidade de Domínio (resolve #8 — Model Anêmico)

**Antes:**
```python
# models.py — só funções soltas devolvendo dict
def get_produto_por_id(id):
    cursor.execute("SELECT * FROM produtos WHERE id = " + str(id))
    row = cursor.fetchone()
    return {"id": row["id"], "nome": row["nome"], ...}
```

**Depois:**
```python
# models/produto.py
class Produto:
    def __init__(self, id, nome, preco, estoque, categoria):
        self.id, self.nome, self.preco = id, nome, preco
        self.estoque, self.categoria = estoque, categoria

    def tem_estoque_suficiente(self, quantidade):
        return self.estoque >= quantidade

    def to_dict(self):
        return {"id": self.id, "nome": self.nome, "preco": self.preco,
                "estoque": self.estoque, "categoria": self.categoria}
```
A regra de negócio ("tem estoque suficiente?") passa a viver na entidade, não espalhada pelo controller.

---

## 7. Eliminar N+1 (resolve #9 — Query em loop)

**Antes:**
```python
for row in pedidos:
    cursor2.execute("SELECT * FROM itens_pedido WHERE pedido_id = " + str(row["id"]))
    for item in cursor2.fetchall():
        cursor3.execute("SELECT nome FROM produtos WHERE id = " + str(item["produto_id"]))
```

**Depois:**
```python
cursor.execute("""
    SELECT p.id AS pedido_id, i.produto_id, i.quantidade, pr.nome AS produto_nome
    FROM pedidos p
    JOIN itens_pedido i ON i.pedido_id = p.id
    JOIN produtos pr ON pr.id = i.produto_id
""")
# agrupe em memória por pedido_id em vez de disparar 1 query por item
```
Uma query com JOIN (ou uma query com `WHERE id IN (...)` batendo os IDs coletados) substitui N+1 round-trips por 1.

---

## 8. Deduplicar Lógica de Negócio (resolve #10 — Lógica duplicada)

**Antes:** a mesma regra reimplementada em vários handlers, enquanto o Model tem um método que ninguém chama.
```python
# routes/task_routes.py
if t.due_date and t.due_date < datetime.utcnow():
    task_data['overdue'] = t.status not in ('done', 'cancelled')

# routes/user_routes.py — cópia independente, que pode divergir
if t.due_date:
    if t.due_date < datetime.utcnow():
        if t.status != 'done' and t.status != 'cancelled':
            task_data['overdue'] = True

# routes/report_routes.py — terceira cópia, contando em vez de marcar
if t.due_date and t.due_date < datetime.utcnow() and t.status not in ('done', 'cancelled'):
    overdue_count += 1
```

**Depois:**
```python
# models/task.py — única fonte de verdade
class Task(db.Model):
    def is_overdue(self):
        if not self.due_date:
            return False
        return self.due_date < datetime.now(timezone.utc) and self.status not in ("done", "cancelled")

# routes/handlers — todos chamam o mesmo método
task_data["overdue"] = t.is_overdue()
overdue_count = sum(1 for t in tasks if t.is_overdue())
```
Toda rota/relatório que precisa dessa informação chama `task.is_overdue()` — zero reimplementações.

---

## 9. Proteger Endpoints Perigosos (resolve #4 — Endpoint sem autenticação)

**Antes:**
```python
@app.route("/admin/query", methods=["POST"])
def executar_query():
    query = request.get_json().get("sql", "")
    cursor.execute(query)   # SQL arbitrário, sem checar quem chamou
```

**Depois:** remova a capacidade de executar SQL arbitrário (não é um requisito de negócio legítimo) ou, se for estritamente necessário manter uma rota administrativa equivalente, proteja com middleware de autenticação + autorização de admin e nunca aceite SQL livre do body:
```python
@app.route("/admin/reset-db", methods=["POST"])
@require_admin_auth
def reset_database():
    ...
```

### 9b. Rotas de escrita sobre usuários/papéis

**Antes:** qualquer cliente anônimo apaga usuários ou se promove a admin.
```python
@user_bp.route("/users/<int:user_id>", methods=["PUT"])
def update_user(user_id):
    return user_controller.update_user(user_id, request.get_json())   # aceita {"role": "admin"}

@user_bp.route("/users/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):
    return user_controller.delete_user(user_id)
```

**Depois:** autentique a rota e autorize o campo sensível — sem bloquear o uso legítimo (o próprio usuário editar o seu perfil, cadastro público com papel padrão).
```python
# routes: o middleware identifica quem chama
@user_bp.route("/users/<int:user_id>", methods=["PUT"])
@require_auth
def update_user(user_id):
    return user_controller.update_user(user_id, request.get_json(), g.auth)

@user_bp.route("/users/<int:user_id>", methods=["DELETE"])
@require_admin
def delete_user(user_id):
    return user_controller.delete_user(user_id)

# controller: regra de autorização sobre o dado
PRIVILEGED_FIELDS = ("role", "active")

def update_user(user_id, data, auth):
    is_admin = auth["role"] == "admin"
    if not is_admin and auth["user_id"] != user_id:
        raise ForbiddenError("Só é possível alterar o próprio usuário")
    if not is_admin and any(f in data for f in PRIVILEGED_FIELDS):
        raise ForbiddenError("Só administradores alteram papel/status")
    ...

def create_user(data, auth=None):   # cadastro público continua aberto
    role = data.get("role", "user")
    if role != "user" and not (auth and auth["role"] == "admin"):
        raise ForbiddenError("Só administradores criam usuários com papel elevado")
    ...
```
Equivalente em Express: `router.delete("/users/:id", requireAdmin, controller.remove)` e a mesma checagem de `req.auth` no controller.

### Regras deste padrão

- **O finding só está resolvido quando o middleware está aplicado** a todas as rotas citadas nele. Criar o middleware e deixá-lo "disponível" sem uso não resolve nada — o relatório final não pode marcar isso como pendente.
- Exigir autenticação em rota destrutiva/privilegiada é **correção de segurança deliberada**, não quebra de contrato (ver `04-architecture-guidelines.md`, regra 5). A confirmação humana da Fase 2 já autorizou essa correção — não a adie para "decisão humana" posterior.
- Cubra **todas** as portas para o mesmo privilégio: se `PUT` permite trocar `role`, verifique também `POST` (criação) e qualquer outra rota que grave o mesmo campo.
- Prefira o controle mais estreito que fecha a falha: `require_admin` em ações exclusivamente administrativas (delete, reset); `require_auth` + regra de dono/campo onde usuários comuns têm uso legítimo.
- Se o projeto tem seed/fixture, garanta que existe um usuário admin com o qual a validação consiga obter token.
- Valide cada rota protegida **duas vezes** na Fase 3: sem token (espera 401/403) e com token adequado (espera o status original, ex: 200).

---

## 10. Substituir APIs Deprecated (resolve seção "APIs Deprecated" do catálogo)

**Antes:**
```python
created_at = datetime.utcnow()
```
**Depois:**
```python
from datetime import datetime, timezone
created_at = datetime.now(timezone.utc)
```

**Antes:**
```python
self.password = hashlib.md5(pwd.encode()).hexdigest()
```
**Depois:**
```python
from werkzeug.security import generate_password_hash, check_password_hash
self.password = generate_password_hash(pwd)
# na checagem: check_password_hash(self.password, pwd_informada)
```

---

## Checklist ao final da Fase 3

- [ ] Todo finding CRITICAL e HIGH do relatório tem uma transformação aplicada. Findings de **segurança** CRITICAL/HIGH nunca são adiados; só um finding arquitetural pode ficar pendente, com justificativa explícita no resumo final.
- [ ] Todo middleware de autenticação/autorização criado está aplicado às rotas citadas no finding (busque os usos, não só a definição).
- [ ] Rotas protegidas foram validadas sem token (401/403) e com token adequado (status original).
- [ ] Nenhum segredo literal restou no código.
- [ ] Nenhuma query é montada por concatenação de string com input externo.
- [ ] Arquivos antigos órfãos foram removidos, não deixados ao lado da nova estrutura.
- [ ] A aplicação sobe e os endpoints originais respondem.
