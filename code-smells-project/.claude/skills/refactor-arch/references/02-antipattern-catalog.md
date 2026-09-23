# Catálogo de Anti-Patterns (Fase 2)

Escala de severidade usada em todo o catálogo:

- **CRITICAL**: falha grave de arquitetura ou segurança. Impede funcionamento correto, expõe dados sensíveis (credenciais hardcoded, SQL Injection) ou quebra completamente a separação de responsabilidades (God Class com banco + lógica + roteamento juntos).
- **HIGH**: forte violação de MVC/SOLID que dificulta muito manutenção e testes (lógica de negócio pesada dentro de Controllers, acoplamento forte sem injeção de dependência, estado global mutável).
- **MEDIUM**: padronização, duplicação de código, gargalo de performance moderado (N+1, middleware mal usado, validação ausente nas rotas).
- **LOW**: legibilidade, nomenclatura, magic numbers.

Para cada item: nome, severidade típica, sinais de detecção (o que procurar no código) e por que importa. A severidade típica é um ponto de partida — ajuste para cima/baixo conforme o impacto real observado no projeto (ex: um endpoint que executa SQL arbitrário sem autenticação é tecnicamente a mesma causa-raiz de SQL Injection, mas pode ser classificado separadamente para não duplicar contagem).

---

### 1. Hardcoded Credentials / Secrets — CRITICAL
**Sinais:** literais de string atribuídos a variáveis como `SECRET_KEY`, `password`, `senha`, `apiKey`, `api_key`, `token`, `dbPass`, `smtp_password`, direto no código-fonte (não lidos de `os.environ`/`process.env`).
**Por quê:** qualquer pessoa com acesso ao repositório (inclusive se vazar ou for público) tem em mãos chaves de produção — sessão, banco, gateway de pagamento, e-mail.

### 2. SQL Injection — CRITICAL
**Sinais:** queries montadas por concatenação/interpolação de string com dado vindo de `request` (`"...WHERE id = " + str(id)`, f-strings com input do usuário dentro do SQL, template literals JS com variável direta no SQL) em vez de placeholders (`?`, `%s`, bind parameters do ORM).
**Por quê:** qualquer campo de entrada pode ser usado para ler, alterar ou apagar dados fora do escopo pretendido.

### 3. God Class / God File — CRITICAL
**Sinais:** um único arquivo/classe que cria o schema do banco, define rotas HTTP, valida entrada, executa regra de negócio e roda queries — tudo junto, sem separação por responsabilidade.
**Por quê:** impossível testar uma parte isoladamente; qualquer mudança pequena arrisca quebrar um comportamento não relacionado em outro canto do mesmo arquivo.

### 4. Endpoint Perigoso Sem Autenticação — CRITICAL/HIGH
**Sinais:** rota que executa uma ação destrutiva ou administrativa (reset de banco, execução de SQL arbitrário, exclusão em massa) sem nenhuma checagem de identidade/permissão antes de agir.
**Por quê:** é uma porta aberta — o dano potencial não depende de "achar" uma vulnerabilidade, só de conhecer a URL.

### 5. Fat Controller / Lógica de Negócio na Rota — HIGH
**Sinais:** handler de rota com dezenas de linhas de `if/else` de regra de negócio, cálculo, formatação e orquestração multi-tabela, em vez de delegar a um Model/Service e só traduzir HTTP ⇄ chamada de função.
**Por quê:** mistura a responsabilidade de "falar HTTP" com "aplicar regra de domínio", dificultando reuso (job, CLI, outro endpoint) e teste unitário sem subir um servidor.

### 6. Estado Global Mutável / Ausência de Injeção de Dependência — HIGH
**Sinais:** variáveis de módulo mutáveis compartilhadas entre requisições (cache global tipo `globalCache = {}`, contador `totalRevenue` em módulo, conexão de banco singleton acessada via import direto em vez de injetada), sem isolamento por requisição/sessão.
**Por quê:** requisições concorrentes podem se contaminar; impossível testar com um estado limpo sem reiniciar o processo inteiro.

### 7. Ausência de Camada de Persistência (Repository/DAO) — HIGH/MEDIUM
**Sinais:** SQL cru (ou chamadas de ORM equivalentes a SQL cru) espalhado direto dentro dos handlers de rota ou dos controllers, sem um módulo dedicado a "falar com o banco".
**Por quê:** acopla a aplicação inteira ao banco específico; trocar de banco ou testar a lógica sem um banco real vira um projeto à parte.

### 8. Model Anêmico/Procedural (sem entidade de domínio) — MEDIUM
**Sinais:** o "Model" é só um conjunto de funções soltas que devolvem `dict`/objeto genérico a partir do resultado cru do banco, sem encapsular nenhuma regra (equivalente a um Repository disfarçado de Model).
**Por quê:** mistura o papel de Model com o de Repository e acopla os controllers ao formato exato das tabelas — qualquer mudança de coluna se propaga para vários lugares.

### 9. Queries N+1 / Consulta Dentro de Loop — MEDIUM
**Sinais:** um `for` que, a cada iteração, dispara uma nova query ao banco (buscar item → para cada item buscar detalhe → para cada detalhe buscar outro detalhe) em vez de um JOIN ou uma query com `IN (...)`.
**Por quê:** o número de round-trips ao banco cresce linearmente com o volume de dados, degradando performance conforme a base cresce.

### 10. Lógica Duplicada em Múltiplos Lugares — MEDIUM
**Sinais:** a mesma regra (ex: "isso está atrasado?", "isso é válido?") reimplementada de forma independente em mais de um arquivo/rota, em vez de centralizada em uma função/método único chamado de todos os lugares.
**Por quê:** as cópias divergem com o tempo — uma é corrigida, as outras não, e endpoints diferentes passam a responder coisas diferentes para o mesmo dado.

### 11. Exceção Genérica / Silenciosa — MEDIUM
**Sinais:** `except:` sem tipo, `except Exception as e: return generic_error` sem logar detalhes, ou `catch (err) {}` vazio, escondendo a causa raiz de uma falha.
**Por quê:** esconde erros reais, dificulta debugging e observabilidade — o sistema "engole" o problema em vez de sinalizá-lo.

### 12. Validação Ausente ou Ignorada nas Rotas — MEDIUM
**Sinais:** validação existe em um lugar (método no Model, helper) mas as rotas não a chamam — reimplementam checagem inline ou não checam nada; ou rotas que aceitam qualquer payload sem checar tipo/obrigatoriedade dos campos.
**Por quê:** é código morto de um lado (a validação que existe nunca roda) e duplicado/inconsistente do outro.

### 13. Dados Órfãos / Ausência de Cascade em Delete — LOW
**Sinais:** rota de delete que remove só o registro principal sem tratar registros dependentes (filhos ficam apontando para um ID que não existe mais).
**Por quê:** corrompe a integridade referencial ao longo do tempo — sem erro imediato, mas com dado inconsistente acumulando.

### 14. Logging via `print()`/`console.log()` em vez de Logger — LOW
**Sinais:** observabilidade da aplicação inteira depende de `print()`/`console.log()` espalhados pelo código, sem nível de log, sem formato estruturado, sem poder ser desligado em produção.
**Por quê:** funciona em desenvolvimento, mas não escala para produção — não dá para filtrar por severidade nem redirecionar para um sistema de logs.

### 15. Vazamento de Informação Interna em Endpoint Público — LOW
**Sinais:** rota pública (ex: `/health`) devolvendo detalhes internos desnecessários (contagens de tabelas, `SECRET_KEY`, flag de `debug`, caminho do arquivo do banco).
**Por quê:** ajuda um atacante a mapear o sistema antes mesmo de explorar qualquer coisa — não é a falha mais grave, mas é prática ruim de exposição de informação.

---

## APIs Deprecated (verificação obrigatória)

Além do catálogo acima, cheque explicitamente se o projeto usa APIs marcadas como deprecated pela própria linguagem/framework na versão detectada na Fase 1. Sempre reporte o equivalente moderno na recomendação.

| Sinal no código | Deprecated desde | Substituir por |
|---|---|---|
| `datetime.utcnow()` / `datetime.utcfromtimestamp()` (Python) | Python 3.12 | `datetime.now(timezone.utc)` |
| `hashlib.md5()` / `hashlib.sha1()` usados para hash de senha | sempre foi inadequado para senha (não é deprecated formalmente, mas é criptografia insegura equivalente na prática) | `werkzeug.security.generate_password_hash` / `bcrypt` / `argon2` |
| `app.run(debug=True)` como forma de servir em produção (Flask) | prática deprecated pela própria doc do Flask para produção | servidor WSGI dedicado (gunicorn/uwsgi) + `debug=False` fora de desenvolvimento |
| `@app.before_first_request` (Flask) | removido no Flask 2.3+ | inicialização no momento da criação da app (fora do decorator) |
| Callback-style API do driver `sqlite3` do Node sem `util.promisify` em código novo | não é removido, mas é o padrão legado da lib | `sqlite` (wrapper Promise) ou `better-sqlite3` |
| `new Buffer(...)` (Node.js) | Node 10+ | `Buffer.from(...)` / `Buffer.alloc(...)` |
| Hash de senha caseiro (loop manual com `Buffer.toString('base64')` ou similar, em vez de biblioteca de criptografia) | sempre inadequado | `bcrypt`/`argon2` — nunca reinventar hashing de senha |

Se nenhuma API deprecated for encontrada, diga isso explicitamente no relatório ("Nenhuma API deprecated identificada") em vez de omitir a seção.
