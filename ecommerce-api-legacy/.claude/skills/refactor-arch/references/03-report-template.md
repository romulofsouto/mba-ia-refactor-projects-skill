# Template do Relatório de Auditoria (Fase 2)

Use exatamente esta estrutura. Preencha todos os campos com dados reais — nunca deixe um placeholder no relatório final.

```
================================
ARCHITECTURE AUDIT REPORT
================================
Project: <nome-do-projeto>
Stack:   <linguagem> + <framework> <versão>
Files:   <N> analyzed | ~<M> lines of code

## Summary
CRITICAL: <n1> | HIGH: <n2> | MEDIUM: <n3> | LOW: <n4>

## Findings

### [CRITICAL] <Nome do anti-pattern>
File: <arquivo>:<linha ou intervalo de linhas>
Description: <o que está acontecendo, em 1-3 frases, citando o trecho real>
Impact: <consequência concreta — o que pode dar errado por causa disso>
Recommendation: <transformação recomendada, referenciando o padrão do playbook usado na Fase 3>

### [HIGH] <Nome do anti-pattern>
File: <arquivo>:<linha>
Description: <...>
Impact: <...>
Recommendation: <...>

(... repita para cada finding, sempre em ordem decrescente de severidade: CRITICAL → HIGH → MEDIUM → LOW)

## Deprecated APIs
<Liste cada API deprecated encontrada com arquivo:linha e o substituto recomendado, ou escreva "Nenhuma API deprecated identificada".>

================================
Total: <N> findings
================================

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
```

## Regras de preenchimento

- `Files: <N> analyzed | ~<M> lines of code` — use os números reais levantados na Fase 1 (rode uma contagem de linhas, ex: `wc -l` nos arquivos-fonte considerados).
- O `## Summary` precisa bater exatamente com o número de findings listados em `## Findings` — some antes de escrever.
- Cada finding é independente e autocontido — não force dois problemas diferentes dentro de um mesmo finding só para reduzir a contagem, e não separe o mesmo problema em dois findings só para inflar a contagem.
- `File:` sempre no formato `caminho/relativo/ao/projeto.ext:linha` (linha única) ou `arquivo.ext:linha_inicial-linha_final` (intervalo). Nunca "vários lugares" sem listar onde.
- `Recommendation:` deve ser acionável — nomeie a transformação (ex: "Extrair para variável de ambiente", "Parametrizar a query", "Mover para Controller dedicado"), não apenas "melhorar isso".
- Salve uma cópia idêntica deste relatório em `reports/audit-project-N.md` na raiz do repositório, além de imprimir na tela.
