# Divisão da equipe por pessoa

Este documento é a fonte de roteamento para as quatro pessoas que desenvolvem o
ZENIT com assistentes de IA. Ao iniciar uma conversa, a pessoa informa apenas
quem é; a IA deve identificar sua trilha abaixo, conferir o estado real do
repositório e continuar o primeiro pacote elegível da fila.

## Identificação obrigatória

Use uma destas mensagens na primeira interação:

```text
Sou Rafael. Continue minha trilha do projeto ZENIT.
Sou Guilherme. Continue minha trilha do projeto ZENIT.
Sou Lucas. Continue minha trilha do projeto ZENIT.
Sou Gabriel. Continue minha trilha do projeto ZENIT.
```

`Rafa`, `Rafael` e `dono do projeto` identificam a trilha de Rafael. Se o nome
não corresponder inequivocamente a uma das quatro pessoas, a IA deve perguntar
quem está trabalhando antes de editar.

## O que a IA deve fazer depois de receber o nome

1. Ler `AGENTS.md`, `README.md`, `docs/team/README.md`, este documento e o
   pacote completo em `work-packages.md`.
2. Inspecionar branch, working tree, branches remotas, PRs e commits recentes.
3. Não presumir que a fila abaixo continua atual: confirmar se o predecessor foi
   integrado em `origin/main` e se o pacote já tem branch ou PR.
4. Escolher somente o primeiro pacote elegível da trilha da pessoa. Se estiver
   bloqueado, realizar documentação ou validação explicitamente permitida, sem
   implementar a parte bloqueada.
5. Declarar ticket, resultado esperado, branch, arquivos reservados, fora de
   escopo e testes antes de editar.
6. Criar/continuar uma branch exclusiva `feature/<ticket>-<slug>`,
   `fix/<ticket>-<slug>` ou `docs/<ticket>-<slug>`, conforme o tipo da mudança,
   baseada na `origin/main` atual. Nunca reutilizar a branch de outro ticket.
7. Implementar, confirmar cada critério com evidência, atualizar documentação,
   fazer commit em inglês, sincronizar sem reescrever histórico, fazer push da
   branch e abrir PR. Nunca enviar diretamente para `main`.

Se houver alterações locais de outra pessoa, conflito de arquivo reservado,
segredo, nova dependência, migração ou decisão arquitetural não autorizada, a IA
deve parar essa parte e explicar exatamente o que precisa ser coordenado.

## Rafael (você) — integração, API, autenticação e segurança

**Missão:** manter os contratos e a integração do produto coerentes, corrigir a
autenticação, coordenar merges e garantir que nenhuma frente quebre segurança,
proveniência ou regras operacionais.

**Fila principal:**

1. `QA-001` — matriz E2E e baseline de integração;
2. `SEC-001` — threat model incremental;
3. `API-001` — análise de view models e paginação;
4. `WEB-004` — login e sessão, somente após `WEB-002` integrado e em
   coordenação com Guilherme;
5. `API-002`, `OPS-001` e `OPS-002` somente depois das decisões externas que os
   mantêm bloqueados.

**Arquivos/domínios preferenciais:** `services/api/`, autenticação e autorização,
`contracts/`, testes E2E/segurança, CI, Compose e documentação de integração.

**Não editar sem combinar:** estilos/componentes compartilhados com Guilherme,
pipeline geoespacial com Lucas e arquivos centrais do Flutter com Gabriel.

**Revisões:** revisa contratos consumidos pelas outras frentes e recebe revisão
de Guilherme em login/UX, Lucas em contratos geoespaciais e Gabriel em contratos
mobile.

## Guilherme — marca, design system, dashboard e mapa

**Missão:** conduzir a repaginação completa da dashboard, com sistema visual
coerente, acessibilidade, responsividade e mapa operacionalmente legível.

**Fila principal:**

1. `GOV-001` — inventário visual e funcional;
2. `WEB-001` — tokens e folhas de estilo;
3. `WEB-002` — primitivas acessíveis;
4. `WEB-003` — shell responsivo;
5. `WEB-005` → `WEB-006` → `WEB-007` → `WEB-008` → `WEB-009`, um
   ticket e um PR por vez;
6. `GOV-002` e `WEB-010` continuam bloqueados até as respectivas decisões.

**Arquivos/domínios preferenciais:** `apps/dashboard/`, estilos, componentes web,
conteúdo de interface, testes web e documentação de design.

**Limite do mapa:** pode melhorar mapa-base, interação e visualização sem esperar
modelo. A camada que afirma diferenciar árvore, grama ou arbusto depende de
`GEO-003`; até lá deve usar `unknown` ou dados claramente preparados.

**Revisões:** revisa UX das telas de Rafael e tokens mobile de Gabriel; recebe
revisão de Lucas nas legendas/camadas geoespaciais e de Rafael em autenticação e
autorização.

## Lucas — geoespacial, Planet, qualidade de dados e IA vegetal

**Missão:** construir a evidência geoespacial reproduzível, preparar o uso
controlado da Planet e definir como distinguir grama, árvore, arbusto e outras
coberturas sem transformar inferência em medição de altura.

**Fila principal:**

1. concluir/revisar a fundação Planet descrita no `ADR-0067`;
2. `GEO-001` — taxonomia de cobertura, inicialmente como proposta;
3. `GEO-002` — protocolo de ground truth;
4. `GOV-003` — apoiar homologação sem modificar `data/raw/`;
5. `GEO-003` → `GEO-004` somente após aprovações e migração autorizada;
6. `AI-001` → `AI-002` → `AI-003` somente quando os predecessores e gates
   humanos estiverem formalmente aprovados.

**Próximos incrementos Planet, sempre em tickets separados:** validação da
conta/catálogo; persistência com migração aprovada; controle de cota; Orders e
downloads; checksums/linhagem; proxy/cache de tiles; processamento offline do
trecho piloto de 1 km. Descoberta de catálogo não autoriza download.

**Arquivos/domínios preferenciais:** `services/geospatial-worker/`, documentos de
qualidade de dados, manifests derivados, provedores de imagem e testes geo.

**Revisões:** revisa mapa/camadas de Guilherme; recebe revisão de Rafael para
contratos/migrações e de Gabriel para requisitos de coleta em campo.

## Gabriel — aplicativo mobile, coleta de campo e sincronização

**Missão:** tornar o aplicativo Flutter modular, legível em campo, resiliente
offline e seguro ao coletar fotos, GPS, medições e decisões humanas.

**Fila principal:**

1. `MOB-001` — decompor arquitetura preservando comportamento;
2. `MOB-002` — tokens/componentes, depois dos tokens de Guilherme estabilizados;
3. `MOB-003` — jornada de ordem e coleta;
4. `MOB-004` — central de sincronização;
5. `MOB-005` somente após `GEO-002`, `GEO-003` e políticas aprovadas;
6. `MOB-006` somente após piloto e processo de release aprovados.

**Arquivos/domínios preferenciais:** `apps/mobile/`, testes Flutter, cofre local,
fila offline, captura e documentação mobile.

**Não alterar unilateralmente:** OpenAPI, payloads ou regras de permissão; abrir
ticket contratual e coordenar com Rafael. Dados preparados/simulados devem
continuar rotulados como tais.

**Revisões:** revisa impactos mobile dos contratos de Rafael e protocolo de campo
de Lucas; recebe revisão visual de Guilherme.

## Arquivos compartilhados e integração

Estes arquivos não pertencem permanentemente a uma pessoa. Quem precisar alterá-los
deve reservá-los no quadro do grupo e avisar os demais antes de começar:

- `contracts/openapi.json` e modelos compartilhados;
- `compose.yaml`, arquivos de CI e manifestos/lockfiles;
- `apps/dashboard/src/app/layout.tsx` e estilos globais;
- `apps/mobile/lib/main.dart` e `apps/mobile/lib/app_controller.dart`;
- `infra/migrations/` e qualquer novo número de migração;
- documentos que mudam contratos, regras de domínio ou status de tickets.

Rafael coordena a ordem de integração, mas não aprova sozinho marca, regra de
vegetação, dado oficial, privacidade ou elegibilidade operacional. Cada PR exige
ao menos uma revisão humana de outra pessoa; mudanças de alto risco seguem a
revisão especializada definida no playbook.

## Quadro mínimo do grupo

Mantenham este estado em uma ferramenta compartilhada, issue ou project board;
não usem o mesmo arquivo Markdown editado por quatro branches ao mesmo tempo.

| Ticket | Pessoa | Branch | Arquivos reservados | Estado | Base | PR |
| --- | --- | --- | --- | --- | --- | --- |
| exemplo | Guilherme | `feature/web-001-design-tokens` | `apps/dashboard/src/styles/` | `IN_PROGRESS` | `<sha>` | `<url>` |

Estados permitidos: `READY`, `IN_PROGRESS`, `IN_REVIEW`, `BLOCKED` e `DONE`.

## Regra de continuidade

Quando a pessoa disser “continue”, a IA não deve reiniciar a trilha nem escolher
um trabalho novo automaticamente. Primeiro deve procurar branch/PR em andamento
daquela pessoa. Se existir, continua e conclui esse ticket. Somente inicia o
próximo item quando o anterior estiver integrado ou houver autorização explícita
para executar em paralelo sem conflito.
