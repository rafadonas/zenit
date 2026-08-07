# ZENIT

ZENIT is a road-vegetation monitoring platform designed to connect geospatial
and satellite data with explainable recommendations, human approval, field
execution, and auditable operational reporting.

## Current status

Sprints 0–2 are implemented: the local stack and health API, auditable source
ingestion into PostGIS, a marker-derived candidate axis split into 100 m
segments, a bbox GeoJSON endpoint, and a read-only dashboard map. The candidate
axis remains `estimated`, `needs_validation`, and blocked from operational use.

## Planned architecture

- `apps/dashboard`: Next.js management dashboard
- `apps/mobile`: offline-first Flutter Android application
- `services/api`: FastAPI application and domain use cases
- `services/geospatial-worker`: geospatial and satellite processing
- `services/ai-worker`: explainable rules and future model candidates
- `packages/contracts`: shared API and event contracts
- `infra`: Docker and database migrations
- `data`: local raw inputs, manifests, and generated products
- `docs`: architecture, decisions, and data-quality reports

## Data preparation

Place the supplied project inputs in `data/raw/`. Raw inputs are local,
immutable evidence and must not be committed. See `data/README.md` for the
expected files and handling rules.

## Development sequence

1. Audit supplied source files and record checksums and anomalies.
2. Implement versioned, idempotent ingestion.
3. Build the PostGIS domain model and 100 m segmentation.
4. Add the cached satellite pipeline and explainable baseline.
5. Close the recommendation, approval, offline field, and reporting loop.

## API development

Python 3.12 or newer is required. From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
ruff check .
pytest
uvicorn zenit_api.main:app --app-dir services/api/src --reload
```

Copy `.env.example` to `.env` before changing local configuration. Placeholder
passwords in `.env.example` are development defaults, never production secrets.

## Containers

With Docker and Docker Compose installed:

```bash
docker compose up --build
```

The API health endpoint is available at `http://localhost:8000/health`, PostGIS
at port `5432`, and the MinIO console at `http://localhost:9001`.

This workstation uses Docker Engine rootless. The project-local binaries are
ignored by Git. In a new shell, select them with:

```bash
export PATH="$PWD/.tools/docker/bin:$PATH"
export DOCKER_HOST="unix:///run/user/$(id -u)/docker.sock"
```

PostGIS, MinIO, and the API have been built and validated as healthy. Flutter is
not installed yet because the mobile application is outside the current Sprint 1
ingestion scope.

## Database migrations and ingestion

Apply migrations in numeric order before importing sources. The current local
database already has migrations `0001`, `0002`, and `0003` applied.

```bash
docker-compose exec -T postgres psql -v ON_ERROR_STOP=1 -U zenit -d zenit \
  < infra/migrations/0001_source_catalog_and_staging.sql
docker-compose exec -T postgres psql -v ON_ERROR_STOP=1 -U zenit -d zenit \
  < infra/migrations/0002_allow_invalid_staging_polygons.sql
docker-compose exec -T postgres psql -v ON_ERROR_STOP=1 -U zenit -d zenit \
  < infra/migrations/0003_road_axis_candidates_and_segments.sql
```

Use `zenit-import` for one immutable raw file at a time. Full examples are in
`docs/architecture/source-ingestion.md`.

## Segment GeoJSON API

The current estimated axis is queryable by bounding box:

```text
GET /v1/roads/SP021/segments?min_lon=-46.84&min_lat=-23.64&max_lon=-46.72&max_lat=-23.40
```

The response is GeoJSON in EPSG:4326. Segment properties explicitly report
`estimated`, `needs_validation`, and `eligible_for_operations=false`; see
`docs/data-quality/km-axis-quality.md` before using this dataset.

## Dashboard development

The Sprint 2 dashboard renders the candidate SP-021 axis as selectable 100 m
segments and keeps the data-quality and operational-use warnings visible. It
does not substitute simulated data when the API is unavailable.

Install the declared workspace dependencies and start the API before running the
dashboard:

```bash
npm install
npm run dev --workspace @zenit/dashboard
```

The server-side dashboard request uses `INTERNAL_API_URL` and defaults to
`http://localhost:8000`. Validate it from the repository root with:

```bash
npm run dashboard:lint
npm run dashboard:typecheck
npm run dashboard:test
npm run dashboard:build
```
