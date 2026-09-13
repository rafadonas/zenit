# Plano de repaginação completa da dashboard

## Objetivo

Transformar a dashboard em uma experiência operacional calma, explicável e
responsiva, mantendo segurança, proveniência e aprovação humana. A repaginação é
incremental: não será uma substituição total em uma branch longa.

## Problemas a resolver

- telas densas, com hierarquia e padrões diferentes;
- CSS e páginas grandes dificultam trabalho simultâneo;
- dados, ações e limitações competem visualmente;
- mapa ainda parece uma camada técnica, não uma ferramenta de navegação e decisão;
- status, classe histórica e cobertura vegetal podem ser confundidos;
- estados de falha/ausência/desatualização não são consistentes;
- filas de revisão repetem estruturas e não formam uma jornada coesa.

## Arquitetura de informação proposta

```text
Visão geral
Monitoramento
  Corredor e mapa
  Segmento/zonas
Decisões
  Recomendações
  Aprovações e auditoria
Campo
  Inspeções e fotos
  Planejamento/roçada
Resultados
  Pós-serviço
  Histórico e relatórios
Administração (somente quando autorizada)
```

A navegação exibida depende do papel, mas URLs e proteção no servidor continuam
sendo a fonte de autorização. Esconder botão não substitui controle de acesso.

## Especificação por tela

### Login

**Pergunta respondida:** quem está entrando, em qual ambiente e com qual perfil?

- marca/direção discreta, formulário central e explicação curta;
- sessão local demonstrativa claramente identificada;
- campo, validação e erro sem enumerar usuário;
- loading impede submissão duplicada;
- link de suporte/configuração somente se existir processo real;
- redirect para rota permitida, nunca para URL externa arbitrária.

### Visão geral

**Pergunta respondida:** qual é a situação e o que precisa de mim agora?

- primeira faixa: status do dado, rodovia e data;
- segunda faixa: até quatro métricas úteis, cada uma com fonte/escopo;
- coluna principal: corredor resumido e distribuição de atenção;
- coluna lateral: “Próximas ações” por papel;
- seção inferior: exceções, qualidade/inconclusivos e atividade recente;
- zero-state orienta importação/configuração sem inventar números.

### Corredor e mapa

**Pergunta respondida:** onde está a condição e qual evidência sustenta isso?

- busca por rodovia, km e segmento;
- filtros: data/fonte, zona, status, N1/N2/N3, cobertura e confiança/qualidade;
- seletor de “modo de cor” evita sobrepor três semânticas;
- mapa ocupa a maior área; painel lateral apresenta seleção;
- mobile usa bottom sheet não bloqueante;
- detalhe: identificação, 100 m, zona, classe/status, cobertura, data, método,
  confiança, limitações e ação segura;
- lista equivalente com mesma ordenação/filtros;
- URL guarda filtros/seleção não sensíveis para compartilhamento;
- tiles indisponíveis não apagam feições/lista já carregadas.

### Detalhe do segmento

**Pergunta respondida:** o que sabemos, o que não sabemos e qual histórico existe?

- cabeçalho com road/km/side/zone e data status;
- abas/âncoras: situação, evidências, histórico, recomendações, auditoria;
- comparação temporal só une fontes comparáveis;
- “unknown/inconclusivo” tem explicação e caminho para inspeção;
- ação primária depende do papel e nunca é “Autorizar roçada” por inferência.

### Recomendações

**Pergunta respondida:** quais casos exigem decisão humana?

- lista paginada/virtualizada com filtros persistentes;
- cada item mostra motivo, regra/modelo/versão, fonte/data e qualidade;
- painel de evidência preserva contexto do mapa;
- ações: aprovar recomendação permitida, rejeitar com razão, solicitar inspeção;
- conflito/alteração concorrente retorna estado atual sem sobrescrever;
- lote só quando a regra de domínio autorizar e cada item permanecer auditável.

### Fotos e evidências

**Pergunta respondida:** a evidência é suficiente, íntegra e relacionada ao caso?

- viewer grande com zoom/rotação por controles;
- metadados de captura, hash, upload, GPS/precisão, ponto e origem;
- checklist de qualidade e razão de rejeição estruturada;
- comparação lado a lado apenas para imagens temporalmente compatíveis;
- fila reutilizável para inspeção, roçada e pós-serviço com vocabulário específico;
- bytes ausentes/corrompidos não removem o manifesto nem a trilha.

### Planejamento e roçada

**Pergunta respondida:** existe um plano revisado e elegível para o estado atual?

- separar recomendação, aprovação, planejamento e execução;
- equipe/equipamento/clima/segurança mostram origem e validade;
- artefatos preparados mantêm “ensaio/simulado” em destaque;
- nenhum toggle local promove elegibilidade operacional;
- ações críticas exigem contexto, confirmação e registro humano.

### Resultados e histórico

**Pergunta respondida:** o que foi executado, validado e aprendido?

- linha do tempo de eventos e responsáveis;
- antes/depois com data, fonte e compatibilidade;
- medições, cobertura, qualidade e exceções;
- resumos simulados separados de resultados reais;
- relatórios mostram metodologia, limitações e proveniência.

## Componentização planejada

Estrutura indicativa, a ser refinada sem mudança arquitetural grande em um único
ticket:

```text
apps/dashboard/src/
  app/                    # rotas e composição fina
  components/
    ui/                   # primitivas sem domínio
    layout/               # shell, nav, headers
    data-status/          # provenance/status/quality
    map/                  # mapa, layers, legend, fallback list
    recommendations/
    evidence/
  features/               # queries, state, domain composition
  styles/                 # tokens, base, utilities
  lib/                    # clientes e transformações puras
```

Não mover tudo de uma vez. Extraia uma unidade, adicione testes, migre uma tela e
apague duplicação comprovadamente não usada.

## Plano específico do mapa

### Fase M1 — robustez e linguagem

- estado loading/empty/error/offline;
- atribuição da base;
- legendas separadas e modo de cor;
- hover/focus/selected consistentes;
- data/fonte/validade no painel;
- lista equivalente.

### Fase M2 — navegação

- busca rodovia/km;
- filtros combináveis com chips e limpar tudo;
- fit bounds da seleção;
- deep-link de estado não sensível;
- teclado: mover na lista, focar feição e abrir detalhe.

### Fase M3 — desempenho

- solicitar por bbox/zoom quando necessário;
- cancelar requests obsoletos;
- cache curto com chave de filtros/versão;
- simplificação de visualização preservando geometria canônica;
- medir parse, render e interação com volume-alvo.

### Fase M4 — cobertura vegetal

Somente após GEO-003: camada/tipo manual ou modelado com fonte, método, data,
qualidade e `unknown`. Nunca produzir árvore/grama apenas por uma cor de pixel ou
NDVI. Resultado modelado começa em modo não operacional.

## Dados e contratos

Frontend não deve remapear significado de classe por conta própria. Contratos
devem fornecer identificador estável, geometria/SRID esperado, temporalidade,
fonte, status do dado, classe/status/tipo separados e permissões de ação.

Se o payload atual não atender, primeiro medir a lacuna; depois abrir ticket API
com ADR/OpenAPI. Não acoplar a página diretamente a resposta não versionada.

## Testes de aceite da repaginação

- rotas em 360/768/1024/1280/1440 e zoom 200%;
- teclado completo e foco previsível;
- leitor de tela nos fluxos críticos;
- contraste e reduced motion;
- loading/empty/partial/stale/error/forbidden;
- manager e supervisor com ações corretas;
- data preparada/simulada/inconclusiva nunca perde o rótulo;
- nenhuma ação silenciosa de roçada;
- mapa com e sem tiles, mouse, teclado e lista;
- métricas/payload/desempenho registrados antes/depois;
- lint, typecheck, testes e build verdes.

## Fora do escopo da repaginação P0

- comprar/contratar provedor de mapa;
- criar modelo de árvore/grama;
- promover dado preparado a real;
- redesenhar autenticação operacional/IdP;
- adicionar biblioteca de UI ou observabilidade sem aprovação;
- reescrever backend apenas para adequar um mockup.
