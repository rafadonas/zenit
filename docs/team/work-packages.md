# Pacotes de trabalho

Este é o backlog técnico distribuível. Estado inicial: `READY` significa que o
ticket pode ser detalhado/implementado respeitando dependências; `BLOCKED`
significa que falta decisão ou evidência externa. Ao começar, troque para
`IN_PROGRESS`, registre responsável e branch no quadro do grupo. Não use este
arquivo como substituto de uma ferramenta de gestão concorrente.

A atribuição nominal e a ordem de trabalho de Rafael, Guilherme, Lucas e Gabriel
estão em [`team-assignments.md`](team-assignments.md). A fila pessoal não torna
um ticket bloqueado elegível nem substitui seus predecessores.

## Modelo de cabeçalho para cada execução

```text
Ticket:
Responsável:
Branch/worktree:
Branch remota/PR:
Arquivos reservados:
Dependências confirmadas:
Testes planejados e evidências de aceite:
Decisões/assunções:
```

## A. Governança e baseline

### GOV-001 — inventário visual e funcional (`READY`, P0)

**Escopo:** capturar as sete rotas do dashboard em 360, 768, 1024 e 1440 px;
registrar loading/empty/error/success; capturar as jornadas mobile existentes.

**Saída:** evidências ignoradas pelo Git ou pequenas imagens aprovadas, matriz de
regressão e problemas ligados a tickets. Não registrar dados pessoais.

**Aceite:** todas as rotas e estados têm proprietário; rótulos preparado/simulado
são auditados; nenhuma captura contém segredo.

### GOV-002 — decisões de marca (`READY` para escopo acadêmico, P0)

**Decisão aceita:** registrar que ZENIT é projeto acadêmico/estudantil sem
relação direta, patrocínio, autorização ou licença de marca da Motiva.

**Escopo:** documentar limites de uso: identidade própria ZENIT, menção Motiva
somente como contexto de desafio/fonte, sem logotipo, assets, cores oficiais,
slogans ou linguagem de endosso.

**Aceite:** ADR aceito, design system e tokens classificados como placeholders
acadêmicos do ZENIT, documentação deixa claro que uso oficial da Motiva permanece
bloqueado.

### GOV-003 — homologação dos dados de origem (`BLOCKED`, P1)

**Escopo:** validar eixo, zonas, atributos do KMZ e datas com data owner.

**Aceite:** decisão assinada/versionada, origem/checksum, SRID, mapeamento, limites
e exceções registrados. O arquivo bruto não é modificado.

## B. Design system e dashboard

### WEB-001 — tokens e folhas de estilo (`READY`, P0)

**Predecessor:** GOV-001.

**Arquivos-alvo:** novo diretório `apps/dashboard/src/styles/`, layout global e
CSS existente. Evitar mudança visual extensa neste ticket.

**Implementação:** extrair cor, tipografia, espaço, raio, sombra, movimento,
breakpoints e z-index; manter aliases de compatibilidade; adicionar preferência
`prefers-reduced-motion` e tokens de foco.

**Aceite:** nenhuma cor de estado crítica fica hardcoded nas páginas; build e
snapshots atuais continuam válidos; contraste documentado; sem nova dependência.

### WEB-002 — primitivas acessíveis (`READY`, P0)

**Predecessor:** WEB-001.

**Escopo:** Button, IconButton, Badge, DataStatus, Alert, Card, EmptyState,
ErrorState, Skeleton, Field, Select, Tabs e Dialog/Drawer. Use HTML nativo quando
possível; dependência externa exige aprovação.

**Aceite:** estados hover/focus/disabled/loading, nome acessível, teclado, alvo de
44 px e testes unitários; API dos componentes documentada.

### WEB-003 — shell responsivo (`READY`, P0)

**Predecessor:** WEB-001, WEB-002.

**Escopo:** sidebar desktop, modo compacto tablet, navegação móvel, cabeçalho,
breadcrumb, título, contexto de papel/rodovia e área principal.

**Aceite:** rota ativa, skip link, um `main`, foco após navegação, 200% zoom sem
perda; manager/supervisor veem apenas ações permitidas.

### WEB-004 — login e sessão (`READY`, P0)

**Predecessor:** WEB-002.

**Escopo:** reorganizar formulário, demonstrar claramente ambiente/perfil,
mensagens seguras, progresso e recuperação. Não armazenar token no cliente.

**Aceite:** login por teclado, erro genérico sem enumeração, redirect seguro,
sessão expirada compreensível e testes de CSRF/origin existentes verdes.

### WEB-005 — overview orientada a decisão (`READY`, P0)

**Predecessor:** WEB-003.

**Escopo:** hierarquia “situação → atenção → próxima ação”, indicadores com data e
status de dado, resumo do corredor, fila humana e atalhos por papel.

**Aceite:** entendimento em até 10 s em teste moderado interno; sem KPI fictício;
empty/error/stale; fonte e referência temporal visíveis.

### WEB-006 — corredor e mapa v2 (`READY`, P0)

**Predecessor:** WEB-003. **Dependência para tipo vegetal:** GEO-003.

**Escopo:** busca rodovia/km, filtros, legenda, seleção, drawer, lista equivalente,
estado sem tiles, carregamento por viewport e estilos definidos no plano.

**Aceite:** mapa continua útil sem mouse e sem tiles; seleção sincroniza lista;
N1/N2/N3 nunca aparentam ser dado atual; 642+ feições sem congelamento perceptível
na máquina de referência; testes de transformação e interação.

### WEB-007 — recomendações e aprovação (`READY`, P0)

**Predecessor:** WEB-003.

**Escopo:** fila única com filtros; painel de evidência; regra/modelo/versão;
confiança como faixa/qualidade, não altura; aceitar/rejeitar/inspecionar com
confirmação e justificativa.

**Aceite:** nenhuma recomendação autoriza roçada silenciosamente; trilha humana e
estados de conflito preservados; ações protegidas por papel.

### WEB-008 — filas de foto e campo (`READY`, P0)

**Predecessor:** WEB-002, WEB-003.

**Escopo:** extrair estruturas comuns das páginas de photo review; combinar
navegação e separar claramente inspeção, roçada e pós-serviço.

**Aceite:** atalhos, zoom, metadados, hash/proveniência e decisões sem duplicação;
imagem indisponível não impede ler o caso; testes das três filas.

### WEB-009 — resultados e histórico (`READY`, P0)

**Predecessor:** WEB-003, WEB-008.

**Escopo:** consolidar resumos pós-serviço, histórico, comparação e limitações.

**Aceite:** antes/depois não mistura datas/fontes; resultados simulados não entram
em relatório oficial; exportação mantém status e proveniência.

### WEB-010 — regressão visual e telemetria (`BLOCKED`, P1)

**Decisão:** ferramenta de screenshot/monitoramento e política de privacidade.
Não adicionar serviço ou dependência sem aprovação.

## C. Dados geoespaciais e inteligência vegetal

### GEO-001 — taxonomia de cobertura (`READY` para desenho, P0/P1)

**Escopo:** propor `unknown`, `grass/herbaceous`, `shrub`, `tree`, `mixed` e
`non_vegetation`; definir oclusão, objeto dominante, copa sobre faixa e conflito.

**Aceite:** revisão de especialista e data owner antes de virar schema oficial.

### GEO-002 — protocolo de ground truth (`READY` para desenho, P1)

**Predecessor:** GEO-001.

**Escopo:** amostragem por zona/rodovia/estação, foto/escala/altura/GPS, dupla
anotação, adjudicação e privacidade.

**Aceite:** piloto de anotação mede concordância; licença/consentimento e retenção
documentados; dados demo excluídos.

**Proposta:** [`../data-quality/ground-truth-protocol-proposal.md`](../data-quality/ground-truth-protocol-proposal.md),
com [`tooling reproduzível`](../data-quality/ground-truth-protocol.md)
(`proposed`; aprovações e piloto real pendentes).

### GEO-003 — contrato de cobertura vegetal (`BLOCKED`, P1)

**Predecessor:** aprovação de GEO-001 e ADR.

**Escopo:** propriedades de feição e API para tipo, método, fonte, validade,
confiança/qualidade e estado de revisão. `unknown` é obrigatório.

**Aceite:** migração reversível, OpenAPI, autorização, proveniência e testes; UI
não recebe significado implícito por cor.

### GEO-004 — dataset versionado (`BLOCKED`, P1)

**Predecessor:** GEO-002, GOV-003.

**Escopo:** manifesto, checksums, splits espaciais/temporais, rótulos adjudicados,
licença e exclusões.

**Aceite:** zero dado simulado/demo; reconstrução reproduzível; estatísticas por
classe, zona e fonte; nenhum arquivo grande commitado.

### AI-001 — baseline árvore/grama (`BLOCKED`, P1)

**Predecessor:** GEO-004; aprovação para dependências/compute.

**Escopo:** primeiro baseline simples e interpretável, depois comparação com
segmentação; avaliação offline apenas.

**Aceite:** macro-F1/IoU e recall por classe, matriz de confusão, calibração,
holdout espacial/temporal, erros amostrados e model card. Sem integração automática.

### AI-002 — shadow mode (`BLOCKED`, P2)

**Predecessor:** AI-001 aceito, observabilidade e política de revisão.

**Aceite:** previsões invisíveis para decisão operacional, comparação humana,
drift, rollback e gate formal de promoção.

### AI-003 — altura/crescimento avançados (`BLOCKED`, P2)

**Predecessor:** sensor e ground truth homologados.

**Aceite:** erro em centímetros por zona e faixa de altura, intervalo/limitação,
validação temporal. NDVI isolado não satisfaz o ticket.

## D. Aplicativo móvel

### MOB-001 — decompor a arquitetura sem alterar comportamento (`READY`, P0)

**Arquivos de alto conflito:** `main.dart`, `app_controller.dart`.

**Escopo:** separar app shell, features, widgets, estado e navegação em commits
pequenos; preservar gateway, cofre e modelos.

**Aceite:** testes existentes verdes, mesmo fluxo e payloads, reinício/offline;
classes centrais deixam de concentrar UI e regras de múltiplas features.

### MOB-002 — tokens e componentes de campo (`READY`, P0)

**Predecessor:** design system definido; pode acompanhar MOB-001 com arquivos
reservados distintos após o shell existir.

**Escopo:** cores semânticas, tipografia, espaçamento, botões, cards, banners,
status, campos, stepper e estados offline/sync.

**Aceite:** 44 px, contraste, escala de fonte, semantics labels, uso sob luz forte,
nenhuma cor como único sinal.

### MOB-003 — jornada de ordem e coleta (`READY`, P0)

**Predecessor:** MOB-001, MOB-002.

**Escopo:** inbox, detalhe, confirmação, progresso, três pontos, fotos, resumo e
envio; manter todo dado preparado/simulado atual.

**Aceite:** usuário sempre sabe o próximo passo, o que está salvo localmente e o
que foi enviado; fechar/reabrir não perde rascunho.

### MOB-004 — central de sincronização (`READY`, P0)

**Predecessor:** MOB-001.

**Escopo:** estados pending/sending/accepted/rejected/conflict, tentativas,
dependência manifesto-bytes e recuperação acionável.

**Aceite:** modo avião, timeout, 401, 409, processo encerrado e retomada cobertos;
retry não duplica evento.

### MOB-005 — captura orientada e rótulo manual (`BLOCKED`, P1)

**Predecessor:** GEO-002, GEO-003, política de privacidade/permissões.

**Escopo:** guia de enquadramento, escala, qualidade, tipo manual, motivo unknown,
GPS real e feedback antes de salvar.

**Aceite:** não sobrescreve EXIF/evidência silenciosamente; registra precisão,
fonte e consentimento; falha fechada quando requisito não é atendido.

### MOB-006 — release operacional (`BLOCKED`, P1)

**Predecessor:** piloto aprovado.

**Escopo:** assinatura, custódia, distribuição, crash policy, suporte, atualização,
MDM se aplicável e revogação.

## E. API, plataforma, segurança e QA

### API-001 — view models e paginação de filas (`READY` para análise, P0)

**Escopo:** medir payloads/chamadas atuais e propor apenas endpoints que reduzam
complexidade real. Alteração exige ADR/OpenAPI e migração de consumidores.

### API-002 — identidade operacional (`BLOCKED`, P1)

**Decisão:** IdP, MFA, ciclo de vida, escopo por rodovia, recertificação e contas
de serviço. Sessão demo/local não é solução produtiva.

### OPS-001 — staging e observabilidade (`BLOCKED`, P1)

**Escopo:** ambiente isolado, logs estruturados, métricas, traces, SLOs, alertas e
redação de dados. Requer infraestrutura e política aprovadas.

### OPS-002 — backup, restauração e incidente (`BLOCKED`, P1)

**Aceite:** restauração testada de banco/objetos, RPO/RTO, rotação, responsável,
runbook e exercício; nunca declarar backup apenas por existir volume.

### QA-001 — matriz E2E de jornada (`READY`, P0)

**Escopo:** manager/supervisor, sucesso e falha, web/mobile/API, offline e
acessibilidade. Inicialmente manual/reprodutível; automação requer decisão de ferramenta.

### SEC-001 — threat model incremental (`READY`, P0/P1)

**Escopo:** autenticação, autorização, upload, offline vault, mapa externo,
proveniência, prompt/tooling de IA e supply chain.

**Aceite:** ativos, atores, fronteiras, ameaças, controles e riscos aceitos; testes
negativos ligados aos itens de maior risco.

## F. Planet e imagens

Incrementos da trilha geoespacial, sempre em tickets separados. Descoberta de
catálogo não autoriza download, e nenhum item desta seção torna resultado
operacional ou oficial.

### PLANET-003 — persistir cenas com migração aprovada (`DONE`, gate pendente, P1)

**Escopo:** metadados de cena PlanetScope em AOI e janela limitadas, com migração
reversível e gravação idempotente.

**Aceite:** [`../data-quality/planet-catalog-metadata-persistence.md`](../data-quality/planet-catalog-metadata-persistence.md).
Implementado em `0d36d57`; faltam revisão da migração por outra pessoa, destino
de banco explícito, testes de persistência e decisão de retenção.

### PLANET-005 — controle de cota (`DONE`, aprovação do orçamento pendente, P1)

**Predecessor:** PLANET-003 e PLANET-004.

**Escopo:** orçamento versionado de área, bytes e chamadas; consumo derivado de
`planet_order`; checagem antes de cada Order; extrato; repasse da chave aos
serviços que precisam dela.

**Aceite:** [`../data-quality/planet-quota-control.md`](../data-quality/planet-quota-control.md).
Implementado com a migração `0044`, `zenit-planet-quota` e verificação embutida
no Order; faltam os valores aprovados do orçamento e a revisão da migração.

### PLANET-006 — proxy e cache controlado de tiles (`DONE`, desligado até aprovação, P2)

**Predecessor:** PLANET-005; linhas L3 e L6 do
[registro de licenças](../governance/licence-register.md) e decisão D6 da
[base de privacidade](../governance/privacy-baseline.md).

**Escopo:** rota autenticada no backend, cache com TTL e limite por usuário,
atribuição e desligamento por padrão. OSM permanece direto, sem proxy.

**Aceite:** [`../data-quality/planet-tile-proxy.md`](../data-quality/planet-tile-proxy.md).
Implementado atrás de `TILE_PROXY_ENABLED=false`; ligar depende da licença de
tiles e da decisão sobre endereço do visitante.

### PLANET-007 — checksums e linhagem dos ativos (`DONE`, política pendente, P1)

**Predecessor:** PLANET-003 e PLANET-004.

**Escopo:** cadeia cena → Order → ativo → artefato derivado, com auditoria que
recalcula checksums e exporta manifesto determinístico.

**Aceite:** [`../data-quality/asset-checksums-and-lineage.md`](../data-quality/asset-checksums-and-lineage.md).
Implementado com a migração `0045` e `zenit-asset-lineage`; faltam a política de
divergência e a revisão da migração.

### PLANET-008 — processar offline o trecho piloto de 1 km (`DONE`, AOI e licença pendentes, P2)

**Predecessor:** PLANET-005, PLANET-007, AOI homologada e licença de
processamento.

**Escopo:** processar apenas ativos cacheados e verificados, sem rede, com
máscara UDM2 e resultado por segmento e zona.

**Aceite:** [`../data-quality/planet-pilot-offline-processing.md`](../data-quality/planet-pilot-offline-processing.md).
Implementado com `zenit-planet-process`, sem migração nova; faltam a AOI
homologada, a licença de processamento e a revisão do processador.

## Ordem recomendada para começar agora

1. GOV-001;
2. WEB-001 e MOB-001 em paralelo;
3. WEB-002, MOB-002, GEO-001 e QA-001 em paralelo;
4. WEB-003 e MOB-003;
5. WEB-004/005/006/007/008 por donos separados após estabilizar compartilhados;
6. GEO-002 e decisões externas;
7. somente então contratos, dataset, IA e coleta operacional.
