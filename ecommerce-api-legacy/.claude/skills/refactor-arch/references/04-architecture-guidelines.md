# Guidelines de Arquitetura Alvo — MVC (Fase 3)

O alvo da refatoração é sempre MVC, adaptado ao contexto de uma API HTTP (sem template rendering na maioria dos casos — "View" aqui é a camada de rota/serialização, não HTML).

## Camadas e responsabilidades

### Model
- Dono dos dados e das regras de domínio (validação de invariantes, cálculos de negócio, o que significa "estar atrasado", "estar em estoque", etc.).
- Encapsula o acesso ao banco (ou delega a um Repository, se o acesso for complexo o bastante para justificar separar). Nenhum outro lugar do sistema deve montar SQL/queries diretamente.
- **Nunca** conhece o protocolo HTTP — não recebe `request`, não devolve status code, não formata JSON de resposta.
- Em ORMs (SQLAlchemy, Sequelize, etc.), o Model é a própria classe mapeada à tabela; métodos de validação e regra de negócio vivem nela ou em um módulo de domínio próximo.

### View / Routes
- Mapeia método HTTP + path para uma função de Controller. Só isso.
- Não contém regra de negócio, não acessa o banco diretamente, não faz cálculo.
- Faz a serialização de entrada/saída (parse do JSON da request, formatação da resposta) quando essa lógica for puramente mecânica; validação de regra de negócio fica no Model/Controller.

### Controller
- Orquestra: recebe dados já parseados da rota, valida o formato de entrada (campos obrigatórios, tipos), chama o Model (ou Service) para aplicar a regra de negócio, e traduz o resultado em uma resposta HTTP (status code + payload).
- Não executa SQL. Não decide regra de negócio complexa sozinho — delega ao Model/Service.
- Fino: se um Controller tem múltiplas dezenas de linhas de `if` de regra de negócio, essa lógica pertence a um Model ou Service.

### Service (camada opcional, adicione quando fizer sentido)
- Use quando uma operação orquestra múltiplos Models/tabelas em um fluxo com efeitos colaterais (ex: checkout que cria usuário + matrícula + pagamento + log de auditoria + notificação). Um Model sozinho não deveria coordenar outras tabelas.
- Para CRUD simples de uma única entidade, não force uma camada de Service — o Model já resolve, e uma camada extra vazia é abstração especulativa.

### Middlewares / Error Handling
- Handler de erro centralizado (um único lugar que transforma exceções em resposta HTTP padronizada), em vez de cada Controller decidir o formato de erro sozinho.
- Autenticação/autorização como middleware aplicado às rotas que precisam, não checagem manual copiada em cada handler.

### Config
- Um módulo dedicado (`config/settings.py`, `config/index.js`, etc.) que lê variáveis de ambiente (`os.environ`, `process.env`, `python-dotenv`) e expõe valores tipados. Nenhum segredo literal no código-fonte.
- `.env.example` documenta as variáveis esperadas sem conter valores reais; `.env` real nunca é commitado (adicione ao `.gitignore` se ainda não estiver).

### Composition Root (entrypoint)
- Um único arquivo (`app.py`, `src/app.js`) monta a aplicação: cria a instância do framework, registra rotas/blueprints/routers, registra middlewares, sobe o servidor. Não contém regra de negócio nem definição de rota inline.

## Estruturas de referência por stack

### Python/Flask

```
src/
├── config/
│   └── settings.py
├── models/
│   ├── produto_model.py
│   └── usuario_model.py
├── controllers/
│   ├── produto_controller.py
│   └── pedido_controller.py
├── routes/
│   └── routes.py
├── middlewares/
│   └── error_handler.py
└── app.py            # composition root
```

Para um projeto que já tem `models/`, `routes/`, `services/` (caso parcialmente organizado), não recrie a árvore do zero: **adicione** o que falta (ex: `controllers/` se a lógica ainda está nas rotas, `config/` se os segredos estão hardcoded) e mova o código existente para dentro da convenção, em vez de descartar a organização que já é boa.

### Node.js/Express

```
src/
├── config/
│   └── index.js
├── models/
│   ├── userModel.js
│   └── courseModel.js
├── controllers/
│   ├── checkoutController.js
│   └── reportController.js
├── routes/
│   └── index.js
├── middlewares/
│   └── errorHandler.js
└── app.js             # composition root
```

## Regras que valem para qualquer stack

1. Nenhuma camada abaixo do Controller conhece o protocolo HTTP.
2. Nenhuma camada acima do Model/Repository monta SQL.
3. Toda config sensível vem de variável de ambiente, nunca de literal no código.
4. Erros são tratados em um lugar central, não replicados em cada handler.
5. O contrato público da API (rotas, métodos, formato de payload) não muda por causa da refatoração interna — só a organização interna muda.
