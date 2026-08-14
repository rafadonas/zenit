# ZENIT

Plataforma de monitoramento da vegetação rodoviária que conecta dados
geoespaciais e de satélite, recomendações explicáveis, decisão humana, trabalho
de campo e relatórios auditáveis.

> **Limite atual:** o repositório implementa um MVP demonstrativo. Dados e
> fluxos marcados como `prepared`, `estimated` ou `simulated` não representam
> operação real, não autorizam roçada e não podem alimentar treinamento de
> modelos nem relatórios oficiais.

## Sumário

- [Objetivo e regras essenciais](#objetivo-e-regras-essenciais)
- [Estado atual](#estado-atual)
- [Arquitetura do repositório](#arquitetura-do-repositório)
- [Início rápido](#início-rápido)
- [Dados, proveniência e importação](#dados-proveniência-e-importação)
- [Banco de dados e migrações](#banco-de-dados-e-migrações)
- [Fluxos e APIs principais](#fluxos-e-apis-principais)
- [Desenvolvimento e validação](#desenvolvimento-e-validação)
- [Segurança e limitações conhecidas](#segurança-e-limitações-conhecidas)
- [Documentação](#documentação)

## Objetivo e regras essenciais

O ZENIT busca fechar este ciclo:

```text
dados rodoviários + imagem de satélite + histórico
→ análise por segmento e zona
→ recomendação explicável
→ revisão e decisão humana
→ ordem e coleta móvel offline
→ fotos, medições e sincronização
→ histórico e relatório
```

As regras de domínio que não podem ser flexibilizadas são:

- analisar segmentos de 100 m, separando margem esquerda, margem direita,
  canteiro central e áreas especiais;
- usar 30 cm como limite geral e 10 cm em áreas especiais ou operacionais;
- preservar as classes históricas: N1 abaixo de 10 cm, N2 entre 10 e 30 cm e
  N3 acima de 30 cm;
- encaminhar baixa confiança normalmente para inspeção;
- nunca permitir que a IA autorize uma roçada silenciosamente;
- preservar decisões humanas, versões de regras/modelos, trilha de auditoria e
  proveniência;
- distinguir dados reais, estimados, preparados, simulados e inconclusivos;
- nunca usar dados demonstrativos ou simulados para treinamento ou relatório
  oficial.

As planilhas fornecidas têm data de referência **2025-03-28**. Elas não
descrevem a condição atual da vegetação e não formam uma série de crescimento.

## Estado atual

### Fundação, dados e mapa

- Monorepo com FastAPI/Python, Next.js/TypeScript, Flutter, PostgreSQL/PostGIS,
  MinIO e Docker Compose.
- Catálogo imutável de fontes, checksums, linhagem e importações idempotentes.
- Parsers tipados para KMZ/KML e planilhas, com anomalias documentadas.
- Eixo candidato derivado dos marcos e dividido em 309 segmentos geométricos.
- API GeoJSON por `bbox` e dashboard de corredor somente leitura.

O eixo candidato é apenas para desenvolvimento. Como não foi fornecido um eixo
rodoviário oficial e os marcos contêm inversões e lacunas conhecidas, ele é
marcado como `estimated`, `needs_validation` e
`eligible_for_operations=false`.

### Satélite e recomendação

- Catálogo de cenas e ativos com checksum, execuções versionadas, zonas,
  métricas de qualidade e recomendações explicáveis.
- Descoberta normalizada de Sentinel Hub Catalog e INPE BDC STAC.
- Cinco aquisições Sentinel persistidas somente como metadados `discovered`.
- Validação estatística de uma AOI preparada de 100 m, mantida como
  inconclusiva/inspeção porque o eixo e o buffer não são oficiais e NDVI não é
  altura.
- Recorte NDVI de 5 × 11 pixels, com checksum e linhagem, disponível apenas
  como camada preparada e `partially_cached` no dashboard.
- Baseline de regras com qualidade, explicação, confiança e revisão humana.

Nenhuma cena-fonte completa foi baixada ou aprovada para uso operacional. O
recorte NDVI não representa altura, condição atual ou autorização de roçada.

### Inspeção preparada

- Identidade local de MVP e RBAC de gestor/supervisor por rodovia.
- Fila de recomendações e decisões imutáveis de aceitar, rejeitar ou ajustar.
- Ordem de inspeção preparada com três pontos estimados na linha central.
- Aplicativo Android offline-first com login inicial online, vault AES-256,
  ciclo demonstrativo, três medições, fotos e sincronização idempotente.
- Upload AES-256-GCM, recuperação autorizada e revisão humana de fotos.
- Resumo preparado com mínimo, média, máximo e contagens N1/N2/N3.
- Exportação CSV determinística e auditada.

Todo esse fluxo permanece preparado, com localização simulada, sem execução de
campo e inelegível para relatório oficial.

### Planejamento e ensaio de roçada

- Proposta pós-inspeção e revisão humana separada.
- Ordem de roçada não executável, recursos candidatos, avaliação manual de
  prontidão e decisão exclusiva de planejamento.
- Ensaio móvel simulado com confirmação, início em ponto estimado,
  pausa/retomada equilibradas e finalização.
- Três alturas pós-serviço simuladas e não verificadas, separadas das medições
  de inspeção.
- Uma foto pós-serviço por ponto, guardada no vault criptografado.
- Manifestos sincronizados antes dos bytes; upload explícito e retomável após
  aceitação dos três manifestos.
- Recibo imutável do conteúdo criptografado, ainda marcado como simulado,
  não localizado, não validado e não operacional.
- Recuperação autorizada da versão exata, com descriptografia, verificação de
  integridade e evento de acesso imutável.
- Fila autenticada e revisão humana append-only de qualidade e visibilidade da
  régua, sob política própria e ainda simulada.
- Resumo pós-serviço simulado, gerado somente com três medições digitadas e três
  revisões visuais aceitas, sem transformar foto em altura ou conclusão.
- Histórico gerencial somente leitura do ensaio e das alturas brutas.

Ainda não existem conclusão de roçada validada, atualização do mapa/histórico
ou resumo pós-serviço.

## Arquitetura do repositório

| Caminho | Responsabilidade |
| --- | --- |
| `apps/dashboard` | Dashboard de gestão em Next.js |
| `apps/mobile` | Aplicativo Android offline-first em Flutter |
| `services/api` | API FastAPI e casos de uso de domínio |
| `services/geospatial-worker` | Processamento geoespacial e de satélite |
| `services/ai-worker` | Regras explicáveis e futuros modelos candidatos |
| `packages/contracts` | Contratos compartilhados de API e eventos |
| `infra` | Compose, infraestrutura e migrações SQL |
| `data` | Entradas locais, manifestos e produtos derivados |
| `docs` | Arquitetura, decisões e relatórios de qualidade |

O dashboard mantém a fila de fotos de inspeção em `/photo-reviews` e a fila
separada de fotos pós-serviço simuladas em `/mowing-photo-reviews`.

## Início rápido

### Pré-requisitos

- Python 3.12 a 3.14;
- Node.js 22 ou superior;
- Docker Engine com Docker Compose;
- Flutter apenas para desenvolvimento do aplicativo móvel.

### Configuração local

Copie `.env.example` para `.env` antes de personalizar o ambiente. As senhas de
exemplo são apenas padrões de desenvolvimento e nunca devem ser usadas em
produção.

```bash
cp -n .env.example .env
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
npm install
```

### Subir a plataforma

```bash
docker compose up --build
```

Serviços locais:

| Serviço | Endereço |
| --- | --- |
| Dashboard | `http://localhost:3000` |
| API | `http://localhost:8000` |
| Healthcheck | `http://localhost:8000/health` |
| PostgreSQL/PostGIS | `localhost:5432` |
| MinIO Console | `http://localhost:9001` |

Nesta estação, o Docker roda em modo rootless. Em um novo shell, os binários
locais podem ser selecionados assim:

```bash
export PATH="$PWD/.tools/docker/bin:$PATH"
export DOCKER_HOST="unix:///run/user/$(id -u)/docker.sock"
```

## Dados, proveniência e importação

Coloque os arquivos fornecidos em `data/raw/`. Esse diretório contém evidências
locais imutáveis: não altere os originais e não os adicione ao Git. Consulte
[`data/README.md`](data/README.md) para nomes esperados e regras de manuseio.

Cada importação ou produto derivado deve registrar checksum e linhagem. O
arquivo `classificacao_rocada.kmz` deve ser normalizado sem modificar o original;
mapeamentos de atributos inferidos permanecem pendentes de validação.

Use `zenit-import` para importar uma fonte imutável por vez. Exemplos completos
estão em
[`docs/architecture/source-ingestion.md`](docs/architecture/source-ingestion.md).

O fluxo Sentinel preparado e idempotente para a AOI de validação é:

```bash
zenit-satellite \
  --segment-index 195 \
  --zone left \
  --from-date 2026-07-01 \
  --to-date 2026-08-07
```

Ele é restrito à geometria preparada e não operacional. Leia
[`docs/architecture/satellite-discovery.md`](docs/architecture/satellite-discovery.md)
antes de alterar AOI ou período.

## Banco de dados e migrações

O banco atual exige as migrações `0001` a `0037`, sempre em ordem numérica. Um
volume novo do Compose executa todas automaticamente por
`/docker-entrypoint-initdb.d`. Volumes existentes não são atualizados por esse
mecanismo.

Para uma atualização controlada, aplique somente as migrações ainda ausentes.
Para um banco vazio fora da inicialização automática, execute:

```bash
for migration in infra/migrations/*.sql; do
  docker compose exec -T postgres \
    psql -v ON_ERROR_STOP=1 -U zenit -d zenit < "$migration"
done
```

As migrações preservam uma evolução append-only:

- `0001`–`0007`: catálogo de fontes, staging, eixo/segmentos e fundação
  satelital;
- `0008`–`0010`: revisão de recomendações, identidade/RBAC e ordens de
  inspeção;
- `0011`–`0014`: sincronização móvel, ciclo demonstrativo e manifestos de foto;
- `0015`–`0021`: upload/revisão de mídia, resumo preparado e exportação
  auditada;
- `0022`–`0027`: proposta pós-inspeção, revisão e planejamento de roçada;
- `0028`–`0037`: ensaio simulado, medições, fotos, acesso, revisão, resumo,
  exportação, exceção pós-serviço e decisão humana da exceção.

Decisões detalhadas e invariantes de cada etapa estão em
[`docs/decisions`](docs/decisions).

## Fluxos e APIs principais

Todas as rotas de escrita autenticadas derivam o ator do token verificado. As
rotas abaixo usam o prefixo versionado `/v1`.

### Consulta e análise

| Método e rota | Finalidade |
| --- | --- |
| `GET /health` | Saúde da API |
| `GET /v1/roads/SP021/segments?...` | Segmentos GeoJSON por `bbox` |
| `GET /v1/segments/{id}/satellite-observations` | Evidências persistidas do segmento |
| `POST /v1/analysis/preview` | Prévia não persistente do baseline |
| `GET /v1/recommendations` | Fila de recomendações |

Exemplo de consulta do eixo estimado:

```text
GET /v1/roads/SP021/segments?min_lon=-46.84&min_lat=-23.64&max_lon=-46.72&max_lat=-23.40
```

A resposta é GeoJSON EPSG:4326 e mantém os rótulos `estimated`,
`needs_validation` e `eligible_for_operations=false`. Consulte
[`docs/data-quality/km-axis-quality.md`](docs/data-quality/km-axis-quality.md).

No baseline, NDVI sozinho nunca se transforma em estimativa de altura. Dados de
baixa qualidade ou não reais retornam `inconclusive` e `inspect`. Altura real
acima do limite aplicável retorna `mowing_review`, que ainda exige decisão
humana.

### Autenticação e decisão humana

Crie um usuário local após a migração `0009`; nenhuma credencial padrão é
versionada:

```bash
zenit-user \
  --email manager@example.test \
  --display-name "Gestor local do MVP" \
  --road-code SP021 \
  --role manager
```

Obtenha um token de 30 minutos:

```text
POST /v1/auth/token
Content-Type: application/x-www-form-urlencoded

username=manager%40example.test&password=<senha-local>
```

Rotas centrais do fluxo gerencial:

| Método e rota | Finalidade |
| --- | --- |
| `GET /v1/auth/me` | Identidade e papéis do usuário |
| `POST /v1/recommendations/{id}/decisions` | Aceitar, rejeitar ou ajustar recomendação |
| `POST /v1/work-orders` | Criar ordem preparada de inspeção |
| `GET /v1/work-orders` | Listar ordens acessíveis ao ator |
| `GET /v1/photo-review-queue` | Fila autorizada de revisão de fotos |

Decisões rejeitadas ou ajustadas exigem justificativa. Ajustes também exigem
`adjusted_recommendation`. Nenhuma resposta autoriza trabalho de campo.

### Aplicativo móvel e sincronização

Registre o identificador lógico do aparelho antes da sincronização:

```text
POST /v1/mobile/devices
Authorization: Bearer <access-token>
Content-Type: application/json

{"device_id":"<device-uuid>","platform":"android","app_version":"1.0.0+1"}
```

`POST /v1/sync/batch` recebe lotes idempotentes e retorna `accepted`,
`rejected`, `conflicts` e `next_sync_cursor`. O aplicativo retém eventos locais
até obter resultado persistente. Conflitos preservam as duas versões.

O contrato aceita, em superfícies separadas:

- ciclo preparado de inspeção e três medições;
- manifestos de fotos de inspeção;
- ciclo de ensaio de roçada explicitamente simulado;
- três medições pós-serviço simuladas;
- manifestos separados das fotos pós-serviço.

Metadados de manifesto nunca provam que o servidor recebeu os bytes.

### Mídia de inspeção preparada

```text
POST /v1/media/{photo_id}
GET  /v1/media/{photo_id}
POST /v1/media/{photo_id}/reviews
```

O upload aceita JPEG/PNG de até 25 MiB, confere assinatura, tamanho, checksum,
ator, dispositivo e papel na rodovia. A API criptografa os bytes com
AES-256-GCM antes do MinIO privado e versionado. Recuperação e revisão repetem
as verificações de acesso e deixam trilha append-only.

Mesmo uma foto aceita permanece preparada e inelegível para operação,
treinamento ou relatório oficial.

### Resumo e proposta pós-inspeção

```text
POST /v1/work-orders/{work_order_id}/prepared-summary
GET  /v1/prepared-inspection-summaries
POST /v1/prepared-inspection-summaries/{summary_id}/exports
POST /v1/prepared-inspection-summaries/{summary_id}/post-inspection-proposal
POST /v1/prepared-post-inspection-proposals/{proposal_id}/decisions
```

O resumo exige ciclo finalizado, três medições e três revisões efetivamente
aceitas. Seus agregados vêm das medições digitadas, não das fotos. Uma violação
do limite produz `mowing_review`, nunca autorização de roçada.

O histórico de ensaio também informa, por ponto, se a foto pós-serviço simulada
aguarda revisão ou possui uma decisão visual registrada. Esse status não altera
as medições e não representa conclusão de roçada.

### Planejamento e ensaio de roçada

```text
POST /v1/prepared-mowing-orders
GET  /v1/prepared-mowing-orders
POST /v1/prepared-mowing-orders/{id}/resource-plans
POST /v1/prepared-mowing-orders/{id}/readiness-assessments
POST /v1/prepared-mowing-orders/{id}/planning-approvals
GET  /v1/prepared-mowing-rehearsals
POST /v1/mowing-media/{photo_id}
GET  /v1/mowing-media/{photo_id}
POST /v1/mowing-media/{photo_id}/reviews
GET  /v1/mowing-photo-review-queue
POST /v1/prepared-mowing-orders/{mowing_order_id}/post-service-summary
GET  /v1/prepared-mowing-post-service-summaries
POST /v1/prepared-mowing-post-service-summaries/{summary_id}/exports
POST /v1/prepared-mowing-post-service-summaries/{summary_id}/exceptions
GET  /v1/prepared-mowing-post-service-exceptions
POST /v1/prepared-mowing-post-service-exceptions/{exception_id}/decisions
```

Recursos são referências candidatas; clima e segurança são declarações manuais
preparadas; `approved_for_planning` não é aprovação operacional. O ensaio não
usa GPS real, não despacha equipe e não declara serviço concluído.

O upload pós-serviço só ocorre após aceitação dos três manifestos. O aplicativo
persiste cada recibo antes de avançar e retoma apenas fotos não confirmadas. A
resposta permanece `simulated`, `uploaded_unverified`, `not_validated`,
`not_collected` e inelegível para execução, treinamento e relatório oficial.
Na recuperação, a API revalida o papel atual na rodovia, descriptografa a
versão exata, confere tamanho/SHA-256 e registra o acesso antes da entrega.
A fila e as decisões humanas permanecem separadas da inspeção; uma aceitação
confirma apenas qualidade visual e régua visível, sem validar altura ou roçada.
O dashboard permite solicitar, consultar, revisar exceções humanas e exportar
CSV dos resumos pós-serviço simulados tanto em `/mowing-post-service-summaries`
quanto no contexto de `/photo-reviews`; essa agregação permanece simulada,
idempotente, auditada e não atualiza mapa, histórico operacional nem relatório
oficial.
Uma exceção pós-serviço simulada pode apontar necessidade de inspeção de
seguimento quando a máxima digitada ainda excede 10 cm em área especial ou
30 cm nas demais zonas; ela exige revisão humana e não autoriza campo. A decisão
humana da exceção é append-only, pode aceitar, rejeitar ou ajustar apenas para
`monitor`/`inspect_follow_up`, e continua inelegível para mapa, histórico
operacional, relatório oficial e treinamento de modelo.

### Prévia NDVI local

O recorte Sentinel-2 de 5 × 11 pixels pode ser consultado na
[prévia NDVI em cache](docs/previews/sentinel-ndvi-preview.html). Quando o cache
ignorado estiver disponível, regenere a página sem rede ou pacotes externos:

```bash
python scripts/render_cached_ndvi_preview.py
```

O renderizador verifica os checksums do GeoTIFF e dos metadados antes de gravar
a prévia e o manifesto de linhagem. Não há raster RGB de cor verdadeira em
cache.

## Desenvolvimento e validação

### API Python

```bash
source .venv/bin/activate
ruff check .
pytest
uvicorn zenit_api.main:app --app-dir services/api/src --reload
```

### Dashboard Next.js

Inicie a API e execute:

```bash
npm run dev --workspace @zenit/dashboard
```

Validação completa do dashboard:

```bash
npm run dashboard:lint
npm run dashboard:typecheck
npm run dashboard:test
npm run dashboard:build
```

O servidor do dashboard usa `INTERNAL_API_URL`, cujo padrão é
`http://localhost:8000`. O token bearer fica em cookie `HttpOnly` no servidor;
mutações exigem token CSRF, `Origin` exata e cookie `SameSite=Strict`.

### Aplicativo Flutter

No diretório `apps/mobile`:

```bash
../../.tools/flutter/bin/flutter --no-version-check --suppress-analytics pub get --enforce-lockfile
../../.tools/flutter/bin/dart format --output=none --set-exit-if-changed lib test
../../.tools/flutter/bin/flutter --no-version-check --suppress-analytics analyze
../../.tools/flutter/bin/flutter --no-version-check --suppress-analytics test
```

O emulador usa `http://10.0.2.2:8000` por padrão. Builds de produção devem
fornecer uma URL HTTPS:

```bash
../../.tools/flutter/bin/flutter run \
  --dart-define=ZENIT_API_BASE_URL=https://api.example.test \
  --dart-define=ZENIT_APP_VERSION=1.0.0+1
```

Tráfego HTTP sem TLS só é permitido pelo manifesto Android de depuração.

### Integração contínua

A CI valida Python, dashboard, Flutter e um ambiente Compose novo. O smoke test
confere schema PostGIS, healthcheck, resposta satelital vazia com proveniência,
proteção das rotas de escrita e disponibilidade do dashboard/login sem exigir
arquivos brutos ou credenciais de provedores.

## Segurança e limitações conhecidas

- A autenticação local do MVP não possui identidade corporativa, refresh token,
  recuperação de senha ou limitação de tentativas. Não deve ser exposta
  diretamente à internet.
- Staging e produção devem usar HTTPS, `DASHBOARD_COOKIE_SECURE=true` e
  `DASHBOARD_PUBLIC_ORIGIN` com a origem pública exata.
- A chave AES-256-GCM fica fora do object storage. Perder essa chave torna as
  mídias irrecuperáveis; custódia, rotação, backup e recuperação precisam ser
  definidos antes de um piloto.
- Ainda faltam política de retenção/legal hold, tratamento de EXIF, verificação
  por decoder/malware e controles completos de privacidade.
- Não há GPS real, despacho, rastreamento, execução de roçada ou aprovação
  operacional.
- O mapa e o histórico ainda não são atualizados com um resultado pós-roçada.
- Não existe relatório operacional oficial; os resumos atuais são preparados e
  simulados.
- A cena satelital completa e o eixo rodoviário oficial continuam pendentes.

## Documentação

- [Manual mestre do projeto](ZENIT_Manual_Mestre_para_Codex.pdf)
- [Decisões arquiteturais](docs/decisions)
- [Relatórios de qualidade dos dados](docs/data-quality)
- [Arquitetura](docs/architecture)
- [Aplicativo móvel](apps/mobile/README.md)
- [Regras para agentes de desenvolvimento](AGENTS.md)

O histórico detalhado de cada incremento deve permanecer nos ADRs. Este README
é a referência de entrada para executar o projeto, entender seus limites e
localizar os contratos atuais.
