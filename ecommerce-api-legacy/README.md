# ecommerce-api-legacy

LMS API (com fluxo de checkout) em Node.js/Express usada como entrada do desafio `refactor-arch`.

## Como rodar

```bash
npm install
cp .env.example .env   # preencha ADMIN_TOKEN (e PAYMENT_GATEWAY_KEY)
npm start
```

As rotas administrativas (`GET /api/admin/financial-report` e `DELETE /api/users/:id`) exigem o header `X-Admin-Token` com o valor de `ADMIN_TOKEN`. Sem `ADMIN_TOKEN` configurado elas respondem `401`.

## Estrutura

```
src/
├── app.js            # composition root
├── config/           # env, logger, conexão/schema/seed do SQLite
├── models/           # acesso a dados (SQL parametrizado)
├── services/         # checkout, relatório, gateway de pagamento, hash de senha
├── controllers/      # HTTP ⇄ service
├── routes/           # mapeamento de rotas
└── middlewares/      # auth de admin, erro centralizado, wrapper async
```

A aplicação sobe em `http://localhost:3000`. O banco SQLite é em memória e já carrega seeds automaticamente no boot.

Exemplos de requisições estão em `api.http`.
