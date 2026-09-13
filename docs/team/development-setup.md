# Configuração completa do ambiente de desenvolvimento

Este guia cobre ambiente limpo, stack inteira, execução por componente, dados
locais e diagnóstico. Use credenciais exclusivamente locais. Não copie segredos
reais para comandos, commits, screenshots ou conversas de IA.

Para o inventário completo de chaves, serviços externos, formatos e requisitos
por ambiente, leia
[`external-services-and-secrets.md`](external-services-and-secrets.md).

## 1. Versões suportadas

| Ferramenta | Versão/base |
| --- | --- |
| Git | atual com suporte a worktree |
| Python | 3.12–3.14; CI usa 3.12 |
| Node.js | 22+ |
| npm | versão compatível com Node 22 e lockfile |
| Docker Engine + Compose v2 | necessário para stack integrada |
| Flutter | 3.44.9 na baseline atual |
| Android | min SDK 24, target SDK 36; JDK/SDK compatíveis com o projeto |

Flutter/Android são necessários somente para o app. O diretório local `.tools/`
não deve ser assumido em todas as máquinas; cada pessoa pode usar SDK no `PATH`.
Não atualize SDK/lockfiles incidentalmente.

## 2. Clone e leitura inicial

```bash
git clone <URL_DO_REPOSITORIO> zenit
cd zenit
git status --short --branch
```

Leia `AGENTS.md`, o Manual Mestre, o README e `docs/team/README.md`. Confirme que
não há alteração local antes de criar a sua branch:

```bash
git switch main
git pull --ff-only
git switch -c feature/<ticket>-<slug>
```

Use `fix/<ticket>-<slug>` para correções e `docs/<ticket>-<slug>` para mudanças
exclusivamente documentais.

Se o grupo usar worktrees, crie um diretório irmão com uma branch exclusiva. Não
compartilhe a mesma working tree entre duas IAs.

Depois desse ponto, não trabalhe nem envie commits diretamente em `main`. Siga o
fluxo completo de validação, push da branch e pull request em
[`git-collaboration-workflow.md`](git-collaboration-workflow.md).

## 3. Configuração de ambiente

```bash
cp -n .env.example .env
```

Edite `.env` localmente. O arquivo não deve ser commitado. Valores
`development-only`/`change_me` só servem em uma máquina isolada. Para qualquer
ambiente compartilhado, gere segredos separados e configure-os fora do Git.

Não faça `source .env`: `DATABASE_URL` do Compose usa hostname `postgres`, enquanto
processos executados no host precisam de `localhost`.

## 4. Dependências Python

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
ruff check .
python scripts/export_openapi.py --check
```

Se `python3.12` não existir, use uma versão instalada entre 3.12 e 3.14 e confirme
`python --version`. Não altere a restrição do projeto para contornar ambiente local.

## 5. Dependências web

Na raiz:

```bash
node --version
npm --version
npm install
npm run dashboard:typecheck
```

`npm install` deve respeitar o lockfile. Uma alteração inesperada em
`package-lock.json` precisa ser revisada; não a inclua em ticket visual sem causa.

## 6. Stack inteira via Docker Compose

```bash
docker compose config --quiet
docker compose up --build -d
docker compose ps
curl --fail http://localhost:8000/health
curl --fail http://localhost:3000/api/health
```

Endereços:

| Serviço | URL/porta |
| --- | --- |
| Dashboard gerente | `http://localhost:3000` |
| Dashboard supervisor | `http://localhost:3002` |
| API/Swagger | `http://localhost:8000` / `/docs` |
| PostgreSQL/PostGIS | `localhost:5432` |
| MinIO API/console | `localhost:9000` / `http://localhost:9001` |

Para acompanhar:

```bash
docker compose logs --tail=200 api dashboard dashboard-supervisor
```

Pare sem excluir dados:

```bash
docker compose stop
```

`docker compose down -v` apaga volumes locais. Só use com autorização explícita e
depois de confirmar o nome do projeto/volumes; a operação não é necessária para
parar ou reconstruir containers.

### Docker rootless opcional

Este checkout pode conter ferramentas locais ignoradas. Se a equipe adotá-las:

```bash
export PATH="$PWD/.tools/docker/bin:$PATH"
export DOCKER_HOST="unix:///run/user/$(id -u)/docker.sock"
docker info
```

Não commit `.tools` nem dependa dele em scripts portáveis.

## 7. Banco e migrações

Em volume novo, o Compose aplica os arquivos forward montados em ordem. Em volume
existente, `/docker-entrypoint-initdb.d` não roda novamente.

Confira a migração mais recente no repositório e o schema antes de aplicar algo.
Para banco vazio fora do init automático:

```bash
for migration in infra/migrations/[0-9][0-9][0-9][0-9]_*.sql; do
  case "$migration" in *.down.sql) continue ;; esac
  docker compose exec -T postgres \
    psql -v ON_ERROR_STOP=1 -U zenit -d zenit < "$migration"
done
```

Não reaplique migrações indiscriminadamente em banco compartilhado. Uma nova
migração deve ter número exclusivo, transação/testes e down quando a política
vigente exigir.

## 8. Três níveis de dados locais

### A. Smoke vazio

É suficiente para CI, healthchecks, autenticação negativa e renderização básica.
Não precisa dos documentos brutos nem de provedor satelital.

### B. Desenvolvimento com fontes locais

Coloque os arquivos fornecidos sob `data/raw/` sem renomear/substituir e nunca os
commite. Consulte `data/README.md`. Com a infraestrutura ativa:

```bash
source .venv/bin/activate
export DATABASE_URL='postgresql+psycopg://zenit:change_me@localhost:5432/zenit'
zenit-import km-markers 'data/raw/01. Rodovia Motiva - Rodoanel/Marco km_rodoanel 2.kmz'
zenit-import mowing-polygons 'data/raw/01. Rodovia Motiva - Rodoanel/classificacao_rocada.kmz'
zenit-import vegetation-workbook 'data/raw/02. Dados Gestão verde - Atual/Retigrafico/RA-RET-ROÇ-LIMP-2026-03-13.xlsx'
```

O importador só cria staging e linhagem; não promove automaticamente. Confirme
status/anomalias. Os caminhos exatos podem diferir conforme o pacote entregue.

### C. Eixo candidato demonstrativo

Somente para desenvolvimento, depois de importar marcos:

```bash
docker compose exec -T postgres \
  psql -v ON_ERROR_STOP=1 -U zenit -d zenit < scripts/sql/build_estimated_axis.sql
```

O resultado continua `estimated`, `needs_validation` e inelegível. Não use o script
em ambiente operacional nem chame o eixo de oficial.

## 9. Usuários e login local

A sessão fixa por porta não cria usuários. Após existir a rodovia `SP021`, crie os
e-mails configurados no `.env`; a CLI pede senha sem imprimi-la:

```bash
source .venv/bin/activate
export DATABASE_URL='postgresql+psycopg://zenit:change_me@localhost:5432/zenit'
zenit-user --email manager@example.com --display-name 'Manager local' \
  --road-code SP021 --role manager
zenit-user --email supervisor@example.com --display-name 'Supervisor local' \
  --road-code SP021 --role supervisor
```

Use senha local de no mínimo 12 caracteres. Os dashboards em 3000/3002 usam essas
identidades fixas apenas em development/demo. Nunca publique essas portas. Para
testar login por senha, desative conscientemente a sessão fixa e alinhe variáveis
do dashboard/API; consulte os ADRs de autenticação antes de alterar o Compose.

O script `scripts/seed_demo_orders.py` cria dados **simulados/preparados** e exige
SP021, segmentos e `manager@example.com`. Execute apenas quando esse tipo de demo
for necessário:

```bash
source .venv/bin/activate
export DATABASE_URL='postgresql+psycopg://zenit:change_me@localhost:5432/zenit'
python scripts/seed_demo_orders.py
```

## 10. Execução por componente

### Infraestrutura + API local

```bash
docker compose up -d postgres minio
source .venv/bin/activate
export DATABASE_URL='postgresql+psycopg://zenit:change_me@localhost:5432/zenit'
export OBJECT_STORAGE_ENDPOINT='http://localhost:9000'
uvicorn zenit_api.main:app --app-dir services/api/src --reload
```

As demais configurações podem vir de `.env` por mecanismo da aplicação. Confirme
que endpoints usam hosts acessíveis pelo processo local.

### Dashboard local

Com API em `localhost:8000`:

```bash
export INTERNAL_API_URL='http://localhost:8000'
npm run dev --workspace @zenit/dashboard
```

Tiles OSM dependem de rede. Falha de mapa-base não deve ser confundida com falha
da API GeoJSON; inspecione Network e a lista alternativa da tela.

### Flutter/Android

Com Flutter no `PATH`:

```bash
cd apps/mobile
flutter --version
flutter doctor -v
flutter pub get --enforce-lockfile
flutter analyze
flutter test
flutter devices
flutter run \
  --dart-define=ZENIT_API_BASE_URL=http://10.0.2.2:8000 \
  --dart-define=ZENIT_APP_VERSION=1.0.0+1
```

Se o SDK local oficial estiver em `.tools/flutter`, substitua `flutter` por
`../../.tools/flutter/bin/flutter` e `dart` por `../../.tools/flutter/bin/dart`.
Emulador Android usa `10.0.2.2` para alcançar o host; dispositivo físico precisa
de endereço alcançável na rede de desenvolvimento. HTTP é somente debug.

## 11. Gates antes de commit

### Python/API/geo

```bash
source .venv/bin/activate
ruff check .
pytest
python scripts/export_openapi.py --check
```

### Dashboard

```bash
npm run dashboard:lint
npm run dashboard:typecheck
npm run dashboard:test
npm run dashboard:build
```

### Mobile

```bash
cd apps/mobile
dart format --output=none --set-exit-if-changed lib test
flutter analyze
flutter test
flutter build apk --debug --dart-define=ZENIT_API_BASE_URL=https://api.example.invalid
```

### Stack

```bash
python scripts/verify_mvp_stack.py
docker compose ps
```

Execute os gates proporcionais aos arquivos afetados. Mudanças em contrato ou
infra exigem consumidores e smoke, não apenas unitários.

## 12. Diagnóstico rápido

| Sintoma | Verificação |
| --- | --- |
| login fixo falha | usuários existem com os mesmos e-mails do `.env`; API e secrets de sessão coincidem |
| `road SP021 does not exist` | importação + eixo candidato demonstrativo ainda não foram executados |
| API local não conecta ao DB | URL do host deve usar `localhost`, não hostname `postgres` |
| mapa vazio | verificar API GeoJSON, bbox, dados importados e só depois tiles |
| mapa sem base | rede/`MAP_TILE_URL`/atribuição; lista deve continuar útil |
| migração nova não apareceu | volume existente não reaplica init scripts |
| mobile não alcança API | emulador usa `10.0.2.2`; device precisa de host alcançável |
| lockfile mudou | versão de ferramenta ou comando incorreto; revisar antes de incluir |
| porta ocupada | identificar processo/container; não matar serviço alheio automaticamente |

Ao pedir ajuda a uma IA, forneça comando, exit code, trecho mínimo do erro, sistema,
versões e `git status`; remova tokens, senhas, cookies e dados pessoais.
