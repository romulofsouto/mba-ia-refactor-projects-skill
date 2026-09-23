# task-manager-api

API de Task Manager em Python/Flask usada como entrada do desafio `refactor-arch`, já refatorada para MVC.

## Como rodar

```bash
pip install -r requirements.txt
cp .env.example .env   # preencha SECRET_KEY (e SMTP_* se for enviar e-mails)
python seed.py
python app.py
```

A aplicação sobe em `http://localhost:5000`. O `seed.py` popula o banco SQLite (`DATABASE_URL`, padrão `instance/tasks.db`) com usuários, categorias e tasks de exemplo. **Rode-o antes do primeiro boot**, senão os endpoints retornam listas vazias.

Em produção, use um servidor WSGI (ex: `gunicorn "app:app"`) com `DEBUG=false`.

## Estrutura

```
app.py                 # composition root: cria a app, registra middlewares e rotas
config/settings.py     # configuração lida de variáveis de ambiente
models/                # entidades SQLAlchemy + regras de domínio, validação e consultas
controllers/           # validam a entrada, chamam Model/Service e devolvem (payload, status)
services/              # relatórios multi-tabela, token de login, notificações por e-mail
routes/                # blueprints: método + path → controller
middlewares/           # handler de erro centralizado e autenticação por token
utils/dates.py         # utc_now() (substitui datetime.utcnow, deprecated)
```

## Autenticação

`POST /login` devolve um token assinado com `SECRET_KEY` (válido por `AUTH_TOKEN_MAX_AGE` segundos). Os decorators `require_auth` / `require_admin` em `middlewares/auth.py` validam o header `Authorization: Bearer <token>`, mas **ainda não estão aplicados a nenhuma rota**, para preservar o contrato público atual.

Senhas usam `werkzeug.security` (scrypt). Hashes MD5 gravados pela versão antiga continuam aceitos e são migrados automaticamente no próximo login.
