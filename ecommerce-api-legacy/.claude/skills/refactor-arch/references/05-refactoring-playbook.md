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

**Antes:** SQL cru espalhado pelos handlers/models.

**Depois:**
```python
# models/produto_repository.py
def find_by_id(db, produto_id):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM produtos WHERE id = ?", (produto_id,))
    return cursor.fetchone()
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

**Antes:** `is_overdue` reimplementado em `task_routes.py`, `user_routes.py` e `models/task.py`.

**Depois:**
```python
# models/task.py — única fonte de verdade
class Task(db.Model):
    def is_overdue(self):
        if not self.due_date:
            return False
        return self.due_date < datetime.now(timezone.utc) and self.status not in ("done", "cancelled")
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

- [ ] Todo finding CRITICAL e HIGH do relatório tem uma transformação aplicada (ou uma justificativa explícita de por que não, se algo foi propositalmente adiado).
- [ ] Nenhum segredo literal restou no código.
- [ ] Nenhuma query é montada por concatenação de string com input externo.
- [ ] Arquivos antigos órfãos foram removidos, não deixados ao lado da nova estrutura.
- [ ] A aplicação sobe e os endpoints originais respondem.
