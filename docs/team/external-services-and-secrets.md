# Serviços externos, credenciais e configurações

Este documento lista o que o ZENIT precisa para executar localmente, ativar
integrações opcionais e futuramente operar em staging/produção. Ele descreve
nomes e requisitos, nunca valores reais.

Data do inventário do código: **2026-09-12**.

## Resumo rápido

| Recurso | Local básico | Recurso opcional | Staging/produção |
| --- | --- | --- | --- |
| PostgreSQL/PostGIS | obrigatório; credencial local | — | credencial gerenciada + TLS/rede |
| MinIO/object storage | obrigatório para health/media | — | credencial gerenciada + HTTPS |
| segredo de autenticação | padrão somente local | — | segredo forte obrigatório |
| segredo da sessão fixa | necessário no demo Compose | — | sessão fixa deve ser desativada |
| chave de criptografia de mídia | padrão somente local | — | chave forte e custodiada obrigatória |
| Copernicus/Sentinel | não | obrigatório para `zenit-satellite` | conta técnica/rotação |
| INPE BDC/CBERS | não | token opcional | decidir conforme política do provedor |
| Planet | não | `PL_API_KEY` para catálogo | conta técnica, proxy/cache e controle de cota |
| mapa-base | OSM local sem chave | URL de outro provedor | serviço/SLA/licença aprovados |
| API do mobile | URL local | — | URL HTTPS e certificado válido |
| assinatura Android | debug automática | — | keystore/custódia obrigatórios |
| Git/GitHub | autenticação do colaborador | — | proteção de branch/CI aprovadas |

**Conclusão:** a stack demonstrativa local não exige API paga. Para baixar e
processar dados Sentinel ao vivo, exige credenciais OAuth do Copernicus Data
Space. Não existe chave do Google Maps no projeto atual.

## 1. Onde configurar

### Desenvolvimento local

```bash
cp -n .env.example .env
```

O `.env` é ignorado pelo Git. Não cole seu conteúdo em issue, PR, log, screenshot
ou conversa com IA. Não execute `source .env`: a URL de banco do Compose usa
hostname `postgres`, enquanto processos no host normalmente usam `localhost`.

### Compose

O `compose.yaml` lê variáveis do `.env` e encaminha somente as necessárias aos
containers. Confira a configuração resolvida sem publicar a saída, pois ela pode
conter segredos:

```bash
docker compose config --quiet
```

Evite `docker compose config` sem `--quiet` em logs compartilhados.

### Staging/produção

Use o secret manager da plataforma escolhida. Essa plataforma ainda não foi
definida. Segredos não devem entrar em imagem Docker, arquivo versionado,
`--dart-define` público, variável `NEXT_PUBLIC_*` ou URL entregue ao navegador.

## 2. Segredos internos obrigatórios

### `POSTGRES_PASSWORD` e `DATABASE_URL`

**Função:** autenticar PostgreSQL/PostGIS. A senha em `POSTGRES_PASSWORD` deve ser
a mesma usada no componente password de `DATABASE_URL`.

**Local:** os placeholders de `.env.example` funcionam apenas em máquina isolada.

**Produção:** senha aleatória exclusiva, rede restrita, TLS quando aplicável,
backups e rotação coordenada. A URL completa é segredo porque contém credencial.

Formatos usados pelo projeto:

```text
# dentro do Compose
postgresql+psycopg://<user>:<password>@postgres:5432/<database>

# processo Python executado no host
postgresql+psycopg://<user>:<password>@localhost:5432/<database>
```

Não percent-encode a senha manualmente sem validar a URL; caracteres reservados
precisam ser tratados pelo mecanismo de configuração escolhido.

### `AUTH_SECRET_KEY`

**Função:** assinar JWT HS256 e participar da proteção criptográfica relacionada
ao login. É somente do backend.

**Requisito do código:** em `staging` e `production`, deve ser diferente do
placeholder e ter pelo menos 32 caracteres.

**Geração candidata local/infra:**

```bash
openssl rand -hex 32
```

Guarde a saída diretamente no secret manager/.env local, sem publicá-la. Rotação
invalida tokens/artefatos criptográficos relacionados e precisa de plano de sessão.

### `AUTH_FIXED_SESSION_SECRET`

**Função:** autenticar o handshake servidor-servidor que cria as sessões fixas dos
dashboards demonstrativos. API e dashboard devem receber exatamente o mesmo valor.

**Requisito:** pelo menos 32 caracteres quando `AUTH_FIXED_SESSION_ENABLED=true`.

**Uso permitido:** `development`, `test` e `demo`. Em staging/produção:

```text
AUTH_FIXED_SESSION_ENABLED=false
```

Não configure identidades fixas em ambiente publicado. O segredo pode ser gerado
com `openssl rand -hex 32`, separado de `AUTH_SECRET_KEY`.

### `OBJECT_STORAGE_ACCESS_KEY` e `OBJECT_STORAGE_SECRET_KEY`

**Função:** autenticar API/MinIO no object storage privado. No Compose local também
se tornam usuário/senha root do MinIO.

**Produção:** não usar credencial root; criar identidade de serviço com menor
privilégio e acesso apenas aos buckets necessários. Endpoint deve usar HTTPS fora
de development/test/demo.

Variáveis relacionadas, não secretas por si:

- `OBJECT_STORAGE_ENDPOINT`;
- `OBJECT_STORAGE_BUCKET_MEDIA`.

`OBJECT_STORAGE_BUCKET_RAW` e `OBJECT_STORAGE_BUCKET_PROCESSED` aparecem hoje no
`.env.example`, mas não possuem consumidor runtime localizado neste inventário.
Não presuma que configurá-los ativa upload/ingestão desses buckets.

### `OBJECT_STORAGE_MEDIA_ENCRYPTION_KEY`

**Função:** criptografar mídia no servidor com AES-256-GCM antes de armazená-la.

**Requisito do código:** Base64 válido que decodifique para exatamente 32 bytes.

Geração:

```bash
openssl rand -base64 32
```

Essa é uma chave de dados, não uma senha comum. Perder a chave pode tornar as
mídias irrecuperáveis; substituí-la sem recriptografar torna objetos antigos
ilegíveis. Produção exige KMS/secret manager, backup seguro, controle de acesso,
versionamento e procedimento de rotação/recriptografia.

## 3. Credenciais de satélite

### `PL_API_KEY`

**Necessidade:** obrigatória somente para consultar APIs Planet. A fundação atual
usa a Data API para descobrir metadados `PSScene`; ela não cria Orders nem baixa
ativos.

**Origem:** página de configurações/desenvolvedor da conta Planet autorizada. Não
cole a chave em código, PR, issue, screenshot ou conversa. Configure localmente:

```text
PL_API_KEY=<planet-api-key>
```

**Proteção:** a chave fica no backend/worker e segue em header de autorização.
Ela nunca pode entrar em `NEXT_PUBLIC_*`, `MAP_TILE_URL`, aplicativo Flutter ou
URL entregue ao navegador. Tiles futuros precisam de proxy/cache autenticado no
backend com limites por usuário e registro de consumo.

**Produtos disponíveis informados para a conta:** basemap tiles e scene tiles
possuem cotas próprias; scene downloads possuem cota por área. A disponibilidade
exata de mosaicos, item types, assets e product bundles deve ser consultada pela
API/conta antes de cada fluxo, sem presumir que toda cena encontrada pode ser
baixada.

Comando de descoberta sem download:

```bash
zenit-planet-catalog \
  --bbox -46.80 -23.55 -46.76 -23.50 \
  --from-date 2026-08-01 \
  --to-date 2026-08-07
```

Esse comando não persiste cenas e não consome a cota de download. Não execute
contra a conta compartilhada sem combinar AOI e período com o grupo.

### `COPERNICUS_CLIENT_ID`

### `COPERNICUS_CLIENT_SECRET`

**Necessidade:** obrigatórias em conjunto somente para executar o pipeline Sentinel
ao vivo pelo comando `zenit-satellite`. Elas não são necessárias para:

- subir PostgreSQL, MinIO, API e dashboard;
- executar testes offline;
- abrir o mapa com polígonos já importados;
- usar o app móvel contra dados já persistidos.

**Origem:** cliente OAuth confidencial criado em uma conta autorizada do
Copernicus Data Space Ecosystem. O portal/processo exato deve ser confirmado no
momento da criação, pois regras externas podem mudar.

**Fluxo atual:** client credentials backend-only → token temporário → Catalog,
Statistical e Process APIs. O token temporário fica apenas em memória e não deve
ser salvo, logado nem entregue ao dashboard/mobile.

Configuração local:

```text
COPERNICUS_CLIENT_ID=<client-id>
COPERNICUS_CLIENT_SECRET=<client-secret>
```

Antes da chamada ao provedor, o banco precisa conter a AOI preparada e não
operacional. O comando também depende de rede:

```bash
zenit-satellite --segment-index 195 --zone left \
  --from-date 2026-07-01 --to-date 2026-08-07
```

Não use datas desse exemplo como “estado atual”. O resultado permanece
inconclusivo/preparado conforme as regras atuais.

### `BDC_ACCESS_TOKEN`

**Necessidade:** opcional para o cliente de catálogo CBERS/INPE BDC. O STAC público
pode ser consultado sem token no desenho atual; quando configurado, o token é
enviado como bearer pelo backend.

**Estado atual:** a variável existe em `Settings` e o cliente CBERS aceita token,
mas o CLI `zenit-satellite` atual executa o fluxo Sentinel. Não trate o simples
preenchimento da variável como ativação de um pipeline CBERS completo.

**Origem:** conta/token autorizado pelo INPE BDC, caso o provedor passe a exigir ou
o projeto aprove uso autenticado. Confirmar termos e procedimento no momento do
uso.

## 4. Mapa-base

### `MAP_TILE_URL`

**Função:** template de tiles usado pelo MapLibre no dashboard.

**Atual:** `https://tile.openstreetmap.org/{z}/{x}/{y}.png`, sem chave, apenas para
demonstração acadêmica local e baixo volume conforme ADR-0066. É necessário
respeitar atribuição e política do serviço.

**Importante:**

- Google Maps não está integrado e nenhuma Google Maps API key é necessária;
- MapLibre é a biblioteca de renderização, não um provedor de tiles;
- a base OSM comunitária não oferece SLA de produção;
- um provedor comercial pode exigir token, domínio permitido, cota e pagamento;
- uma chave colocada diretamente em `MAP_TILE_URL` será visível no navegador.

Se o provedor escolhido exigir segredo real, criar ADR e um proxy/token efêmero
apropriado. Não esconder chave permanente em JavaScript. Para produção, decidir
provedor/self-hosting, licença, atribuição, cache, cota, offline e indisponibilidade.

## 5. Dashboard: configurações, não chaves de API

| Variável | Função | Segredo? |
| --- | --- | --- |
| `INTERNAL_API_URL` | URL server-side da API | não, mas é topologia interna |
| `DASHBOARD_APP_ENV` | ambiente | não |
| `DASHBOARD_PUBLIC_ORIGIN` | origem exata do dashboard | não |
| `DASHBOARD_SUPERVISOR_PUBLIC_ORIGIN` | origem da instância supervisor | não |
| `DASHBOARD_COOKIE_SECURE` | exige cookie Secure | não |
| `DASHBOARD_MANAGER_EMAIL` | identidade demo fixa | dado de configuração |
| `DASHBOARD_SUPERVISOR_EMAIL` | identidade demo fixa | dado de configuração |
| `DASHBOARD_FIXED_USER_EMAIL` | e-mail encaminhado a cada container | dado de configuração |
| `DASHBOARD_FIXED_HOME_PATH` | rota inicial demo | não |
| `DASHBOARD_SESSION_COOKIE_NAME` | nome do cookie | não |
| `DASHBOARD_CSRF_COOKIE_NAME` | nome do cookie CSRF | não |
| `DASHBOARD_FIXED_SESSION_SECRET` | espelho do segredo fixo | **sim** |

Em staging/produção, `DASHBOARD_PUBLIC_ORIGIN` deve ser HTTPS e
`DASHBOARD_COOKIE_SECURE=true`. Tokens bearer e CSRF são criados em runtime; não
são valores para preencher em `.env`.

## 6. Aplicativo móvel

Configurações de build:

```text
ZENIT_API_BASE_URL=<URL da API>
ZENIT_APP_VERSION=<versão+build>
```

São passadas com `--dart-define`. A URL não é segredo e pode ser extraída do APK.
Produção exige HTTPS e certificado válido. Não passe token, senha, chave de
provedor, segredo de banco ou chave de mídia por `--dart-define`.

Credenciais do usuário:

- senha é digitada e nunca persistida;
- access token é emitido pela API e armazenado no Android secure storage;
- chave do cofre móvel é gerada no dispositivo e protegida pelo secure storage;
- nenhuma delas deve ser pré-configurada no repositório.

### Assinatura Android futura

O build debug usa assinatura debug. Uma distribuição operacional ainda exigirá:

- keystore de release;
- alias;
- senha do keystore;
- senha da chave;
- política de custódia/backup/rotação e responsáveis;
- configuração segura do pipeline de build/distribuição.

Esses itens não estão configurados ou versionados. Nunca commitar `.jks`, `.keystore`,
`key.properties` ou senhas.

## 7. Identidades locais

Os usuários `manager` e `supervisor` não são API keys. Eles são criados pela CLI
`zenit-user`, que solicita uma senha de no mínimo 12 caracteres sem ecoá-la. As
contas precisam existir antes da sessão fixa demonstrativa.

Staging/produção ainda necessitam de decisão sobre IdP, MFA, recuperação de conta,
recertificação de papéis e contas de serviço. Não existe hoje chave de Google,
Microsoft, Auth0 ou outro IdP configurada.

## 8. GitHub e colaboração

Para clone/fetch/push, cada colaborador precisa autenticar-se no GitHub usando sua
própria chave SSH ou credencial suportada pelo provedor. Isso não é configuração
runtime do ZENIT e não deve ser compartilhado entre pessoas/IAs.

CI usa recursos padrão do GitHub e não referencia secrets customizados no workflow
atual. Deploy futuro pode exigir credencial de registry/cloud; ainda não foi
escolhido. Recomenda-se proteger `main`, exigir PR/review e bloquear force-push.

## 9. Configurações não secretas consumidas

Elas não são chaves, mas precisam estar coerentes por ambiente:

| Variável | Uso/restrição |
| --- | --- |
| `APP_ENV` | `development`, `test`, `demo`, `staging` ou `production` |
| `APP_NAME` / `APP_VERSION` | identidade e versão reportada da API |
| `HEALTH_PROBE_TIMEOUT_SECONDS` | timeout entre 0,1 e 10 s |
| `POSTGRES_DB` / `POSTGRES_USER` | criação/conexão local do PostgreSQL |
| `AUTH_ACCESS_TOKEN_MINUTES` | validade entre 5 e 1440 min |
| `AUTH_TOKEN_ISSUER` / `AUTH_TOKEN_AUDIENCE` | emissão e validação do JWT |
| `AUTH_LOGIN_ATTEMPT_LIMIT` | limite configurável entre 2 e 20 |
| `AUTH_LOGIN_WINDOW_SECONDS` | janela de contabilização entre 60 e 86400 s |
| `AUTH_LOGIN_BLOCK_SECONDS` | duração do bloqueio entre 60 e 86400 s |
| `AUTH_LOGIN_THROTTLE_POLICY_VERSION` | versão auditável da política de login |
| `AUTH_FIXED_SESSION_ENABLED` | somente development/test/demo; `false` fora deles |
| `OBJECT_STORAGE_BUCKET_MEDIA` | bucket privado de mídia, nome compatível com S3 |
| `DASHBOARD_APP_ENV` | ambiente quando dashboard roda fora do Compose |
| `DASHBOARD_PUBLIC_ORIGIN` | origem exata, sem path/query/credencial |
| `DASHBOARD_SUPERVISOR_PUBLIC_ORIGIN` | origem da segunda instância demo |
| `DASHBOARD_COOKIE_SECURE` | obrigatório `true` com HTTPS em staging/produção |
| `DASHBOARD_MANAGER_EMAIL` / `DASHBOARD_SUPERVISOR_EMAIL` | usuários fixos locais existentes |

As versões abaixo entram nos artefatos/auditoria e não devem ser mudadas apenas
para “limpar” a configuração. Alterar comportamento exige ADR/testes e nova versão:

- `RECOMMENDATION_REVIEW_POLICY_VERSION`;
- `INSPECTION_ORDER_POLICY_VERSION`;
- `PREPARED_PHOTO_REVIEW_POLICY_VERSION`;
- `PREPARED_INSPECTION_SUMMARY_POLICY_VERSION`;
- `PREPARED_POST_INSPECTION_POLICY_VERSION`;
- `PREPARED_MOWING_ORDER_POLICY_VERSION`;
- `PREPARED_MOWING_RESOURCE_POLICY_VERSION`;
- `PREPARED_MOWING_READINESS_POLICY_VERSION`;
- `PREPARED_MOWING_APPROVAL_POLICY_VERSION`;
- `PREPARED_MOWING_PHOTO_REVIEW_POLICY_VERSION`;
- `PREPARED_MOWING_POST_SERVICE_SUMMARY_POLICY_VERSION`;
- `PREPARED_MOWING_POST_SERVICE_EXCEPTION_POLICY_VERSION`.

## 10. Itens presentes no `.env.example` mas ainda sem efeito runtime localizado

No inventário atual, estas variáveis aparecem como intenção/guardrail, mas não são
consumidas por código executável localizado:

- `OBJECT_STORAGE_BUCKET_RAW`;
- `OBJECT_STORAGE_BUCKET_PROCESSED`;
- `DEFAULT_TIMEZONE`;
- `DEFAULT_GENERAL_THRESHOLD_CM`;
- `DEFAULT_SPECIAL_THRESHOLD_CM`;
- `ALLOW_SIMULATED_LOCATION`;
- `ALLOW_DEMO_RESET`;
- `TRAINING_DATA_ENABLED`;
- `OFFICIAL_REPORTS_ENABLED`.

Os thresholds de 30/10 cm continuam sendo regra do domínio, mas configurar essas
duas variáveis não altera o comportamento atual. Do mesmo modo, manter flags de
treino/relatório em `false` comunica a intenção, mas não substitui controles de
elegibilidade existentes. Qualquer ativação futura exige implementação, ADR e teste.

## 11. Serviços que o projeto não usa hoje

Não solicitar nem comprar chaves para estes serviços sem um ticket/ADR aprovado:

- Google Maps/Google Cloud;
- Mapbox ou outro provedor comercial de tiles;
- OpenAI, Anthropic ou outra IA hospedada;
- Firebase, Crashlytics ou push notifications;
- Sentry, Datadog, New Relic ou plataforma de observabilidade;
- API de clima;
- SMTP, e-mail, SMS ou WhatsApp;
- fila/broker como RabbitMQ, Kafka ou Redis;
- cloud AWS/Azure/GCP e container registry externo;
- IdP corporativo;
- distribuição mobile/MDM/loja.

Esses recursos podem aparecer no roadmap como necessidades futuras, mas não há
integração ativa nem formato de segredo definido.

## 12. Material não secreto que também é necessário

Dependendo da jornada:

- documentos fonte locais em `data/raw/`, imutáveis e fora do Git;
- eixo/zonas oficiais homologados para operação;
- usuários e papéis;
- Docker images do Compose e acesso de rede para baixá-las na primeira execução;
- acesso à internet para tiles e APIs satelitais;
- Flutter/Android SDK para mobile;
- dispositivo/emulador e câmera/GPS para futuro piloto;
- domínio, DNS e certificados TLS em staging/produção;
- política de privacidade, retenção, backup e resposta a incidente;
- dataset real, licenciado e validado antes de treinar modelos.

## 13. Checklist por ambiente

### Local sem satélite

- `.env` copiado;
- placeholders restritos à máquina local;
- PostgreSQL/MinIO acessíveis;
- segredos locais não commitados;
- nenhuma credencial externa necessária.

### Local com Sentinel

- tudo do local básico;
- `COPERNICUS_CLIENT_ID` e `COPERNICUS_CLIENT_SECRET`;
- rede para os endpoints do provedor;
- AOI preparada no banco;
- resultado rotulado como preparado/inconclusivo quando aplicável.

### Staging/produção futura

- secret manager/KMS escolhido;
- segredos fortes e exclusivos por ambiente;
- fixed session desativada;
- banco/object storage com TLS e menor privilégio;
- chave de mídia custodiada e recuperável;
- HTTPS, DNS e cookies secure;
- basemap/provedor com licença/SLA;
- assinatura Android se houver distribuição;
- rotação, auditoria, backup/restauração e resposta a incidente;
- nenhuma chave exposta ao browser/app/CI log.

## 14. Como uma IA deve lidar com segredos

- pode listar **nomes** de variáveis e requisitos;
- pode verificar se a variável está definida sem imprimir o valor;
- nunca deve executar `cat .env`, `env`, `printenv` amplo ou `docker compose config`
  em saída compartilhada;
- nunca deve copiar token/secret para teste, fixture, comentário ou prompt;
- deve usar placeholders em documentação;
- deve revisar `git diff --cached` antes do commit;
- se um segredo aparecer no Git, deve parar, não repetir o valor e pedir rotação;
- remover do último commit não basta se o segredo já foi enviado: o proprietário
  precisa revogá-lo/rotacioná-lo e tratar o histórico com autorização específica.
