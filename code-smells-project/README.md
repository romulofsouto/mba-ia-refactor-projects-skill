# code-smells-project

API de E-commerce em Python/Flask usada como entrada do desafio `refactor-arch`, já refatorada para MVC.

## Como rodar

```bash
pip install -r requirements.txt
cp .env.example .env   # preencha SECRET_KEY, ADMIN_TOKEN e as senhas de seed
python app.py
```

A aplicação sobe em `http://localhost:5000`. O banco SQLite (`DATABASE_PATH`, padrão `loja.db`) é criado automaticamente no primeiro boot, já com produtos e usuários de exemplo. As senhas desses usuários vêm de `SEED_ADMIN_PASSWORD` / `SEED_CLIENTE_PASSWORD`. Sem elas, uma senha aleatória é usada.

Em produção, use um servidor WSGI (ex: `gunicorn "app:app"`) com `DEBUG=false`.

## Estrutura

```
app.py                 # composition root: cria a app, registra middlewares e rotas
config/settings.py     # configuração lida de variáveis de ambiente
models/                # entidades de domínio + acesso ao banco (único lugar com SQL)
services/              # orquestração multi-tabela (pedido) e notificações
controllers/           # traduzem entrada já parseada ⇄ Model/Service ⇄ (payload, status)
routes/                # blueprints: método + path → controller
middlewares/           # autenticação de admin e handler de erro centralizado
```

## Endpoints administrativos

`POST /admin/reset-db` exige o header `X-Admin-Token` igual a `ADMIN_TOKEN`. Sem `ADMIN_TOKEN` configurado, o endpoint responde 403. O antigo `POST /admin/query` (execução de SQL arbitrário) foi removido.
