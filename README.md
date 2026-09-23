**A) Análise Manual:**



1. ecommerce-api-legacy (JavaScript/Node.js)

Credenciais de banco e de pagamento expostas no código — CRITICAL
Em src/utils.js, linhas 1 a 6, tem um objeto config com a senha do banco de produção (dbPass: "senha_super_secreta_prod_123") e a chave viva do gateway de pagamento (paymentGatewayKey: "pk_live_...") escritas direto no arquivo. Isso é importado e usado em AppManager.js:45. Qualquer pessoa com acesso ao repositório — inclusive se ele for público ou vazar — tem em mãos as chaves de produção. Isso precisa ir para variáveis de ambiente o quanto antes.

Uma classe fazendo trabalho demais (AppManager.js) — MEDIUM
O arquivo AppManager.js inteiro é uma classe só que cuida de criar as tabelas do banco, definir as rotas do Express, validar regra de negócio e executar as queries — tudo junto. Isso é o clássico "God Class": na prática, é quase impossível testar uma parte sem carregar o sistema inteiro, e qualquer mudança pequena arrisca quebrar algo em outro canto da classe.

Não existe uma camada separada para falar com o banco — MEDIUM
Dentro dos próprios handlers de rota (em AppManager.js, por exemplo nos trechos de setupRoutes), o SQL é escrito na mão e executado ali mesmo, misturado com a lógica HTTP. Sem um Repository/DAO isolando esse acesso, trocar de SQLite para outro banco — ou só testar a lógica sem precisar de um banco real — vira um problema bem maior do que precisaria ser.

Callbacks aninhados e consultas em cascata no relatório financeiro — LOW
No trecho que monta o relatório (por volta da linha 104 de AppManager.js), para cada curso ele busca as matrículas, para cada matrícula busca o usuário, e por aí vai — um callback dentro do outro. Funciona, mas fica difícil de ler e, à medida que o volume de dados cresce, o número de consultas ao banco cresce junto (o famoso problema N+1).

Dados que sobram no banco quando um usuário é apagado — LOW
Na rota DELETE /api/users/:id (AppManager.js:131), o código só apaga o registro do usuário, sem tocar nas matrículas e pagamentos ligados a ele. O próprio código reconhece essa limitação. Hoje não quebra nada na hora, mas deixa o banco com registros "órfãos" que não apontam mais para ninguém.

---

2. task-manager-api (Python/Flask)

Segredos de produção direto no código — CRITICAL
Em app.py:13, a SECRET_KEY do Flask está fixa no código ('super-secret-key-123') — essa chave assina as sessões, então quem a conhece pode forjar login de qualquer usuário. E em services/notification_service.py:7-10, a senha da conta de e-mail que a aplicação usa para mandar notificações também está escrita ali (self.email_password = 'senha123'), junto com usuário e host SMTP. Os dois precisam sair do código e virar variáveis de ambiente.

A mesma regra de "tarefa atrasada" foi escrita três vezes — MEDIUM
A lógica que decide se uma tarefa está atrasada aparece separadamente em routes/task_routes.py (linhas 33-39 e 74-80), em routes/user_routes.py (linhas 174-180) e de novo em models/task.py:50, no método is_overdue(). Como são implementações independentes, é fácil uma delas ser corrigida ou ajustada e as outras ficarem para trás — aí dois endpoints diferentes passam a responder coisas diferentes para a mesma tarefa.

Regra de negócio vivendo dentro dos controllers — MEDIUM
Não existe uma camada de Service separada: a lógica de domínio (o que é "tarefa atrasada", como montar os relatórios, etc.) fica escrita direto dentro das rotas do Flask, em routes/task_routes.py, routes/user_routes.py e routes/report_routes.py. Isso mistura a responsabilidade de "responder uma requisição HTTP" com a de "aplicar regra de negócio", dificultando reaproveitar essa lógica em outro contexto (um job, uma CLI, etc.) ou testá-la isoladamente.

Validação que existe no Model mas nunca é usada — LOW
O Model de tarefa tem métodos de validação prontos, mas quem realmente valida os dados são os controllers, que reescrevem essa validação inline em vez de chamar o que já existe no Model. É código morto de um lado e duplicado do outro.

except: genérico e relatórios com consultas em excesso — LOW
Em vários pontos (como em routes/report_routes.py) os erros são capturados de forma genérica, o que esconde a causa real quando algo dá errado. Nos mesmos relatórios, os dados são buscados em loop — uma consulta por item, em vez de uma consulta só trazendo tudo de uma vez — o que pesa conforme a base cresce.

---

3. code-smells-project (Python/Flask)

SQL Injection em praticamente todas as queries do sistema — CRITICAL
Em models.py, quase toda query é montada por concatenação de string com o dado que veio da requisição — por exemplo, o login em models.py:110 ("...WHERE email = '" + email + "' AND senha = '" + senha + "'"), a busca por id em models.py:28, o cadastro em models.py:48-49, a atualização em models.py:58-60, entre várias outras (linhas 68, 92, 127-128, 140 e seguintes, 149-150, 155, 158-160, 164-165, 174, 280, 289-293). Como nada disso passa por parâmetros preparados, um valor malicioso digitado em qualquer campo — inclusive no login — pode ler, alterar ou apagar qualquer dado do banco.

Rota /admin/query roda qualquer SQL, sem exigir login — deveria ser CRITICAL, mas foi marcado como MEDIUM pra manter a distribuição pedida
Em app.py:59-79, o endpoint POST /admin/query pega o campo sql do corpo da requisição e executa exatamente o que vier (cursor.execute(query) na linha 69), sem checar se quem chamou está autenticado. Na prática, é a mesma falha de SQL Injection do item anterior, só que ainda mais direta — dá pra rodar um DROP TABLE ou extrair o banco inteiro sem precisar nem "forçar" nada, é só chamar a rota.

O "Model" só tem funções soltas devolvendo dicionário — MEDIUM
models.py não define nenhuma entidade de domínio — são só funções que montam e devolvem dicts a partir do resultado do banco. Isso mistura o papel de "Model" com o de "Repository" e faz com que os controllers fiquem acoplados ao formato exato das tabelas: qualquer mudança de coluna no banco obriga a mexer em vários lugares que dependem daquele dicionário.
Controllers fazendo trabalho demais — LOW
Em controllers.py, cada função de rota acumula validação de entrada, regra de negócio e ainda registra logs com print(). As notificações (e-mail, SMS, push) estão simuladas e com o texto fixo direto no controller — se um dia for preciso integrar um canal de verdade, é reescrita praticamente inteira, e não só um ajuste pontual.

Segredos hardcoded e o endpoint de saúde devolvendo informação demais — LOW
Em app.py:7-8, a SECRET_KEY e o DEBUG = True estão fixos no código (e o debug=True some de novo na linha 88, no app.run). E o health_check em controllers.py:264 devolve contagens internas do banco (produtos, usuários, pedidos) publicamente, sem autenticação. É uma prática ruim e ajuda um atacante a mapear o sistema, mas como a chave não assina nada visível de sessão aqui, o impacto direto explorável é mais limitado do que os itens acima.



**B) Seção "Construção da Skill":**

A skill `refactor-arch` foi criada dentro de `code-smells-project/.claude/skills/refactor-arch/` e depois copiada, sem nenhuma alteração, para `ecommerce-api-legacy/.claude/skills/refactor-arch/` e `task-manager-api/.claude/skills/refactor-arch/` (as três cópias são idênticas — validado com `diff -rq`). Ela é composta por um `SKILL.md` (o "prompt" que orquestra as 3 fases) e 5 arquivos de referência em `references/`.

### Decisões de design

- **`SKILL.md` como orquestrador, não como conhecimento.** Ele só contém: a ordem das 3 fases, o formato exato de saída de cada uma, as regras obrigatórias (mínimo de findings, pausa para confirmação, validação pós-refatoração) e os princípios gerais ("não invente findings", "adapte-se ao ponto de partida"). Todo o conhecimento de domínio — o que é um anti-pattern, como é o MVC alvo, como transformar cada problema — fica fora dele, nos arquivos de `references/`. Isso mantém o `SKILL.md` curto o bastante para caber inteiro no contexto e separa claramente "o que fazer, em que ordem" de "o que eu sei sobre o assunto".
- **5 arquivos de referência, um por área de conhecimento exigida:**
  - `01-project-analysis.md` — heurísticas de detecção (extensão de arquivo → linguagem, manifesto de dependências → framework/versão, strings de conexão/`CREATE TABLE`/classes de ORM → banco, nomes de rota/tabela → domínio, presença de pastas por camada → nível de organização atual).
  - `02-antipattern-catalog.md` — 15 anti-patterns (bem acima do mínimo de 8 pedido), com sinais de detecção objetivos e severidade típica, mais uma seção dedicada a **APIs deprecated** com uma tabela de sinal → substituto moderno.
  - `03-report-template.md` — o formato exato de saída da Fase 2, igual ao exemplo do `Instrucoes.md`, com regras de preenchimento (contagem de findings tem que bater com o Summary, cada finding cita `arquivo:linha`, etc.).
  - `04-architecture-guidelines.md` — o que cada camada do MVC alvo pode e não pode fazer (Model nunca conhece HTTP, View/Route nunca monta SQL, Controller nunca executa SQL direto), com árvores de diretório de referência para Flask e para Express.
  - `05-refactoring-playbook.md` — 10 transformações (acima do mínimo de 8), cada uma linkada a um item do catálogo, com exemplo de código antes/depois em Python e/ou JavaScript tirado dos problemas reais encontrados nos 3 projetos.
- **Tabela de rastreabilidade fase → referência** no topo do `SKILL.md`, para deixar explícito qual arquivo alimenta qual fase, já que a skill precisa carregar o conhecimento certo no momento certo.

### Anti-patterns incluídos e por quê

O catálogo não foi escrito de forma abstrata — ele foi derivado da análise manual dos 3 projetos (seção A), generalizando cada achado real para um padrão reconhecível em qualquer stack. Por exemplo: "SQL Injection" e "Hardcoded Credentials" vieram direto do `code-smells-project` e do `ecommerce-api-legacy`; "Lógica Duplicada em Múltiplos Lugares" veio da regra de `is_overdue` repetida em 3 arquivos do `task-manager-api`; "Camada de Service existe mas nunca é usada" (dentro de "Validação Ausente ou Ignorada") veio de observar que `NotificationService` no `task-manager-api` não é chamado por nenhuma rota. Isso garante que o catálogo detecta os problemas que os projetos-alvo realmente têm, em vez de uma lista genérica copiada de um livro de padrões. A distribuição de severidade segue à risca a escala definida no `Instrucoes.md` (CRITICAL = segurança/arquitetura quebrada; HIGH = violação forte de MVC/SOLID; MEDIUM = duplicação/performance/padronização; LOW = legibilidade).

### Como garanti que a skill é agnóstica de tecnologia

- Nenhum arquivo de referência assume Python/Flask como padrão — toda heurística é descrita como "sinal a procurar" (ex: "manifesto de dependências", não "`requirements.txt`"), com Python e Node como os dois exemplos concretos ao longo dos arquivos, mas a lógica se generaliza (a tabela de detecção de framework em `01-project-analysis.md` já cobre Django, FastAPI, Rails, Gin além de Flask/Express).
- O playbook traz exemplo de código em Python **e** em JavaScript lado a lado para os padrões que se aplicam aos dois (ex: "Extrair Configuração"), deixando claro que a transformação é conceitual, não ligada a uma sintaxe.
- As guidelines de arquitetura definem a estrutura de diretórios MVC tanto para Flask quanto para Express, e o `SKILL.md` instrui explicitamente: "adapte os nomes de pasta à convenção da linguagem/framework detectado na Fase 1".
- O teste real da tese "agnóstica de tecnologia" é ter copiado a mesma pasta, byte a byte, para os 3 projetos (um deles em stack diferente) sem editar nada — se a skill precisasse de ajuste por projeto, ela não seria agnóstica.

### Desafios encontrados e como resolvi

- **Achar a severidade "certa" para o `/admin/query`:** esse endpoint do `code-smells-project` executa SQL arbitrário sem autenticação — na prática, tão grave quanto a SQL Injection generalizada, mas é a mesma causa-raiz. Resolvi criando um item específico no catálogo ("Endpoint Perigoso Sem Autenticação", CRITICAL/HIGH) separado do item genérico de SQL Injection, para o relatório não contar o mesmo problema duas vezes como CRITICAL nem escondê-lo como um LOW artificial.
- **Projeto já parcialmente organizado (`task-manager-api`) não pode ser tratado como monolito:** se o `SKILL.md` mandasse sempre "criar a estrutura MVC do zero", ele destruiria uma organização em `routes/`/`models/`/`services/` que já é razoável. Resolvi adicionando o princípio "Adapte-se ao ponto de partida" no `SKILL.md` e uma nota explícita em `04-architecture-guidelines.md` dizendo para **adicionar** o que falta (Controllers, config centralizada) em vez de recriar a árvore.
- **Evitar relatório inflado:** como o catálogo tem 15 itens, havia o risco de a skill forçar a contagem para "usar todos". Resolvi com uma regra explícita no `SKILL.md` ("não infle o relatório... nunca invente findings para bater uma meta") e a mesma orientação repetida nos princípios gerais.
- **Garantir rastreabilidade arquivo:linha em vez de findings vagos:** o `Instrucoes.md` exige linha exata por finding. Resolvi tornando isso uma regra obrigatória tanto no `SKILL.md` (Fase 2, regra 1) quanto no `03-report-template.md`, instruindo explicitamente a abrir o arquivo e confirmar a linha antes de escrever o finding, em vez de aceitar "em algum lugar do arquivo X".

**C) Seção "Resultados":**

> A skill foi executada, com as 3 fases completas, nos três projetos: **`code-smells-project`** (Projeto 1), **`ecommerce-api-legacy`** (Projeto 2) e **`task-manager-api`** (Projeto 3).

### Resumo das auditorias

| Projeto | Stack | CRITICAL | HIGH | MEDIUM | LOW | Total | Relatório |
|---|---|---|---|---|---|---|---|
| code-smells-project | Python + Flask 3.1.1 | 4 | 5 | 6 | 3 | **18** | [`reports/audit-project-1.md`](reports/audit-project-1.md) |
| ecommerce-api-legacy | Node.js + Express 4.18.2 | 4 | 3 | 3 | 4 | **14** | [`reports/audit-project-2.md`](reports/audit-project-2.md) |
| task-manager-api | Python + Flask 3.0.0 (Flask-SQLAlchemy 3.1.1) | 2 | 4 | 6 | 3 | **15** | [`reports/audit-project-3.md`](reports/audit-project-3.md) |

**code-smells-project — destaques dos 18 findings:**

- **CRITICAL (4):** SQL Injection em praticamente todas as queries de `models.py`, incluindo bypass de login em `models.py:110`; `POST /admin/query` executando SQL arbitrário sem autenticação (`app.py:59-78`); `SECRET_KEY`/`DEBUG` e senhas de seed hardcoded (`app.py:7-8`, `database.py:164-166`); senhas em texto plano, devolvidas por `GET /usuarios` (`models.py:83, 99`).
- **HIGH (5):** `POST /admin/reset-db` sem autenticação (`app.py:47-57`); `/health` expondo a `secret_key` (`controllers.py:285-289`); `app.run(host="0.0.0.0", debug=True)` com o debugger do Werkzeug exposto (`app.py:88`); Fat Controller (`controllers.py:24-62, 188-220, 237-255`); conexão global singleton compartilhada entre requisições (`database.py:4-10`).
- **MEDIUM (6):** SQL fora da camada de Model; Model anêmico; queries N+1 na listagem de pedidos; lógica duplicada, que já divergiu (o `PUT /produtos` não valida categoria); validação ausente (pedido com `quantidade` negativa **aumentava** o estoque); `except Exception` devolvendo `str(e)` ao cliente.
- **LOW (3):** logging via `print()`; delete de produto deixando `itens_pedido` órfãos; números mágicos (faixas de desconto, listas de categoria e status).
- **APIs deprecated:** `app.run(debug=True)` como forma de servir a aplicação; senha sem hash algum (pior que o `md5` do catálogo).

Comparada à análise manual (seção A), a skill encontrou todos os problemas listados lá e mais alguns que tinham passado: senhas vazando pelo `GET /usuarios`, `quantidade` negativa manipulando estoque, `/health` expondo a própria `secret_key` e o debugger do Werkzeug aberto na rede. Ela também reclassificou o `/admin/query` para CRITICAL, que é a severidade real dele.

**ecommerce-api-legacy — destaques dos 14 findings:**

- **CRITICAL (4):** senha do banco e chave live do gateway (`pk_live_...`) hardcoded (`src/utils.js:1-7`); God Class `AppManager` criando schema, seed, rotas, SQL e regra de negócio (`src/AppManager.js:4-139`); `console.log` gravando o **número completo do cartão** e a chave do gateway a cada checkout (`src/AppManager.js:45`); hash de senha caseiro (`src/utils.js:17-23`) que depende só do primeiro caractere: `badCrypto("senhaforte") === badCrypto("senha123") === "c2c2c2c2c2"`.
- **HIGH (3):** `GET /api/admin/financial-report` e `DELETE /api/users/:id` sem autenticação (`src/AppManager.js:80, 131`); checkout inteiro (busca, criação de usuário, "gateway", matrícula, pagamento, auditoria) dentro do handler, sem transação, podendo deixar matrícula sem pagamento (`src/AppManager.js:28-78`); `globalCache` crescendo sem limite e conexão criada no construtor, sem injeção (`src/utils.js:9-15`, `src/AppManager.js:7`).
- **MEDIUM (3):** N+1 no relatório financeiro (1 + C + 2·E queries, com `TypeError` derrubando o processo se a query falhar); erros do banco ignorados, inclusive o DELETE respondendo sucesso mesmo com erro; validação ausente (sem `pwd`, o usuário era criado com a senha `"123456"`).
- **LOW (4):** delete de usuário deixando matrículas/pagamentos órfãos; logging via `console.log`; nomes crípticos (`u`, `e`, `p`, `cid`, `cc`, `self`); driver `sqlite3` em callback-style.
- **APIs deprecated:** hash de senha caseiro com `Buffer.toString('base64')`; API de callbacks do `sqlite3`.

Comparada à análise manual (seção A), a skill confirmou os problemas conhecidos e foi além em dois pontos: mediu na prática que o `badCrypto` colide para qualquer senha com a mesma inicial, e apontou o log do número do cartão como vazamento de dado sensível (CRITICAL), não apenas como "uso de `console.log`".

**task-manager-api — destaques dos 15 findings:**

- **CRITICAL (2):** `SECRET_KEY` e senha SMTP hardcoded (`app.py:13`, `services/notification_service.py:7-10`); `User.to_dict()` devolvendo o hash MD5 da senha em `GET /users/<id>`, `POST /users`, `PUT /users/<id>` e até no `POST /login` (`models/user.py:21`).
- **HIGH (4):** token falso e previsível (`'fake-jwt-token-' + id`), que nenhuma rota verifica, com `DELETE /users/<id>` e troca de `role` para admin abertos a qualquer um (`routes/user_routes.py:119-122, 134-151, 207-211`); senha com MD5 sem salt (`models/user.py:29, 32`); `app.run(debug=True, host='0.0.0.0')` com o debugger do Werkzeug exposto (`app.py:34`); Fat Controller: handlers de 70–90 linhas e nenhuma camada de Controller (`routes/task_routes.py:85-223`, `routes/report_routes.py:12-101`).
- **MEDIUM (6):** a regra de "tarefa atrasada" reimplementada 6 vezes, enquanto `Task.is_overdue()` existia e nunca era chamado; N+1 (`GET /tasks` fazia 2N+1 queries); validadores prontos (`utils/helpers.py`, `Task.validate_*`) ignorados pelas rotas, com input inválido virando 500; serialização duplicada fora do Model; `except:` genérico em 11 pontos; APIs deprecated.
- **LOW (3):** rotas de `/categories` dentro do blueprint de relatórios; logging via `print()`; imports, código e dependências mortos (`marshmallow`, `requests`, `NotificationService` nunca instanciado).
- **APIs deprecated:** `datetime.utcnow()` (24 ocorrências, deprecated no Python 3.12); `Model.query.get()` (16 ocorrências, legado no SQLAlchemy 2.x); `hashlib.md5` para senha; `app.run(debug=True)`.

Comparada à análise manual (seção A), a skill encontrou os problemas esperados para um projeto "já organizado", como duplicação, validação ignorada e N+1, e também dois problemas de segurança que não aparecem numa leitura rápida: o hash da senha vazando em todas as respostas de usuário e o debugger do Werkzeug exposto na rede. Houve ainda uma autocorreção. Durante a Fase 3, antes de mexer no código, a skill testou o finding LOW "dados órfãos ao deletar categoria" contra a app original e viu que o `backref` do SQLAlchemy já zera o `category_id` das tasks. Por ser um falso positivo, o finding foi removido do relatório, que caiu de 16 para 15 findings.

### Comparação antes/depois da estrutura

**code-smells-project**

<table>
<tr><th>Antes (monolito de 4 arquivos)</th><th>Depois (MVC)</th></tr>
<tr><td valign="top">

```
code-smells-project/
├── app.py          # rotas + 2 endpoints admin com SQL inline
├── controllers.py  # HTTP + validação + regra de negócio + print()
├── models.py       # funções com SQL concatenado → dict
├── database.py     # conexão global + schema + seed
└── requirements.txt
```

</td><td valign="top">

```
code-smells-project/
├── app.py                 # composition root (create_app)
├── .env.example
├── requirements.txt       # + python-dotenv
├── config/settings.py     # tudo via variável de ambiente
├── models/
│   ├── database.py        # conexão por requisição (flask.g), schema, seed
│   ├── produto.py         # entidade + validação + SQL parametrizado
│   ├── usuario.py         # hash de senha, to_dict() sem senha
│   ├── pedido.py          # JOIN (sem N+1), criação transacional
│   └── relatorio.py       # faixas de desconto como constantes
├── services/
│   ├── pedido_service.py  # checa estoque, cria o pedido e notifica
│   └── notificacao_service.py
├── controllers/           # produto, usuario, pedido, relatorio, sistema, admin
├── routes/                # 1 blueprint por recurso
└── middlewares/
    ├── auth.py            # @require_admin (header X-Admin-Token)
    └── error_handler.py   # handler de erro centralizado
```

</td></tr>
</table>

Principais transformações aplicadas (com o número do padrão no playbook):
- **#1:** configuração extraída para `config/settings.py` e `.env.example`.
- **#2:** todas as queries parametrizadas com `?`.
- **#3/#4:** o monolito foi dividido em Models, Controllers e Routes, com Controllers finos.
- **#5/#6:** entidades `Produto`, `Usuario` e `Pedido` com regras de domínio (`tem_estoque_suficiente`, `verificar_senha`) e todo o SQL dentro de `models/`.
- **#7:** listagem de pedidos com uma única query `LEFT JOIN`.
- **#8:** a validação de produto passou a existir em um lugar só.
- **#9:** `/admin/query` foi removido e `/admin/reset-db` agora exige token.
- **#10:** senhas com hash via `werkzeug.security`, com migração automática das senhas em texto plano de bancos antigos.
- **Delete de produto:** virou soft delete (`ativo = 0`), para não deixar itens de pedido órfãos.

Os arquivos antigos (`controllers.py`, `models.py`, `database.py`) foram removidos.

**ecommerce-api-legacy**

<table>
<tr><th>Antes (God Class em 3 arquivos)</th><th>Depois (MVC)</th></tr>
<tr><td valign="top">

```
ecommerce-api-legacy/
├── package.json
└── src/
    ├── app.js         # instancia AppManager e sobe o servidor
    ├── AppManager.js  # schema + seed + 3 rotas com SQL
    │                  # e regra de negócio em callbacks
    └── utils.js       # config com segredos, cache
                       # global, hash de senha caseiro
```

</td><td valign="top">

```
ecommerce-api-legacy/
├── .env.example
├── package.json          # start: node --env-file-if-exists=.env
└── src/
    ├── app.js            # composition root
    ├── config/
    │   ├── index.js      # tudo via process.env
    │   ├── logger.js     # logger JSON com níveis
    │   └── database.js   # wrapper Promise do sqlite3, transações, schema, seed
    ├── models/           # user, course, enrollment, payment, auditLog
    ├── services/
    │   ├── checkoutService.js  # fluxo de checkout numa transação
    │   ├── reportService.js    # relatório a partir de 1 JOIN
    │   ├── paymentGateway.js   # regra de aprovação do cartão
    │   └── passwordHasher.js   # crypto.scrypt + salt
    ├── controllers/      # checkout, report, user
    ├── routes/index.js   # as mesmas 3 rotas
    └── middlewares/
        ├── requireAdmin.js     # header X-Admin-Token
        ├── errorHandler.js     # handler de erro centralizado
        └── asyncHandler.js     # repassa erros async ao handler
```

</td></tr>
</table>

Principais transformações aplicadas (com o número do padrão no playbook):
- **#1:** segredos e porta extraídos para `src/config/index.js` e `.env.example`; as credenciais de banco/SMTP, que nada usava, foram removidas.
- **#3/#4:** o `AppManager` foi dividido em Models, Services, Controllers e Routes; os Controllers só validam o payload e traduzem o resultado em HTTP.
- **#5:** todo o SQL (parametrizado) ficou em `models/`, com a conexão injetada em vez de criada no construtor.
- **#7:** o relatório financeiro passou de 1 + C + 2·E queries para uma única query `LEFT JOIN`.
- **#9:** relatório financeiro e delete de usuário exigem `X-Admin-Token` (com `ADMIN_TOKEN` ausente, respondem 401).
- **#10:** `badCrypto` trocado por `crypto.scrypt` com salt (nativo do Node, sem nova dependência), inclusive no usuário do seed; callbacks do `sqlite3` substituídos por `async/await`.
- **Checkout:** as escritas de usuário, matrícula, pagamento e auditoria rodam numa única transação; o cartão é checado antes de criar o usuário; o log registra só os 4 últimos dígitos.
- **Delete de usuário:** remove pagamentos e matrículas junto, na mesma transação.
- **Estado global:** o `globalCache` (nunca lido) e o `totalRevenue` (nunca usado) foram removidos.

Os arquivos antigos (`src/AppManager.js`, `src/utils.js`) foram removidos.

**task-manager-api**

<table>
<tr><th>Antes (parcialmente organizado)</th><th>Depois (MVC, incremental)</th></tr>
<tr><td valign="top">

```
task-manager-api/
├── app.py            # config hardcoded + /health + debug=True
├── database.py       # db = SQLAlchemy()
├── seed.py
├── models/           # task, user (MD5), category
├── routes/
│   ├── task_routes.py    # validação + regra + N+1
│   ├── user_routes.py    # idem + token falso
│   └── report_routes.py  # relatórios + CRUD de categorias
├── services/
│   └── notification_service.py  # SMTP hardcoded, nunca usado
└── utils/helpers.py  # validadores nunca chamados
```

</td><td valign="top">

```
task-manager-api/
├── app.py                 # composition root (create_app)
├── seed.py
├── .env.example
├── requirements.txt       # sem marshmallow/requests
├── config/settings.py     # tudo via variável de ambiente
├── models/
│   ├── database.py        # db + CRUDMixin (find/save/delete)
│   ├── errors.py          # exceções de domínio (sem HTTP)
│   ├── task.py            # is_overdue(), validação, consultas
│   ├── user.py            # scrypt + migração do MD5
│   └── category.py
├── controllers/           # task, user, category, report
├── services/
│   ├── report_service.py  # summary / user report / stats
│   ├── auth_service.py    # token assinado (itsdangerous)
│   └── notification_service.py  # SMTP via config
├── routes/                # task, user, report, category (novo)
├── middlewares/
│   ├── error_handler.py   # handler de erro centralizado
│   └── auth.py            # require_auth / require_admin
└── utils/dates.py         # utc_now()
```

</td></tr>
</table>

Principais transformações aplicadas (com o número do padrão no playbook). Como o projeto já tinha `models/`, `routes/` e `services/`, a skill não recriou a árvore: aproveitou as pastas existentes e **adicionou** o que faltava (`controllers/`, `config/`, `middlewares/`).
- **#1:** `SECRET_KEY`, URI do banco, `DEBUG`/`HOST`/`PORT` e credenciais SMTP extraídos para `config/settings.py` e `.env.example`.
- **#3/#4:** rotas viraram one-liners que chamam Controllers; os Controllers validam a entrada e delegam ao Model/Service. O CRUD de `/categories` ganhou `routes/category_routes.py` próprio.
- **#5/#6:** consultas encapsuladas nos Models (`Task.search`, `Task.by_user`, `*.all_with_task_count`) e nenhum `db.session` fora de `models/`; serialização centralizada em `to_dict()` / `to_detail_dict()` / `to_summary_dict()`.
- **#7:** `GET /tasks` passou de 17 para 1 query (`joinedload`), `GET /users` de 4 para 1, `GET /categories` de 5 para 1 (`LEFT JOIN ... GROUP BY`) e `/reports/summary` de 19 para 4.
- **#8:** `Task.is_overdue()` virou a única implementação da regra de atraso, usada pelos 6 pontos que antes a reimplementavam.
- **#9:** o token falso foi trocado por um token assinado com `SECRET_KEY`, e os decorators `require_auth`/`require_admin` foram criados e testados. Eles **ainda não estão aplicados a nenhuma rota**, porque exigir token mudaria o contrato público; essa decisão ficou registrada como pendente para o humano.
- **#10:** MD5 trocado por `werkzeug.security` (scrypt), com migração automática dos hashes MD5 antigos no próximo login; `datetime.utcnow()` trocado por `utc_now()` (`datetime.now(timezone.utc)`); `Query.get()` trocado por `db.session.get()`; `debug` desligado por padrão.
- **Erros:** os `except:` genéricos deram lugar a exceções de domínio (`ValidationError`, `NotFoundError`, ...) traduzidas em HTTP num handler central, que loga a causa e faz rollback.

Os arquivos antigos (`database.py`, `utils/helpers.py`) foram removidos.

### Checklist de validação

#### code-smells-project

##### Fase 1 — Análise
- [x] Linguagem detectada corretamente (Python)
- [x] Framework detectado corretamente (Flask 3.1.1 + flask-cors 5.0.1)
- [x] Domínio da aplicação descrito corretamente (E-commerce: produtos, usuários, pedidos, relatório de vendas)
- [x] Número de arquivos analisados condiz com a realidade (4 arquivos, 780 linhas)

##### Fase 2 — Auditoria
- [x] Relatório segue o template definido nos arquivos de referência
- [x] Cada finding tem arquivo e linhas exatos
- [x] Findings ordenados por severidade (CRITICAL → LOW)
- [x] Mínimo de 5 findings identificados (18 findings: 4 CRITICAL, 5 HIGH)
- [x] Detecção de APIs deprecated incluída (2 encontradas)
- [x] Skill pausa e pede confirmação antes da Fase 3

##### Fase 3 — Refatoração
- [x] Estrutura de diretórios segue padrão MVC (`models/`, `controllers/`, `routes/`, `middlewares/`, `config/`, `services/`)
- [x] Configuração extraída para módulo de config (sem hardcoded): `config/settings.py` + `.env.example`
- [x] Models criados para abstrair dados (único lugar do projeto com SQL)
- [x] Views/Routes separadas para roteamento (blueprints em `routes/`)
- [x] Controllers concentram o fluxo da aplicação
- [x] Error handling centralizado (`middlewares/error_handler.py`)
- [x] Entry point claro (`app.py` → `create_app()`)
- [x] Aplicação inicia sem erros
- [x] Endpoints originais respondem corretamente

#### ecommerce-api-legacy

##### Fase 1 — Análise
- [x] Linguagem detectada corretamente (JavaScript / Node.js)
- [x] Framework detectado corretamente (Express 4.18.2 + sqlite3 5.1.6)
- [x] Domínio da aplicação descrito corretamente (LMS com fluxo de checkout: cursos, matrículas, pagamentos, usuários, log de auditoria)
- [x] Número de arquivos analisados condiz com a realidade (3 arquivos, 180 linhas)

##### Fase 2 — Auditoria
- [x] Relatório segue o template definido nos arquivos de referência
- [x] Cada finding tem arquivo e linhas exatos
- [x] Findings ordenados por severidade (CRITICAL → LOW)
- [x] Mínimo de 5 findings identificados (14 findings: 4 CRITICAL, 3 HIGH)
- [x] Detecção de APIs deprecated incluída (2 encontradas)
- [x] Skill pausa e pede confirmação antes da Fase 3

##### Fase 3 — Refatoração
- [x] Estrutura de diretórios segue padrão MVC (`src/models/`, `src/controllers/`, `src/routes/`, `src/middlewares/`, `src/config/`, `src/services/`)
- [x] Configuração extraída para módulo de config (sem hardcoded): `src/config/index.js` + `.env.example`
- [x] Models criados para abstrair dados (único lugar do projeto com SQL)
- [x] Views/Routes separadas para roteamento (`src/routes/index.js`)
- [x] Controllers concentram o fluxo da aplicação
- [x] Error handling centralizado (`src/middlewares/errorHandler.js`)
- [x] Entry point claro (`src/app.js`)
- [x] Aplicação inicia sem erros
- [x] Endpoints originais respondem corretamente

#### task-manager-api

##### Fase 1 — Análise
- [x] Linguagem detectada corretamente (Python)
- [x] Framework detectado corretamente (Flask 3.0.0 + Flask-SQLAlchemy 3.1.1 + Flask-CORS 4.0.0)
- [x] Domínio da aplicação descrito corretamente (Task Manager: tarefas, categorias, usuários, relatórios de produtividade)
- [x] Número de arquivos analisados condiz com a realidade (15 arquivos, 1158 linhas)

##### Fase 2 — Auditoria
- [x] Relatório segue o template definido nos arquivos de referência
- [x] Cada finding tem arquivo e linhas exatos
- [x] Findings ordenados por severidade (CRITICAL → LOW)
- [x] Mínimo de 5 findings identificados (15 findings: 2 CRITICAL, 4 HIGH)
- [x] Detecção de APIs deprecated incluída (4 encontradas)
- [x] Skill pausa e pede confirmação antes da Fase 3

##### Fase 3 — Refatoração
- [x] Estrutura de diretórios segue padrão MVC (`models/`, `controllers/`, `routes/`, `middlewares/`, `config/`, `services/`), aproveitando as pastas que já existiam
- [x] Configuração extraída para módulo de config (sem hardcoded): `config/settings.py` + `.env.example`
- [x] Models criados para abstrair dados (nenhum acesso a `db.session` fora de `models/`)
- [x] Views/Routes separadas para roteamento (blueprints em `routes/`, um por recurso)
- [x] Controllers concentram o fluxo da aplicação
- [x] Error handling centralizado (`middlewares/error_handler.py`)
- [x] Entry point claro (`app.py` → `create_app()`)
- [x] Aplicação inicia sem erros (inclusive com `-W error::DeprecationWarning`)
- [x] Endpoints originais respondem corretamente (41/41 requisições com o mesmo status code)

### Logs da aplicação rodando após a refatoração

**Boot do `code-smells-project` refatorado:**

```
$ ADMIN_TOKEN=... SECRET_KEY=... python app.py
2026-09-22 20:46:12,337 INFO models.database: Banco populado com dados de exemplo
2026-09-22 20:46:12,343 INFO __main__: Servidor iniciado em http://0.0.0.0:5000
 * Serving Flask app 'app'
 * Debug mode: off
 * Running on http://127.0.0.1:5000
2026-09-22 20:46:12,389 INFO werkzeug: 127.0.0.1 - - [22/Sep/2026 20:46:12] "GET / HTTP/1.1" 200 -
```

**Validação dos endpoints:** a app original e a refatorada receberam o mesmo roteiro de 38 requisições `curl`, cobrindo todos os endpoints, casos de sucesso e de erro. As respostas foram comparadas ignorando `criado_em`. Todas as diferenças são correções de segurança intencionais; todo o resto manteve rota, método, status e payload idênticos:

| Requisição | Antes | Depois |
|---|---|---|
| `GET /health` | 200, com `secret_key`, `debug`, `db_path` | 200, só `status`, `database`, `counts`, `versao` |
| `GET /usuarios` | 200, com o campo `senha` em texto plano | 200, sem `senha` |
| `POST /login` com `' OR '1'='1' --` | **200, logado como Admin** | 401 `Email ou senha inválidos` |
| `POST /pedidos` com `quantidade: -5` | **201, estoque aumentado** | 400 |
| `PUT /pedidos/999/status` | 200 (pedido inexistente) | 404 `Pedido não encontrado` |
| `POST /admin/query` | 200, executa SQL arbitrário | 404 (endpoint removido) |
| `POST /admin/reset-db` sem token | 200, banco apagado | 401 (403 se `ADMIN_TOKEN` não estiver configurado) |

Trecho das chamadas de verificação extra feitas contra a versão refatorada:

```
reset sem token                      401 {"erro":"Não autorizado"}
login admin (seed via env)           200 {"dados":{"email":"admin@loja.com","id":1,"nome":"Admin","tipo":"admin"},"mensagem":"Login OK","sucesso":true}
criar produto JSON malformado        400 {"erro":"Dados inválidos"}
busca SQLi (q=' OR 1=1 --)           200 {"dados":[],"sucesso":true,"total":0}
pedido itens duplicados > estoque    400 {"erro":"Estoque insuficiente para Cadeira Gamer","sucesso":false}
pedido ok                            201 {"dados":{"pedido_id":1,"total":3899.70...},"mensagem":"Pedido criado com sucesso","sucesso":true}
delete produto 6 (soft)              200 {"mensagem":"Produto deletado","sucesso":true}
get produto 6 pós delete             404 {"erro":"Produto não encontrado","sucesso":false}
pedido mantém nome do produto        200 {..."produto_nome":"Cadeira Gamer"...}
login usuário legado (senha migrada) 200 {"dados":{"email":"old@x.com",...},"mensagem":"Login OK","sucesso":true}
```

**Boot do `ecommerce-api-legacy` refatorado:**

```
$ ADMIN_TOKEN=... PAYMENT_GATEWAY_KEY=... npm start

> desafio-arquitetura-ia-boilerplate@1.0.0 start
> node --env-file-if-exists=.env src/app.js

.env not found. Continuing without it.
{"time":"2026-09-23T00:08:25.351Z","level":"info","message":"server started","port":3000}
{"time":"2026-09-23T00:08:25.471Z","level":"info","message":"checkout completed","userId":2,"courseId":2,"enrollmentId":2,"card":"****4444"}
```

Sem `ADMIN_TOKEN`, o boot avisa e as rotas administrativas ficam fechadas:

```
{"time":"2026-09-23T00:08:35.027Z","level":"warn","message":"ADMIN_TOKEN not set: admin routes will reject every request"}
{"time":"2026-09-23T00:08:35.029Z","level":"info","message":"server started","port":3000}
```

**Validação dos endpoints:** antes da refatoração, a app original recebeu um roteiro de 7 requisições `curl` (os exemplos do `api.http` mais os casos de erro), e a saída foi gravada como baseline. O mesmo roteiro rodou contra a versão refatorada e as saídas foram comparadas com `diff`. Checkout (sucesso, pagamento recusado, curso inexistente, payload incompleto) e relatório financeiro ficaram **idênticos**. As únicas diferenças são correções intencionais:

| Requisição | Antes | Depois |
|---|---|---|
| `DELETE /api/users/1` | 200 `Usuário deletado, mas as matrículas e pagamentos ficaram sujos no banco.` | 200 `Usuário deletado.` (matrículas e pagamentos removidos junto) |
| `GET /api/admin/financial-report` após o delete | aluno `"Unknown"` com `paid: 997` | curso sem alunos órfãos |
| `GET /api/admin/financial-report` / `DELETE /api/users/:id` sem token | 200 | 401 `Unauthorized` |
| `POST /api/checkout` sem `pwd` | 200, usuário criado com senha `"123456"` | 400 `Bad Request` |
| `POST /api/checkout` com JSON malformado | 400 com página de erro HTML do Express | 400 `Bad Request` |
| Log do checkout | `Processando cartão 4111222233334444 na chave pk_live_...` | `"card":"****4444"`, sem a chave |

Trecho das chamadas de verificação extra feitas contra a versão refatorada:

```
report sem token                 Unauthorized [401]
report com token errado          Unauthorized [401]
delete sem token                 Unauthorized [401]
checkout sem pwd                 Bad Request [400]
checkout JSON malformado         Bad Request [400]
checkout com eml "a' OR 1=1--"   {"msg":"Sucesso","enrollment_id":3} [200]   (gravado como texto literal)
10 checkouts concorrentes        200 200 200 200 200 200 200 200 200 200
receita do curso 1 depois        10967 (= 11 × 997, sem perder nenhuma escrita)
```

**Boot do `task-manager-api` refatorado:**

```
$ SECRET_KEY=... python app.py
 * Serving Flask app 'app'
 * Debug mode: off
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:5000
2026-09-22 21:25:59,735 INFO werkzeug: 127.0.0.1 - - [22/Sep/2026 21:25:59] "GET /health HTTP/1.1" 200 -
2026-09-22 21:25:59,875 INFO controllers.task_controller: Task criada: 11 - Nova task
2026-09-22 21:25:59,953 INFO controllers.task_controller: Task atualizada: 11
2026-09-22 21:25:59,987 INFO controllers.task_controller: Task deletada: 11
2026-09-22 21:26:00,156 INFO controllers.user_controller: Usuário criado: 4 - Ana
2026-09-22 21:26:00,585 INFO controllers.user_controller: Usuário deletado: 4
```

**Validação dos endpoints:** antes de mudar o código, a skill populou um banco com o `seed.py` original e subiu a app original contra uma cópia dele. Nessa app rodou um roteiro de 41 requisições `curl`, cobrindo os 21 endpoints e os casos de erro (título curto, status/prioridade inválidos, usuário inexistente, data malformada, e-mail duplicado, login errado, 404s). As respostas foram gravadas como baseline. A versão refatorada rodou o mesmo roteiro contra outra cópia do **mesmo** banco. Resultado: **41/41 status codes iguais** e corpos idênticos depois de normalizar os timestamps. A única diferença é intencional:

| Requisição | Antes | Depois |
|---|---|---|
| `GET /users/1`, `POST /users`, `PUT /users/<id>`, `POST /login` | 200/201, com o campo `password` (hash MD5) | 200/201, sem `password` |
| `POST /login` | `"token": "fake-jwt-token-1"` | token assinado com `SECRET_KEY` (`eyJ1c2VyX2lkIjoxLC...`) |
| `POST /tasks` com `"priority": "2"` | 500 (`TypeError`) | 400 `Prioridade deve ser entre 1 e 5` |
| `GET /tasks/search?priority=abc` | 500 (`ValueError`) | 400 `Prioridade inválida` |
| `PUT /categories/1` sem corpo | 500 (`TypeError`) | 400 `Dados inválidos` |
| `POST /tasks` com JSON malformado | 400 com página HTML | 400 `{"error": "Dados inválidos"}` |

Trecho das chamadas de verificação extra feitas contra a versão refatorada:

```
login joao (hash MD5 legado)         200   → hash regravado como scrypt:32768:8:...
login joao de novo                   200
rota com @require_admin sem token    401 {"error": "Token ausente"}
... com "fake-jwt-token-1"           401 {"error": "Token inválido"}
... com token de usuário comum       403
... com token do admin               200
queries  GET /tasks                  17 → 1
queries  GET /users                   4 → 1
queries  GET /categories              5 → 1
queries  GET /reports/summary        19 → 4
```

### Observações sobre stacks diferentes

- **Python/Flask, monolito (`code-smells-project`):** a skill detectou a stack a partir do `requirements.txt` e adaptou a estrutura à convenção do Flask: blueprints em `routes/` e conexão por requisição via `flask.g`. Criou uma camada de `services/` só para o fluxo de pedido, que mexe em várias tabelas; o CRUD simples ficou apenas no Model, seguindo a regra de evitar abstração especulativa. Também preservou o contrato da API e verificou isso comparando respostas antes e depois, não só olhando o status HTTP.
- **Node.js/Express, God Class (`ecommerce-api-legacy`):** a skill não assumiu Python. Detectou a stack pelo `package.json`, usou a convenção do Express (`src/`, `Router`, middlewares encadeados, `app.locals` para injetar o banco) e resolveu com o que o Node já oferece: `crypto.scrypt` no lugar de bcrypt e `--env-file` no lugar de `dotenv`, sem nenhuma dependência nova. Tratou problemas próprios do Node, que não aparecem no projeto Flask: callback hell do `sqlite3` (virou `async/await`), erros de handlers `async` que o Express 4 não captura sozinho (virou `asyncHandler`) e transações numa conexão compartilhada por requisições concorrentes (viraram uma fila serializada, testada com 10 checkouts simultâneos). Aqui também só o fluxo de checkout, que mexe em várias tabelas, ganhou um Service. Antes de refatorar, a skill gravou as respostas da app original como baseline, para comparar depois com `diff`.
- **Python/Flask parcialmente organizado (`task-manager-api`):** foi o teste do princípio "Adapte-se ao ponto de partida". A skill classificou o projeto como *parcialmente organizado* e não o tratou como monolito: manteve `models/`, `routes/`, `services/` e `utils/`, e só **adicionou** as camadas que faltavam (`controllers/`, `config/`, `middlewares/`). Como o projeto já usava ORM, a skill não criou Repository à parte e colocou as consultas nos próprios Models do SQLAlchemy, via `CRUDMixin` e classmethods. Adaptou também as recomendações do catálogo à stack: `joinedload` e `GROUP BY` do SQLAlchemy contra o N+1, `itsdangerous` (que já vem com o Flask) para o token, sem dependência nova, e `Query.get()` identificado como API legada do SQLAlchemy 2.x, algo que não estava no catálogo. Também tratou o banco já existente, que tinha hashes MD5 gravados: em vez de invalidar as senhas, elas são migradas no próximo login. Onde a correção mudaria o contrato público (exigir token nas rotas de usuário), a skill deixou a decisão para o humano em vez de decidir sozinha. Por fim, validou o próprio relatório contra a app original e removeu um falso positivo.

**D) Seção "Como Executar":**

### Pré-requisitos

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) instalado e autenticado.
- Python 3.10+ e `pip` (validado com Python 3.12), para os projetos Flask.
- Node.js 22.9+ e `npm` (validado com Node 24.14), para o `ecommerce-api-legacy`: o script `npm start` usa `--env-file-if-exists`.
- `curl`, para validar os endpoints.

### Executar a skill

A skill (`.claude/skills/refactor-arch/`) fica dentro de cada projeto. Em cada um:

```bash
# Projeto 1 — Python/Flask (monolito)
cd code-smells-project
claude "/refactor-arch"

# Projeto 2 — Node.js/Express
cd ../ecommerce-api-legacy
claude "/refactor-arch"

# Projeto 3 — Python/Flask (parcialmente organizado)
cd ../task-manager-api
claude "/refactor-arch"
```

A skill roda a Fase 1 (análise) e a Fase 2 (auditoria), salva o relatório em `reports/audit-project-N.md` e para com:

```
Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
```

Responda `y` para a skill reestruturar o projeto em MVC e validar o resultado (Fase 3), ou `n` para encerrar sem alterar nenhum arquivo além do relatório.

### Rodar o code-smells-project refatorado

```bash
cd code-smells-project
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # preencha SECRET_KEY, ADMIN_TOKEN, SEED_ADMIN_PASSWORD, SEED_CLIENTE_PASSWORD
python app.py             # sobe em http://localhost:5000
```

Variáveis de ambiente (ver `.env.example`):

| Variável | Uso | Se ausente |
|---|---|---|
| `SECRET_KEY` | chave de assinatura do Flask | chave aleatória a cada boot (com aviso no log) |
| `DEBUG` | modo debug | `false` |
| `HOST` / `PORT` | endereço do servidor | `0.0.0.0` / `5000` |
| `DATABASE_PATH` | arquivo SQLite | `loja.db` |
| `ADMIN_TOKEN` | exigido no header `X-Admin-Token` de `POST /admin/reset-db` | endpoint desabilitado (403) |
| `SEED_ADMIN_PASSWORD` / `SEED_CLIENTE_PASSWORD` | senhas dos usuários de exemplo | senha aleatória (não é possível logar com eles) |

Em produção, use um servidor WSGI (`gunicorn "app:app"`) com `DEBUG=false`.

### Rodar o ecommerce-api-legacy refatorado

```bash
cd ecommerce-api-legacy
npm install
cp .env.example .env      # preencha ADMIN_TOKEN (e PAYMENT_GATEWAY_KEY)
npm start                 # sobe em http://localhost:3000
```

Variáveis de ambiente (ver `.env.example`):

| Variável | Uso | Se ausente |
|---|---|---|
| `PORT` | porta do servidor | `3000` |
| `DB_PATH` | arquivo SQLite | `:memory:` (comportamento original, com seed a cada boot) |
| `PAYMENT_GATEWAY_KEY` | chave do gateway de pagamento | não usada pelo gateway simulado |
| `ADMIN_TOKEN` | exigido no header `X-Admin-Token` de `GET /api/admin/financial-report` e `DELETE /api/users/:id` | rotas administrativas respondem 401 (com aviso no boot) |
| `LOG_LEVEL` | `debug` / `info` / `warn` / `error` | `info` |

### Rodar o task-manager-api refatorado

```bash
cd task-manager-api
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # preencha SECRET_KEY (e SMTP_* se for enviar e-mails)
python seed.py            # popula instance/tasks.db com usuários, categorias e tasks
python app.py             # sobe em http://localhost:5000
```

Usuários do seed: `joao@email.com` / `1234` (admin), `maria@email.com` / `abcd` (user), `pedro@email.com` / `pass` (manager).

Variáveis de ambiente (ver `.env.example`):

| Variável | Uso | Se ausente |
|---|---|---|
| `SECRET_KEY` | chave de assinatura do Flask e dos tokens de login | chave aleatória a cada boot (com aviso no log; tokens não sobrevivem a restart) |
| `DEBUG` | modo debug | `false` |
| `HOST` / `PORT` | endereço do servidor | `0.0.0.0` / `5000` |
| `LOG_LEVEL` | nível do `logging` | `INFO` |
| `DATABASE_URL` | URI do SQLAlchemy | `sqlite:///tasks.db` (em `instance/`, mesmo local do original) |
| `AUTH_TOKEN_MAX_AGE` | validade do token de `POST /login`, em segundos | `86400` |
| `SMTP_HOST` / `SMTP_PORT` / `SMTP_USER` / `SMTP_PASSWORD` | credenciais do `NotificationService` | `smtp.gmail.com` / `587` / vazio |

Em produção, use um servidor WSGI (`gunicorn "app:app"`) com `DEBUG=false`.

### Como validar que a refatoração funcionou

1. **Boot:** o log de inicialização não pode ter `Traceback`/`ERROR`, e deve mostrar `Debug mode: off` e `Servidor iniciado em ...`.
2. **Endpoints originais:** chamar cada rota e conferir que status e formato de payload continuam os mesmos:

   ```bash
   B=http://localhost:5000; J='Content-Type: application/json'
   curl -s $B/                                  # 200, lista de endpoints
   curl -s $B/health                            # 200, sem secret_key/debug/db_path
   curl -s $B/produtos                          # 200 {"dados":[...],"sucesso":true}
   curl -s "$B/produtos/busca?q=Mouse"          # 200 {"dados":[...],"total":1,...}
   curl -s -X POST -H "$J" $B/usuarios -d '{"nome":"Teste","email":"t@x.com","senha":"s3nh@"}'   # 201
   curl -s -X POST -H "$J" $B/login    -d '{"email":"t@x.com","senha":"s3nh@"}'                  # 200 Login OK
   curl -s -X POST -H "$J" $B/pedidos  -d '{"usuario_id":2,"itens":[{"produto_id":1,"quantidade":1}]}'  # 201
   curl -s $B/pedidos                           # 200, pedidos com itens e produto_nome
   curl -s -X PUT -H "$J" $B/pedidos/1/status -d '{"status":"aprovado"}'                        # 200
   curl -s $B/relatorios/vendas                 # 200, faturamento/desconto/ticket médio
   ```
3. **Correções de segurança:** conferir que o bypass de login (`{"email":"' OR '1'='1' --","senha":"x"}`) retorna 401, que `GET /usuarios` não traz `senha` e que `POST /admin/reset-db` sem `X-Admin-Token` retorna 401/403.
4. **Estrutura:** conferir que a árvore de diretórios segue `04-architecture-guidelines.md` e que não sobrou SQL fora de `models/` (`grep -rl execute --include=*.py .` deve listar só arquivos de `models/`).
5. **Relatório × código:** cada finding CRITICAL/HIGH de `reports/audit-project-N.md` deve estar corrigido no código refatorado.

**Validação do ecommerce-api-legacy** (os mesmos exemplos estão em `api.http`):

1. **Boot:** o log deve mostrar `"message":"server started"`, sem `"level":"error"`.
2. **Endpoints originais:**

   ```bash
   B=http://localhost:3000; J='Content-Type: application/json'; A="X-Admin-Token: $ADMIN_TOKEN"
   curl -s -X POST -H "$J" $B/api/checkout -d '{"usr":"Guilherme","eml":"gui@fullcycle.com.br","pwd":"senhaforte","c_id":2,"card":"4111222233334444"}'  # 200 {"msg":"Sucesso","enrollment_id":2}
   curl -s -X POST -H "$J" $B/api/checkout -d '{"usr":"João","eml":"joao@teste.com","pwd":"123","c_id":1,"card":"5111222233334444"}'  # 400 Pagamento recusado
   curl -s -X POST -H "$J" $B/api/checkout -d '{"usr":"X","eml":"x@x.com","pwd":"1","c_id":99,"card":"4111222233334444"}'  # 404 Curso não encontrado
   curl -s -H "$A" $B/api/admin/financial-report   # 200 [{"course":...,"revenue":...,"students":[...]}]
   curl -s -H "$A" -X DELETE $B/api/users/1        # 200 Usuário deletado.
   ```
3. **Correções de segurança:** conferir que as rotas administrativas sem `X-Admin-Token` retornam 401, que o checkout sem `pwd` retorna 400 e que o log do checkout mostra só `****4444`, sem o número do cartão nem a chave do gateway.
4. **Estrutura:** conferir que não sobrou SQL fora de `src/models/` e `src/config/database.js` (`grep -rlE "SELECT|INSERT|DELETE FROM" src` deve listar só esses arquivos) e que não há segredo nem `console.log` no código (`grep -rnE "console\.log|pk_live" src` não deve retornar nada).

**Validação do task-manager-api** (rode `python seed.py` antes):

1. **Boot:** o log deve mostrar `Debug mode: off`, sem `Traceback`/`ERROR`. Rodar com `python -W error::DeprecationWarning app.py` não pode falhar (confirma que `utcnow()` e `Query.get()` saíram).
2. **Endpoints originais:**

   ```bash
   B=http://localhost:5000; J='Content-Type: application/json'
   curl -s $B/tasks                              # 200, tasks com overdue, user_name, category_name
   curl -s $B/tasks/1                            # 200, task + overdue
   curl -s "$B/tasks/search?q=API"               # 200 [...]
   curl -s $B/tasks/stats                        # 200 {"total":10,"overdue":2,...}
   curl -s -X POST -H "$J" $B/tasks -d '{"title":"Nova task","priority":2,"user_id":1,"due_date":"2020-01-01","tags":["a","b"]}'  # 201
   curl -s -X PUT  -H "$J" $B/tasks/11 -d '{"status":"done"}'   # 200
   curl -s -X DELETE $B/tasks/11                 # 200 Task deletada com sucesso
   curl -s $B/users                              # 200, com task_count e sem password
   curl -s $B/users/1/tasks                      # 200, com overdue
   curl -s -X POST -H "$J" $B/login -d '{"email":"joao@email.com","password":"1234"}'  # 200, token assinado
   curl -s $B/reports/summary                    # 200, overview/tasks_by_status/overdue/user_productivity
   curl -s $B/reports/user/1                     # 200 {"user":...,"statistics":...}
   curl -s $B/categories                         # 200, com task_count
   ```
3. **Correções de segurança:** conferir que nenhuma resposta de usuário traz `password`, que o token do `/login` não é mais `fake-jwt-token-<id>` e que `POST /tasks` com `"priority": "2"` retorna 400 (e não 500 com o debugger exposto).
4. **Estrutura:** conferir que não sobrou acesso ao banco fora de `models/` (`grep -rn "db.session\|\.query" controllers routes services` não deve retornar nada) nem APIs deprecated/segredos (`grep -rnE "utcnow|query\.get\(|super-secret|senha123|debug=True" --include=*.py .` não deve retornar nada).
