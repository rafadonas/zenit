# Recovered GOV-001 visual corridor

## Source and scope

The local visual inventory on 2026-09-14 used a temporary in-memory mock API,
not imported KMZ files or persisted road geometry. The original mock creation
code was recovered from that task's local history on 2026-09-16. Its UTF-8
SHA-256 is `071e717dfb0ae6e1fee6f7d6aba1fe013c6e314f01b9839d7da0706cfb4ea262`.
The task history itself is not committed.

`apps/dashboard/src/lib/corridor-demo.ts` preserves the original eight line
features, four polygon features, identifiers, coordinate formulas, class examples,
and fictitious distance ranges. Segment status is corrected from the old mock's
`estimated` to `simulated`. The complete fixture has explicit simulation
provenance and false operational, training, and official-report eligibility.

The legacy vegetation rendering contract still names its status `historical`;
this is a mock of that contract, not historical evidence. Both collections carry
`is_simulated=true`, and the demo screen, list, legend, details, and popups label
the data simulated. The reference date `2025-03-28` is retained as fixture
metadata only, not as proof of an observation. No KMZ origin is claimed.

Coordinates do not follow the real road and the nominal 100 m ranges do not
measure the drawn lines. The UI identifies those distances as fictitious. This
fixture has no four-zone analysis, satellite observation, height measurement,
recommendation, field authorization, export, or official-report use.

## Local use

With the normal Compose stack running, open:

`http://localhost:3000/corridor?demo=gov-001`

The empty live corridor also offers an explicit link to this demonstration.
The mode is available only when `DASHBOARD_APP_ENV` (or, if absent, `NODE_ENV`)
is `development`, `test`, or `demo`. Staging, production, and unspecified
environments do not activate it. Existing authentication remains in place.

The page renders local fixtures directly; no mock API, provider credential,
database seed, or new dependency is needed. Base tiles still come from the
configured map provider, with the existing equivalent list when tiles fail.
Selection, search, and class filtering remain available. Selecting a mock
segment does not request satellite evidence from the real API.

Removing `demo=gov-001`, or using the return link, restores the live API view.
There is no automatic demo fallback for missing data or API errors. Nothing is
written into `data/raw`, the database, training datasets, or object storage.

After changing source code, rebuild the dashboards:

```bash
docker compose up --build -d
```

Once built, the regular `docker compose up -d` starts the same version.

## Map worker packaging

The restored fixture exposed a missing MapLibre v6 module worker: raster tiles
loaded, but GeoJSON features never rendered. Following the
[MapLibre Next.js setup](https://maplibre.org/maplibre-gl-js/docs/#installation),
`predev` and `prebuild` copy the installed worker and its shared module into
`public/maplibre`, along with their license. The map sets the same-origin worker
URL before construction. The Docker runtime includes `public`, and the session
proxy excludes this generated static asset directory. Dependency versions and
authentication on application pages and APIs are unchanged.

The generated assets are ignored by Git and ESLint; they are regenerated from
the installed, locked dependency. No CDN or additional dependency is introduced.
