================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      JavaScript (Node.js)
Framework:     Express ^4.18.2
Dependencies:  express ^4.18.2, sqlite3 ^5.1.6 (driver cru em callback-style, sem ORM, sem lib de auth/cripto)
Domain:        LMS com fluxo de checkout (cursos, matrículas, pagamentos, usuários, log de auditoria)
Architecture:  Monolito de poucos arquivos — a classe AppManager cria schema, faz seed, define todas as rotas e executa SQL + regra de negócio inline; utils.js mistura config, cache e "cripto"
Source files:  3 files analyzed (src/app.js, src/AppManager.js, src/utils.js)
DB tables:     users, courses, enrollments, payments, audit_logs (SQLite in-memory)
================================

================================
ARCHITECTURE AUDIT REPORT
================================
Project: ecommerce-api-legacy
Stack:   JavaScript (Node.js) + Express 4.18.2
Files:   3 analyzed | ~180 lines of code

## Summary
CRITICAL: 4 | HIGH: 3 | MEDIUM: 3 | LOW: 4

## Findings

### [CRITICAL] Hardcoded Credentials / Secrets
File: src/utils.js:1-7
Description: O objeto `config` contém literais de produção direto no código: `dbPass: "senha_super_secreta_prod_123"` (linha 3), `paymentGatewayKey: "pk_live_1234567890abcdef"` (linha 4), além de `dbUser`, `smtpUser` e `port` fixos. Nada é lido de `process.env`.
Impact: Qualquer pessoa com acesso ao repositório obtém a senha do banco e a chave live do gateway de pagamento; rotacionar segredos exige deploy de código.
Recommendation: Extrair Configuração (playbook #1) — criar `src/config/index.js` lendo `process.env`, documentar as variáveis em `.env.example` e manter `.env` no `.gitignore`.

### [CRITICAL] God Class (AppManager)
File: src/AppManager.js:4-139
Description: A classe `AppManager` abre a conexão (linha 7), cria as 5 tabelas e faz seed (linhas 10-23), registra as 3 rotas HTTP (linhas 28, 80, 131) e, dentro de cada handler, executa SQL cru e regra de negócio. Não há Model, Controller, Repository nem Route separados.
Impact: Nenhuma parte é testável isoladamente; qualquer alteração em uma rota arrisca quebrar schema, seed ou outra rota; SQL fica acoplado ao protocolo HTTP.
Recommendation: Separar God File em Model/Controller/Routes (playbook #3) + Introduzir Camada de Persistência (playbook #5): `config/database.js` (conexão + schema + seed), `models/*Model.js` (SQL), `services/checkoutService.js`, `controllers/*Controller.js`, `routes/index.js`.

### [CRITICAL] Exposição de dados sensíveis em log (número do cartão + chave do gateway)
File: src/AppManager.js:45
Description: `console.log(\`Processando cartão ${cc} na chave ${config.paymentGatewayKey}\`)` grava o número completo do cartão (PAN) e a chave live do gateway em stdout a cada checkout.
Impact: Qualquer um com acesso aos logs (agregador, CI, suporte) obtém dados de cartão e a chave de pagamento — violação direta de PCI-DSS e vazamento de segredo.
Recommendation: Remover o log; se necessário registrar o evento, logar apenas os 4 últimos dígitos mascarados e nunca a chave (playbook #1 para a chave).

### [CRITICAL] Hash de senha caseiro (API/técnica deprecated)
File: src/utils.js:17-23
Description: `badCrypto` repete `Buffer.from(pwd).toString('base64').substring(0, 2)` 10.000 vezes e corta em 10 chars — o resultado depende só do primeiro caractere (e meio) da senha: `badCrypto("senhaforte") === badCrypto("senha123") === "c2c2c2c2c2"`. Usado em src/AppManager.js:68; o seed (src/AppManager.js:18) ainda grava a senha `'123'` em texto plano.
Impact: O hash não protege nada — é reversível para ~1 caractere e colide em massa; um vazamento do banco equivale a vazar as senhas.
Recommendation: Substituir APIs Deprecated (playbook #10) — usar `crypto.scrypt` com salt aleatório (nativo do Node, sem nova dependência) ou `bcrypt`/`argon2`; aplicar também ao usuário do seed.

### [HIGH] Endpoints administrativos/destrutivos sem autenticação
File: src/AppManager.js:80, src/AppManager.js:131
Description: `GET /api/admin/financial-report` expõe receita e nome de todos os alunos, e `DELETE /api/users/:id` apaga usuários — ambos sem nenhuma checagem de identidade ou permissão.
Impact: Qualquer pessoa que conheça a URL lê dados financeiros/pessoais ou apaga contas.
Recommendation: Proteger Endpoints Perigosos (playbook #9) — middleware `requireAdmin` validando um token de admin vindo de variável de ambiente, aplicado só a essas rotas.

### [HIGH] Fat Controller — regra de negócio de checkout inline na rota
File: src/AppManager.js:28-78
Description: O handler de `POST /api/checkout` busca curso, busca/cria usuário, decide aprovação do pagamento (`cc.startsWith("4")`, linha 46), cria matrícula, pagamento e audit log e escreve no cache — 50 linhas em 4 níveis de callback. As 3-4 escritas (linhas 50, 54, 57, 69) não estão numa transação: se o INSERT de pagamento falhar, a matrícula fica gravada sem pagamento.
Impact: Regra de negócio impossível de reusar/testar sem subir HTTP; risco real de dados inconsistentes (matrícula sem pagamento).
Recommendation: Extrair Controller de dentro da Rota (playbook #4) — `checkoutController` só traduz HTTP; `checkoutService` orquestra os Models dentro de uma transação (`BEGIN`/`COMMIT`/`ROLLBACK`).

### [HIGH] Estado Global Mutável / Ausência de Injeção de Dependência
File: src/utils.js:9-15, src/AppManager.js:7
Description: `globalCache = {}` (linha 9) é um objeto de módulo compartilhado por todas as requisições que cresce sem limite em `logAndCache` (linha 14), e nunca é lido; `totalRevenue` (linha 10) é exportado como primitivo e nunca usado. A conexão com o banco é criada dentro do construtor (`new sqlite3.Database(':memory:')`) em vez de injetada.
Impact: Vazamento de memória proporcional ao nº de checkouts; estado compartilhado entre requisições; impossível testar com um banco isolado.
Recommendation: Remover o cache e o contador mortos; criar a conexão em `config/database.js` e injetá-la nos Models (Separar God File, playbook #3).

### [MEDIUM] Queries N+1 no relatório financeiro
File: src/AppManager.js:83-125
Description: Para cada curso (linha 83) dispara-se uma query de matrículas (linha 92) e, para cada matrícula, uma query de usuário (linha 104) e outra de pagamento (linha 106) — 1 + C + 2·E round-trips, coordenados por contadores manuais (`coursesPending`, `enrPending`).
Impact: Performance degrada linearmente com o volume; a lógica de contagem é frágil (se `err` ocorrer na linha 92, `enrollments.length` lança TypeError e derruba o processo).
Recommendation: Eliminar N+1 (playbook #7) — uma única query com `LEFT JOIN` de courses/enrollments/users/payments, agrupada em memória por curso.

### [MEDIUM] Erros silenciosos / sem tratamento centralizado
File: src/AppManager.js:57, src/AppManager.js:92-93, src/AppManager.js:104-106, src/AppManager.js:133
Description: O `err` é recebido e ignorado no INSERT de audit_logs (linha 57), nas queries do relatório (linhas 92, 104, 106) e no DELETE (linha 133 — responde sucesso mesmo com erro). Cada handler inventa seu próprio formato de erro (`res.status(500).send("Erro DB")`, `"Erro Matrícula"`…).
Impact: Falhas de banco passam despercebidas ou viram respostas de sucesso falsas; sem ponto único de log/observabilidade.
Recommendation: Middleware de erro centralizado (`middlewares/errorHandler.js`), handlers `async` que propagam exceções via `next(err)`.

### [MEDIUM] Validação de entrada ausente/insuficiente
File: src/AppManager.js:35, src/AppManager.js:68
Description: A rota só checa presença de `usr`, `eml`, `c_id`, `card` (linha 35); `pwd` não é exigido e, se ausente, o usuário é criado com a senha padrão `"123456"` (linha 68). Não há checagem de tipo/formato de e-mail, id ou cartão.
Impact: Contas criadas com senha conhecida por qualquer um; payloads malformados chegam ao banco.
Recommendation: Validar o payload no Controller antes de chamar o Service (playbook #4); sem senha padrão implícita.

### [LOW] Dados órfãos ao deletar usuário
File: src/AppManager.js:131-137
Description: `DELETE FROM users WHERE id = ?` remove só o usuário; matrículas e pagamentos continuam apontando para um `user_id` inexistente — a própria resposta admite: "as matrículas e pagamentos ficaram sujos no banco".
Impact: Integridade referencial corrompida; o relatório financeiro passa a exibir alunos "Unknown".
Recommendation: Remover dependentes (payments → enrollments → user) na mesma transação dentro do Model.

### [LOW] Logging via console.log
File: src/app.js:13, src/utils.js:13
Description: Toda a observabilidade depende de `console.log` sem nível nem formato estruturado.
Impact: Não dá para filtrar por severidade nem desligar em produção.
Recommendation: Centralizar num logger mínimo (`config/logger.js`) com níveis, usado pelo boot e pelo error handler.

### [LOW] Nomenclatura críptica
File: src/AppManager.js:26, src/AppManager.js:29-33
Description: Variáveis `u`, `e`, `p`, `cid`, `cc` e o alias `const self = this` (usado para contornar o `this` de `function(err)` do sqlite3).
Impact: Dificulta a leitura e favorece bugs de escopo.
Recommendation: Nomes descritivos internamente (`name`, `email`, `password`, `courseId`, `cardNumber`), mantendo os campos públicos do payload (`usr`, `eml`, `pwd`, `c_id`, `card`) por compatibilidade.

### [LOW] API legada: driver sqlite3 em callback-style
File: src/AppManager.js:1, src/AppManager.js:37-77
Description: Todo o acesso ao banco usa a API de callbacks do `sqlite3`, gerando 4 níveis de aninhamento no checkout e contadores manuais no relatório.
Impact: Callback hell, tratamento de erro inconsistente, impossível usar `try/catch`/transações de forma legível.
Recommendation: Substituir APIs Deprecated (playbook #10) — wrapper Promise (`util.promisify` / pequeno helper `run/get/all`) e `async/await`.

## Deprecated APIs
- src/utils.js:17-23 — hash de senha caseiro com `Buffer.toString('base64')` → `crypto.scrypt` com salt (ou `bcrypt`/`argon2`).
- src/AppManager.js:1, 7, 37-133 — API callback-style do `sqlite3` → wrapper Promise (`util.promisify`) ou `sqlite`/`better-sqlite3`.

================================
Total: 14 findings
================================

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
