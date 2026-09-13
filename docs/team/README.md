# ZENIT team delivery hub

Este diretório é o ponto de entrada para pessoas e assistentes de IA que vão
continuar o ZENIT em paralelo. Ele transforma o estado atual do repositório em
trabalho distribuível, sem tratar funcionalidades demonstrativas como operação
real.

## Ordem obrigatória de leitura

Antes de editar código, leia nesta ordem:

1. [`../../AGENTS.md`](../../AGENTS.md) — regras permanentes do projeto;
2. [`../../ZENIT_Manual_Mestre_para_Codex.pdf`](../../ZENIT_Manual_Mestre_para_Codex.pdf)
   — objetivo, domínio e limites do produto;
3. [`../../README.md`](../../README.md) — arquitetura e comandos já existentes;
4. [`current-state-and-gaps.md`](current-state-and-gaps.md) — o que existe e o
   que ainda falta;
5. [`team-assignments.md`](team-assignments.md) — identificar Rafael, Guilherme,
   Lucas ou Gabriel e selecionar a trilha correta;
6. [`execution-roadmap.md`](execution-roadmap.md) — ordem, dependências e divisão
   entre frentes;
7. o plano da sua frente;
8. ADRs, contratos e documentos de qualidade citados no ticket escolhido.

Não use apenas este diretório para decidir regras de domínio. Se houver conflito,
`AGENTS.md`, ADRs aceitos, contratos versionados e o Manual Mestre têm precedência.

## Documentos por finalidade

| Documento | Use quando |
| --- | --- |
| [`team-assignments.md`](team-assignments.md) | informar quem está trabalhando e descobrir sua fila, limites e revisores |
| [`current-state-and-gaps.md`](current-state-and-gaps.md) | precisar entender o que é real, preparado, simulado ou ausente |
| [`execution-roadmap.md`](execution-roadmap.md) | escolher a próxima onda e saber o que bloqueia o quê |
| [`work-packages.md`](work-packages.md) | assumir um ticket com escopo, arquivos e aceite definidos |
| [`dashboard-redesign-plan.md`](dashboard-redesign-plan.md) | trabalhar no dashboard, mapa ou componentes web |
| [`design-system.md`](design-system.md) | criar ou revisar qualquer interface, texto ou estado visual |
| [`vegetation-intelligence-plan.md`](vegetation-intelligence-plan.md) | trabalhar com árvore, grama, imagens, satélite, rótulos ou modelos |
| [`mobile-app-plan.md`](mobile-app-plan.md) | trabalhar no Flutter, experiência de campo ou sincronização |
| [`development-setup.md`](development-setup.md) | instalar, executar, testar ou diagnosticar o ambiente |
| [`external-services-and-secrets.md`](external-services-and-secrets.md) | descobrir chaves, credenciais, serviços e requisitos por ambiente |
| [`ai-contributor-playbook.md`](ai-contributor-playbook.md) | orientar uma IA, abrir uma frente ou entregar uma mudança |
| [`git-collaboration-workflow.md`](git-collaboration-workflow.md) | criar branch, validar, commitar, enviar e abrir PR |

## Prioridades

- **P0 — demonstrativo confiável:** corrigir regressões, tornar a experiência
  coerente, acessível e testável sem inventar dados operacionais.
- **P1 — piloto controlado:** substituir pressupostos preparados por dados,
  responsáveis, políticas e validações reais formalmente aprovadas.
- **P2 — inteligência avançada:** modelos, automações e otimizações que só podem
  existir depois de dados reais validados e gates de segurança.

P0 não significa “produção”. O estado atual é um MVP demonstrativo/preparado.

## Como uma pessoa assume trabalho

1. Informe seu nome e consulte sua trilha em
   [`team-assignments.md`](team-assignments.md).
2. Escolha somente o primeiro pacote elegível `READY` da sua fila em
   [`work-packages.md`](work-packages.md).
3. Confirme que seus predecessores estão `DONE` ou que a execução paralela está
   explicitamente autorizada.
4. Registre responsável, branch `codex/<ticket>-<slug>` e arquivos reservados no
   quadro compartilhado do grupo.
5. Cole o ticket completo na conversa da IA; não mande apenas o título.
6. Trabalhe em branch/worktree própria. Não edite simultaneamente arquivos que
   outra frente reservou.
7. Execute todos os gates do ticket e os gates globais afetados.
8. Confirme os critérios de aceite com evidências, não apenas com “parece correto”.
9. Entregue commit coeso, faça push da própria branch e abra um pull request.
10. Registre riscos, testes, limitações e próximos passos no handoff/PR.

## Estado inicial deste plano

O plano foi criado a partir do repositório em 2026-09-12. Antes de começar uma
onda, atualize o estado dos pacotes de trabalho; código e ADRs posteriores podem
ter alterado dependências. Datas existentes nas planilhas continuam sendo datas
de referência de **2025-03-28**, não dados atuais.
