# Playbook para colaboradores usando IA

## Objetivo

Fazer com que assistentes diferentes produzam mudanças pequenas, compatíveis e
auditáveis. A IA ajuda a investigar e implementar; decisões de domínio, marca,
operação, privacidade e promoção de modelo continuam humanas.

## Prompt inicial recomendado

Copie e preencha:

```text
Você está trabalhando no monorepo ZENIT.
Leia integralmente AGENTS.md, README.md, docs/team/README.md, o ticket <ID> em
docs/team/work-packages.md e todos os documentos/ADRs citados nele.

Objetivo: <resultado observável>.
Escopo permitido: <arquivos/módulos>.
Fora de escopo: <itens>.
Predecessores confirmados: <IDs/commits>.
Branch/worktree exclusiva: <nome/caminho>.
Critérios de aceite: <colar do ticket + complementos>.
Testes obrigatórios: <comandos>.

Antes de editar, inspecione o estado real e escreva um plano pequeno. Não invente
dados oficiais, não use demo/simulado para treino/relatório, não autorize roçada,
não modifique data/raw, não adicione dependência nem altere arquitetura sem pedir.
Preserve alterações alheias. Ao terminar, revise diff, execute testes, atualize a
documentação necessária e faça commit coeso em inglês. Não dê push sem pedido.
```

## Protocolo obrigatório da IA

### 1. Descobrir

- ler instruções e ticket inteiro;
- executar `git status --short --branch`;
- localizar arquivos com `rg --files`/`rg`;
- ler testes, contrato e ADRs antes da implementação;
- identificar se os dados são real/estimated/simulated/prepared/inconclusive;
- declarar arquivos afetados, riscos e testes.

### 2. Planejar

O plano deve ter no máximo um passo em andamento e responder:

- qual comportamento muda;
- quais arquivos serão reservados;
- qual contrato/estado deve permanecer igual;
- quais falhas e acessibilidade serão cobertas;
- se há dependência, migração, rede, arquitetura ou decisão externa.

Pare e peça autorização para dependência de produção, mudança arquitetural,
operação destrutiva, rede não prevista, dados sensíveis ou expansão material.

### 3. Implementar

- usar inglês em código, identificadores, nomes técnicos e commits;
- seguir estilo local e preferir extrações pequenas;
- nunca reformatar arquivos não relacionados;
- não desfazer mudanças existentes;
- manter autenticação/autorização no servidor;
- manter SRID e unidades explícitos;
- registrar checksum/linhagem em dados derivados;
- preservar idempotência, auditoria e versões;
- renderizar status de dado e temporalidade na UI;
- usar `unknown/inconclusive` em vez de falsa certeza.

### 4. Verificar

- ler o diff completo, inclusive lockfiles e código gerado;
- executar gates do ticket;
- testar caso feliz, falhas, permissão negativa e regressão;
- verificar data/simulação/proveniência;
- para UI: teclado, foco, larguras, zoom e estados assíncronos;
- para contrato: gerar OpenAPI intencionalmente e validar consumidores;
- para migração: forward/down e volume/banco de teste apropriado;
- para mobile: restart/offline/retry além de testes unitários.

### 5. Entregar

- atualizar ADR/contrato/guia quando o comportamento mudar;
- commit coeso com mensagem imperativa em inglês;
- reportar commit, arquivos, comportamento, testes, limitações e próximo ticket;
- não fazer push, merge, deploy ou promoção sem pedido explícito.

## Convenção de branch e commit

- branch: `codex/<ticket-lowercase>-<short-slug>`;
- um pacote por branch;
- exemplos: `codex/web-002-ui-primitives`, `codex/mob-001-feature-split`;
- commit: `Add dashboard data status primitives`, `Refactor mobile order flow`;
- não usar “misc”, “changes” ou commit misturando frontend, modelo e infra sem
  necessidade contratual demonstrada.

## Coordenação entre IAs

Mantenha um quadro externo simples:

| Ticket | Pessoa/IA | Branch | Arquivos reservados | Estado | Base commit |
| --- | --- | --- | --- | --- | --- |

Regras:

- uma pessoa é dona de cada arquivo central por vez;
- mudanças em `contracts/openapi.json`, migrações, lockfiles e Compose são
  serializadas;
- dependentes começam do commit integrado do predecessor, não de cópia manual;
- não peça a duas IAs para “redesenhar toda a dashboard” simultaneamente;
- divida por foundation, shell, rota ou domínio depois que interfaces comuns forem
  aceitas;
- conflitos são resolvidos por quem entende o contrato, não aceitando ambos
  automaticamente.

## Formato de handoff

```markdown
## Ticket e resultado
- ID:
- Resultado observável:
- Commit:

## Arquivos alterados
- caminho: motivo

## Contratos e decisões
- preservados/alterados:
- ADR/OpenAPI/migração:

## Testes executados
- comando — resultado/contagem

## Validação manual
- cenário, perfil, viewport/device e resultado

## Segurança e dados
- status/proveniência/simulação:
- riscos revisados:

## Limitações e próximo passo
- o que não foi feito:
- ticket recomendado:
```

## Checklists especializados

### Dashboard/mapa

- não depender somente de cor/hover/mapa;
- data, fonte, status e limitação visíveis;
- status operacional, N1/N2/N3 e cobertura separados;
- sem tiles ainda há lista/detalhe;
- sem KPI fictício ou “atual” para 2025-03-28;
- manager/supervisor testados separadamente.

### Dados/IA

- `data/raw` intocado;
- manifesto/checksum/licença/split;
- zero demo/simulado em treino;
- baseline e erros por classe/zona;
- baixa confiança → inspeção/abstenção;
- model/version/review/rollback;
- nenhuma promoção automática.

### Mobile

- password não persistida, token no storage seguro;
- cofre e pendências preservados;
- UUID criado antes de envio e retry idempotente;
- manifesto antes dos bytes;
- restart, offline e conflito;
- GPS/foto marcados simulados enquanto não reais;
- build de produção exige HTTPS e processo de assinatura aprovado.

### API/segurança

- autenticação e escopo por rodovia/papel;
- CSRF/origin/cookie no dashboard;
- erro sem segredo + correlation ID;
- auditoria append-only;
- migração/contrato versionados;
- testes negativos e concorrência.

## Sinais de que a IA deve parar e perguntar

- o ticket exige valor “oficial” que não está aprovado;
- seria necessário editar/substituir `data/raw`;
- há segredo, dado pessoal ou documento fonte para publicar;
- duas branches alteram o mesmo contrato/migração/arquivo central;
- a solução adiciona dependência, provedor, serviço ou acesso de rede;
- a ação apaga volume, histórico, evidência ou reescreve Git;
- o modelo seria treinado com demonstração/simulação;
- a UI implicaria autorização de roçada sem ato humano;
- não é possível distinguir erro técnico de evidência inconclusiva.

## Revisão humana mínima

Toda mudança recebe revisão técnica. Além dela:

- UI/conteúdo: Product/Design + acessibilidade;
- regra de vegetação: especialista de domínio/data owner;
- autenticação/upload/privacidade: segurança;
- migração/contrato: backend + consumidor;
- modelo/dataset: geo/ML + domínio + governança;
- elegibilidade de campo/relatório: responsável operacional autorizado.
