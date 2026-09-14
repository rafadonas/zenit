# GOV-001: inventario visual e funcional da dashboard

- Data de execucao: 2026-09-14
- Responsavel: Guilherme
- Branch: `feature/gov-001-dashboard-inventory`
- Base local: `e622dd5`
- Escopo: rotas atuais da dashboard em 360, 768, 1024 e 1440 px; estados sem API,
  estados autenticados com mock local explicito, rotulos de dado e lacunas para
  os proximos tickets WEB.

## Ambiente

O Docker nao esta disponivel no PATH desta estacao, e `.tools/docker/bin/docker.exe`
tambem nao existe. Por isso, a stack completa com PostgreSQL, MinIO e API real nao
foi executada nesta rodada.

Foram usados dois modos de captura:

1. Dashboard Next.js isolado em `http://localhost:3000`, com API ausente. Esse
   modo valida estados de falha e confirma que as telas nao substituem dados por
   simulacao quando a API nao responde.
2. Dashboard Next.js contra uma API mock temporaria em `localhost:8000`, criada
   somente para este inventario, com dados explicitamente marcados como mock,
   `estimated`, `prepared`, `historical` ou `simulated`. Esse modo valida sucesso
   visual, empty states autenticados e rotulos de seguranca sem depender de dados
   reais.

As evidencias locais foram gravadas em:

- `data/processed/gov-001-dashboard-inventory/`
- `data/processed/gov-001-dashboard-inventory/mock-success/`

Esses caminhos ja sao ignorados pelo Git por estarem sob `data/processed/`.
Nenhuma captura contem segredo, credencial real, dado pessoal ou arquivo bruto.

## Rotas cobertas

| Rota | Dono funcional | Estados capturados | Proximo ticket |
| --- | --- | --- | --- |
| `/login` | Guilherme/Rafael | formulario local sem sessao; redirecionamento com sessao mockada | `WEB-004` |
| `/overview` | Guilherme | falha de API; sucesso mockado preparado | `WEB-005` |
| `/corridor` | Guilherme/Lucas | falha de API; mapa com segmentos estimados e classe historica mockada | `WEB-006` |
| `/recommendations` | Guilherme/Rafael | falha de API; fila mockada com decisao humana | `WEB-007` |
| `/photo-reviews` | Guilherme/Rafael | sessao ausente; empty autenticado preparado | `WEB-008` |
| `/mowing-photo-reviews` | Guilherme/Rafael | sessao ausente; empty autenticado simulado | `WEB-008` |
| `/mowing-post-service-summaries` | Guilherme/Rafael | sessao ausente; empty autenticado simulado | `WEB-009` |

## Resultado por largura

| Largura | Resultado geral | Observacoes |
| --- | --- | --- |
| 360 px | Passa sem overflow horizontal | Login e corredor cabem, mas o mapa fica muito alto e a navegacao ocupa muitas linhas. |
| 768 px | Passa sem overflow horizontal | Conteudo continua em coluna estreita em varias rotas. |
| 1024 px | Passa sem overflow horizontal | A hierarquia funciona, mas ainda parece mobile ampliado em telas de decisao/campo. |
| 1440 px | Passa sem overflow horizontal | Uso ruim de espaco: varias rotas ficam presas a esquerda com grande area vazia. |

Todas as capturas automatizadas registraram `mainCount=1` e `mainIdCount=1`.

## Estados de falha

Com a API ausente, `/overview`, `/corridor` e `/recommendations` exibem o estado:

> A API nao respondeu. Os dados nao foram substituidos por uma simulacao.

Isso preserva a regra de dominio: falha de comunicacao nao pode virar dado
preparado, estimado ou simulado inventado.

Lacuna: o mesmo fallback generico diz "carregar o corredor" mesmo quando o usuario
esta em `/recommendations`. O texto deve ficar contextual em `WEB-002`/`WEB-003`.

## Auditoria de rotulos de dado

| Superficie | Rotulos observados | Avaliacao |
| --- | --- | --- |
| Login | "Acesso local do MVP", "Nenhuma revisao autoriza trabalho de campo" | Bom limite de seguranca; precisa melhorar composicao desktop. |
| Overview | "Ambiente preparado", "dados reais e preparados permanecem separados", "inconclusiva" | Rotulos presentes; precisa explicitar fonte/data junto aos indicadores. |
| Corredor/mapa | "Eixo estimado", "uso operacional bloqueado", "Vegetacao historico", referencia `28/03/2025` | Bom limite; legenda ainda mistura altura historica e mapa visual sem seletor de semantica. |
| Recomendacoes | "Demonstracao segura", "Nenhuma decisao libera trabalho de campo", confianca baixa | Bom limite; filtros e painel de evidencia ainda faltam. |
| Fotos preparadas | "Fotos preparadas", "Nenhuma revisao autoriza campo", "Fila vazia" | Bom limite; falta estrutura comum para filas e viewer/metadata rico. |
| Fotos pos-servico | "dados permanecem simulados", "Regua visivel nao valida altura" | Bom limite; deve compartilhar componente com fila de fotos preparadas. |
| Resumos pos-servico | "pos-servico simulado", "Nao e conclusao operacional" | Bom limite; consolidacao/historico ficam para `WEB-009`. |

## Achados priorizados

| ID | Severidade | Achado | Evidencia | Ticket |
| --- | --- | --- | --- | --- |
| GOV-001-A1 | Alta | Layout desktop subutiliza a tela: overview, recommendations e telas de campo ficam em uma coluna estreita colada a esquerda em 1440 px. | `mock-success/1440-overview.png`, `mock-success/1440-recommendations.png`, `1440-mowing-post-service-summaries.png` | `WEB-003`, `WEB-005` |
| GOV-001-A2 | Alta | Nao existe biblioteca de primitivas; estados, cards, alertas, badges, formularios e filas repetem CSS/markup por rota. | `apps/dashboard/src/app/styles.css` e rotas revisadas | `WEB-001`, `WEB-002`, `WEB-008` |
| GOV-001-A3 | Media | O fallback de erro das rotas de dados usa texto generico de corredor fora do contexto da rota. | Capturas sem API de `/recommendations` | `WEB-002`, `WEB-003` |
| GOV-001-A4 | Media | Mapa mobile e util, mas ocupa uma coluna longa; desktop precisa painel/lista equivalente e filtros persistentes. | `mock-success/0360-corridor.png`, `mock-success/1440-corridor.png` | `WEB-006` |
| GOV-001-A5 | Media | A navegacao atual e horizontal em todas as larguras; ainda nao ha shell responsivo com sidebar, compacto tablet e navegacao movel dedicada. | Todas as capturas de 360/768/1440 px | `WEB-003` |
| GOV-001-A6 | Media | Estados autenticados vazios existem para filas, mas cada pagina expressa isso de forma propria. | `mock-success/0360-photo-reviews.png`, `mock-success/0360-mowing-photo-reviews.png` | `WEB-002`, `WEB-008` |
| GOV-001-A7 | Baixa | O login mobile cabe, mas o link de retorno e o indicador flutuante do navegador podem competir no rodape. | `0360-login.png` | `WEB-004` |

## Cobertura mobile Flutter

Flutter nao esta disponivel no PATH e `.tools/flutter/bin/flutter.bat` nao existe
nesta estacao. A captura visual das jornadas mobile nativas nao foi executada.

Foi feita auditoria de codigo e testes existentes. O app ja esta decomposto apos
`MOB-001` e contem superficies para login, ordens preparadas, inspecao, ensaio de
rocada, status de sincronizacao e valores somente leitura. Os testes mantem rotulos
`prepared`, `simulated`, offline e sync. A captura visual real deve ser refeita por
Gabriel ou em ambiente com Flutter/emulador durante `MOB-002`/`MOB-003`.

## Gates executados

| Gate | Resultado |
| --- | --- |
| `npm run dashboard:lint` | PASS |
| `npm run dashboard:typecheck` | PASS |
| `npm run dashboard:test` | PASS - 42 arquivos, 137 testes |
| `npm run dashboard:build` | PASS |
| `docker version` | ENV FAIL - Docker nao encontrado |
| `flutter --version` | ENV FAIL - Flutter nao encontrado |

`npm install` reportou 3 vulnerabilidades de dependencia de desenvolvimento
ja documentadas no baseline de seguranca. Nenhum `npm audit fix` foi executado,
pois alteracao de dependencia/lockfile nao pertence ao escopo de Guilherme.

## Criterios de aceite

| Criterio | Resultado |
| --- | --- |
| Sete rotas em 360, 768, 1024 e 1440 px | PASS para dashboard isolado e mockado; sucesso real depende de Compose/API. |
| Loading/empty/error/success registrados | PARTIAL: error e empty/success mockados registrados; loading apenas por `loading.tsx` e transicoes observadas rapidamente. |
| Jornadas mobile existentes capturadas | BLOCKED por ausencia de Flutter/emulador local; auditoria de codigo registrada. |
| Rotulos preparado/simulado auditados | PASS; nenhum achado de promocao operacional silenciosa. |
| Capturas sem segredo | PASS; somente localhost, mock e estados sem dados pessoais. |
| Problemas ligados a tickets | PASS; achados mapeados para `WEB-001` a `WEB-009`. |

## Proximo passo recomendado

Iniciar `WEB-001` em `feature/web-001-design-tokens`, extraindo tokens de
`apps/dashboard/src/app/styles.css` para `apps/dashboard/src/styles/` sem alterar
visualmente as rotas alem do necessario para estabilizar cor, tipografia, foco,
movimento e breakpoints.
