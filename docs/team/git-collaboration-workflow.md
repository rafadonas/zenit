# Fluxo Git para pessoas e IAs

Este fluxo é obrigatório para trabalho distribuído. Seu objetivo é impedir que
duas pessoas sobrescrevam o trabalho uma da outra e fazer cada mudança chegar ao
repositório remoto com evidências verificáveis.

## Regras inegociáveis

- uma branch curta por ticket/pacote de trabalho;
- uma working tree ou worktree por pessoa/IA;
- nunca desenvolver, commitar ou dar push diretamente em `main`;
- nunca usar `--force`, `--force-with-lease`, reescrever histórico compartilhado,
  apagar branch ou executar hard reset sem autorização específica;
- não misturar dois tickets independentes na mesma branch;
- só enviar a branch após revisar diff, confirmar critérios e executar testes;
- integração em `main` acontece por pull request revisado;
- depois do merge, a próxima tarefa nasce da `main` remota atualizada.

## 1. Registrar a atribuição

Antes de editar, registre no quadro do grupo:

```text
Ticket: WEB-006
Responsável: <pessoa>
Assistente de IA: <ferramenta/conversa, se útil>
Branch: codex/web-006-corridor-map-v2
Arquivos reservados: <lista>
Base commit: <git rev-parse HEAD>
Estado: IN_PROGRESS
```

Se outro ticket reservou o mesmo arquivo central, divida o escopo ou espere o
predecessor ser integrado. Não deixe duas IAs editarem o mesmo arquivo e tente
“resolver depois”.

## 2. Criar a branch a partir da base correta

Com working tree limpa:

```bash
git status --short --branch
git switch main
git pull --ff-only origin main
git switch -c codex/<ticket-lowercase>-<slug>
git status --short --branch
```

Se já houver modificações locais, pare e identifique quem é o dono. Não use stash,
reset ou checkout para esconder/apagar trabalho sem entender sua origem.

### Alternativa com worktree

Útil quando a mesma pessoa coordena mais de uma IA:

```bash
git fetch origin
git worktree add -b codex/<ticket-lowercase>-<slug> \
  ../zenit-<ticket-lowercase> origin/main
```

Cada IA recebe o caminho de uma worktree diferente. A remoção da worktree/branch
fica para depois do merge e requer confirmação de que não existe trabalho pendente.

## 3. Implementar sem ampliar o escopo

- cole o ticket completo no prompt;
- leia `AGENTS.md`, contratos, ADRs e testes relacionados;
- liste arquivos que serão alterados;
- faça mudanças pequenas e mantenha o repositório executável;
- não adicione dependências, rede, migração ou arquitetura sem aprovação;
- atualize testes e documentação junto do comportamento;
- consulte frequentemente `git status --short` e `git diff --stat`.

## 4. Confirmar se está correto

A IA deve produzir uma tabela ou checklist como esta antes do commit:

| Critério de aceite | Evidência | Resultado |
| --- | --- | --- |
| `<critério do ticket>` | `<teste, arquivo/linha ou validação manual>` | PASS/FAIL |

Validação mínima:

```bash
git status --short
git diff --check
git diff --stat
git diff
```

Depois execute os gates da frente descritos em `execution-roadmap.md` e
`development-setup.md`. A IA deve registrar comando, exit code e resumo do
resultado. Se não puder executar um gate, o ticket não é apresentado como
completamente validado: registre a limitação e decida com o responsável.

Checklist de revisão:

- comportamento pedido foi implementado e fora de escopo não entrou;
- testes cobrem sucesso, falha e autorização negativa quando aplicável;
- dados real/estimated/simulated/prepared/inconclusive estão corretos;
- nenhum segredo, dado pessoal, fonte bruta ou arquivo grande foi adicionado;
- `data/raw` continua intocado;
- logs/erros não expõem informação sensível;
- acessibilidade, responsividade ou offline foram testados conforme a frente;
- lockfiles, OpenAPI e migrações só mudaram intencionalmente;
- documentação e ADR estão coerentes;
- não existe autorização automática de roçada nem uso de demo para treino/relatório.

## 5. Commitar

Adicione explicitamente os arquivos do ticket; evite `git add .` quando houver
qualquer arquivo inesperado:

```bash
git add <arquivos-do-ticket>
git diff --cached --check
git diff --cached --stat
git diff --cached
git commit -m "<imperative English summary>"
```

Depois confirme:

```bash
git status --short --branch
git show --stat --oneline HEAD
```

Uma working tree suja significa que a entrega ainda precisa explicar ou tratar os
arquivos restantes. Não crie commit vazio para aparentar conclusão.

## 6. Sincronizar com a main sem reescrever histórico

Antes do push final:

```bash
git fetch origin
git merge --no-edit origin/main
```

Se houver conflito:

1. identifique o significado das duas alterações;
2. consulte o dono do contrato/arquivo central;
3. resolva sem descartar silenciosamente nenhum lado;
4. execute novamente todos os gates afetados;
5. faça o commit de merge/resolução quando necessário.

Não use rebase seguido de force-push em branch já compartilhada. Após sincronizar,
repita pelo menos `git diff --check` e os testes que podem ser afetados pela main.

## 7. Dar push somente na branch do ticket

Descubra e confira o nome antes de enviar:

```bash
git branch --show-current
git status --short --branch
git push -u origin codex/<ticket-lowercase>-<slug>
```

O nome retornado por `git branch --show-current` deve ser exatamente a branch do
ticket e nunca `main`. Se o push falhar por atualização remota, não force: faça
`git fetch`, entenda os commits remotos e coordene com quem também usa a branch.

## 8. Abrir o pull request

Use a interface do provedor Git ou uma CLI já instalada/aprovada. Base: `main`;
compare: branch do ticket. O PR deve conter:

```markdown
## Objetivo
<resultado observável e ticket>

## O que mudou
- <mudança>

## Critérios de aceite
- [x] <critério> — <evidência>

## Testes
- `<comando>` — PASS, <resumo>

## Validação manual
- <perfil, rota/device, viewport/rede e resultado>

## Segurança, dados e proveniência
- <impacto e limites>

## Screenshots
<somente quando úteis e sem dados pessoais/segredos>

## Limitações e rollback
- <não feito, risco restante e como reverter>
```

Peça revisão aos donos necessários: técnica sempre; Design/Produto para UI;
domínio/data owner para vegetação; segurança para identidade/upload/privacidade;
API + consumidor para contrato/migração.

## 9. Depois da revisão

- responda comentários com mudança ou justificativa técnica;
- novos commits passam pelos mesmos gates e são enviados normalmente, sem force;
- não faça merge sem aprovação/política do grupo;
- depois do merge, marque o ticket `DONE` e registre commit/PR integrado;
- comece novo ticket atualizando `main` e criando nova branch;
- limpeza de branch/worktree é uma ação separada, feita somente após confirmar que
  o merge existe e não há trabalho local pendente.

## Instrução curta para colar em toda conversa de IA

```text
Trabalhe exclusivamente na branch codex/<ticket>-<slug>. Ao terminar, compare
cada critério de aceite com evidência objetiva, revise o diff completo, execute
todos os testes aplicáveis, confirme que não há segredo/dado bruto/alteração fora
do escopo, faça commit coeso em inglês, sincronize com origin/main por merge sem
reescrever histórico, repita os gates afetados e dê push somente nessa branch.
Nunca faça push direto em main nem use force-push. Entregue a descrição completa
do pull request e não declare sucesso para testes que não executou.
```
