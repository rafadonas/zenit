# Roteiro de execução e divisão do trabalho

Este roteiro organiza o trabalho em ondas. Uma onda pode ter várias frentes em
paralelo, mas nenhuma tarefa pode ignorar seus gates de dependência.

## Princípios de execução

1. Um pacote de trabalho por branch e por responsável.
2. Mudanças de contrato, migração ou dependência têm dono único e revisão cruzada.
3. Componentes compartilhados são estabilizados antes da migração de todas as telas.
4. Dados preparados/simulados permanecem explicitamente rotulados.
5. Modelos não avançam para treinamento antes da aprovação de taxonomia e dataset.
6. Cada onda termina com testes, documentação, demonstração e decisão go/no-go.

## Ondas

### Onda 0 — alinhamento e baseline

Objetivo: permitir que várias pessoas trabalhem sem duplicação.

- ler e aceitar este hub;
- executar o setup e registrar divergências locais;
- congelar screenshots/baseline das rotas atuais;
- atribuir donos de frontend, backend/contrato, geoespacial/IA, mobile e QA;
- abrir decisões pendentes de marca, dados e piloto.

Saída: todos conseguem rodar testes; quadro de tickets tem responsáveis; nenhuma
mudança de código ainda depende de uma suposição não registrada.

### Onda 1 — fundação visual e arquitetura de UI

Pode executar em paralelo:

- **Web foundation:** tokens CSS, primitivas acessíveis, shell e estados comuns;
- **Mobile foundation:** tokens Dart, decomposição inicial e navegação preservando
  comportamento;
- **Data governance:** taxonomia de cobertura e protocolo de anotação em rascunho;
- **QA:** matriz de dispositivos, rotas e estados, sem adicionar dependência.

Bloqueio: a migração visual massiva espera os tokens e componentes mínimos.

### Onda 2 — jornada principal da dashboard

Ordem recomendada:

1. login e seleção clara de perfil/ambiente;
2. shell global e overview;
3. mapa/corredor;
4. recomendações e decisão humana;
5. filas de foto/campo;
6. resultados e pós-serviço.

Backend pode preparar view models e paginação em paralelo, desde que qualquer
mudança de OpenAPI tenha ticket próprio e seja integrada antes do consumidor.

### Onda 3 — mapa e evidência vegetal

- melhorar interação, filtros, lista equivalente e desempenho do mapa;
- separar visualmente status, N1/N2/N3 e tipo de cobertura;
- homologar taxonomia e guia de anotação;
- implementar coleta manual `unknown/grass/shrub/tree/mixed` somente após ADR;
- criar dataset manifestado e baseline offline, sem expor resultado como atual.

O mapa bonito não depende de modelo. Camadas “árvore/grama” dependem.

### Onda 4 — experiência móvel de campo

- migrar telas para a nova arquitetura sem mudar contratos;
- tornar ordem, rota, coleta, evidência e sincronização legíveis offline;
- adicionar guia de captura e anotação manual validada;
- testar recuperação após processo encerrado, rede instável e conflito;
- iniciar GPS real apenas após política, permissão e protocolo de piloto aprovados.

### Onda 5 — piloto operacional

Requer decisões externas: eixo oficial, identidade, equipes, critérios de qualidade,
provedores, privacidade, suporte e responsável pela aprovação.

- staging isolado;
- importação homologada;
- usuários e papéis reais;
- observabilidade, backup/restauração e runbooks;
- piloto pequeno, reversível e auditado;
- avaliação humana antes de qualquer expansão.

### Onda 6 — inteligência e otimização

- baseline de classificação/segmentação aprovado;
- avaliação espacial/temporal e calibração;
- execução em shadow mode;
- revisão de erros por especialistas;
- promoção versionada e reversível;
- crescimento/altura avançados somente com sensores e ground truth adequados.

## Frentes e responsabilidades

| Frente | Responsável por | Não deve editar sem coordenação |
| --- | --- | --- |
| Product/Design | fluxos, tokens, conteúdo, protótipos, aceite visual | contratos e regras de domínio |
| Dashboard | Next.js, componentes, mapa, testes web | migrações e app mobile |
| API/Contracts | endpoints, autorização, OpenAPI, migrações | inferências de modelo sem data owner |
| Geo/Data/AI | ingestão, qualidade, taxonomia, datasets, modelos | autorização de campo ou relatório |
| Mobile | Flutter, offline, captura, sync UX | contrato sem ticket de API |
| QA/Security/Platform | CI, acessibilidade, ameaça, deploy, observabilidade | redefinição unilateral de produto |

Em equipe pequena, uma pessoa pode assumir duas frentes, mas nunca duas mudanças
simultâneas que reservem o mesmo arquivo central.

## Arquivos de alto conflito

Reserve explicitamente antes de editar:

- `apps/dashboard/src/app/styles.css` e `apps/dashboard/src/app/layout.tsx`;
- shell/header e componentes compartilhados do dashboard;
- `apps/mobile/lib/main.dart` e `apps/mobile/lib/app_controller.dart`;
- `contracts/openapi.json`;
- `package-lock.json`, `apps/mobile/pubspec.lock` e manifestos de dependência;
- `compose.yaml` e overrides;
- `infra/migrations/` — cada número de migração é atribuído uma única vez;
- modelos centrais de autenticação, autorização e sincronização.

## Sequência de integração

```text
governança + baseline
        |
        +--> tokens/componentes web --> shell --> telas --> mapa avançado
        |
        +--> arquitetura mobile -----> telas --> coleta real (após aprovação)
        |
        +--> taxonomia --> anotação --> dataset --> baseline --> shadow mode
        |
        +--> decisões operacionais --> staging --> piloto controlado
```

## Gates por tipo de mudança

### Dashboard

`lint`, `typecheck`, testes, build, teclado, zoom 200%, larguras-alvo e ausência de
console errors. Mapa também exige teste sem rede de tiles e lista alternativa.

### API/geoespacial

Ruff, pytest, OpenAPI check, migração forward/down quando aplicável, SRID explícito,
idempotência, checksums/linhagem e autorização negativa.

### Mobile

format check, analyze, testes, build debug, reinício offline, fila pendente, logout
com dados não reconhecidos e validação em emulador/aparelho-alvo.

### Dados/modelos

manifesto, licença/consentimento, checksum, divisão espacial/temporal, métricas por
classe, model card, revisão humana, reprodutibilidade e bloqueio de demo/simulado.

## Cadência sugerida

- início da semana: escolher pacotes `READY`, donos e arquivos;
- diariamente: registrar bloqueio, mudança de contrato e evidência relevante;
- antes do merge: revisão técnica + revisão de domínio/UX conforme risco;
- fim da onda: demo com dados claramente rotulados, retrospectiva e atualização
  dos estados em `work-packages.md`.

Não use estimativa de calendário como autorização para pular predecessor. O menor
incremento demonstrável e seguro tem preferência sobre uma grande reescrita.
