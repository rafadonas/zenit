# ZENIT MVP readiness

- Assessment date: 2026-08-14
- Target: P0 evaluation demonstration
- Demonstration decision: GO
- Operational or field-pilot decision: NO-GO

## Scope boundary

The repository is ready to demonstrate the complete prepared flow from source
catalog and segment analysis through human decisions, offline mobile capture,
simulated mowing rehearsal, post-service review, summary, exception assessment,
and audited export.

This decision does not certify field execution or production readiness. The
available road axis is estimated, the cached satellite artifact is partial, and
all inspection and mowing returns are prepared or simulated. They remain
ineligible for model training, official reporting, map/history promotion, and
field authorization.

## P0 acceptance matrix

| Capability | Demonstration status | Evidence and boundary |
| --- | --- | --- |
| Reproducible foundation | Ready | Compose defines healthy PostgreSQL/PostGIS, MinIO, API, and dashboard services. A fresh database applies migrations `0001`-`0037`. |
| Source audit and ingestion | Ready | Immutable source catalog, checksums, lineage, idempotent imports, and deterministic parser fixtures are covered by tests and data-quality reports. |
| Segments, zones, and map | Ready with estimated data | The dashboard exposes 100 m segments and separate zones. The candidate axis remains `estimated`, `needs_validation`, and non-operational. |
| Satellite baseline | Ready with partial cache | Discovery, quality gates, explainable rules, provenance, and a checksum-bound NDVI preview exist. No complete source scene is approved for operations. |
| Human decision and inspection order | Ready | Recommendation review is append-only and every prepared order remains linked to its analysis, policy, actor, and effective human decision. |
| Offline inspection demonstration | Ready | Flutter stores encrypted drafts, three measurements, photos, lifecycle events, and idempotent retries while visibly preserving simulated location. |
| Prepared inspection return | Ready | Human photo review gates immutable summaries and audited CSV exports without treating pixels as height. |
| Mowing planning and rehearsal | Ready for demonstration | Proposal, human review, non-executable order, candidate resources, manual readiness, planning-only approval, and offline rehearsal are separated and audited. |
| Post-service feedback | Ready for demonstration | Three separate simulated heights and photos gate a summary, audited export, threshold exception, and append-only human exception review. |
| History and reporting | Ready only in demonstration scope | Read-only rehearsal history and simulated CSV artifacts are available. Operational map/history updates and official reports are intentionally blocked. |
| Dashboard accessibility | Ready as automated baseline | All current main shells expose a skip target; keyboard focus, reduced motion, JSX semantics, and primary muted-text contrast are gated. Manual browser and assistive-technology audits remain required before operational use. |
| Automated quality gates | Ready | Python, dashboard, Flutter, production dashboard build, versioned OpenAPI contract, migration contract, and fresh-database smoke checks pass locally and are represented in CI. |

## Validation record

The local release audit ran these tracked checks successfully:

```text
.venv/bin/ruff check .
.venv/bin/pytest
python scripts/export_openapi.py --check
npm run dashboard:lint
npm run dashboard:test
npm run dashboard:build
flutter analyze
flutter test
flutter build apk --debug --dart-define=ZENIT_API_BASE_URL=https://api.example.invalid
python scripts/verify_android_apk.py \
  apps/mobile/build/app/outputs/flutter-apk/app-debug.apk \
  --expected-application-id br.com.zenit.zenit_mobile \
  --expected-version-name 1.0.0 --expected-version-code 1 \
  --expected-min-sdk 24 --expected-target-sdk 36 \
  --configured-api-base-url https://api.example.invalid
python scripts/verify_release_evidence.py \
  docs/release-evidence/android-mvp-debug-apk-2026-08-14.json \
  --artifact apps/mobile/build/app/outputs/flutter-apk/app-debug.apk
docker compose config --quiet
fresh PostgreSQL initialization with migrations 0001-0037
python scripts/verify_mvp_stack.py
```

The fresh-database check verified the final summary export, exception, exception
review tables, and the versioned exception policy. Its isolated container,
network, and volume were removed after validation; the development stack was
not modified. The tracked smoke verifier is shared with CI and covers 25 HTTP
contracts from public health and collection responses through the final
post-service exception review authentication boundary.

The FastAPI OpenAPI document is tracked at `contracts/openapi.json` and checked
byte for byte in CI. Its repository validator currently covers 34 paths,
requires versioned application routes, unique operation identifiers, tags and
responses, and rejects known development credentials.

The dashboard accessibility baseline covers all eight current main shells,
global visible focus, reduced-motion behavior, Next.js JSX accessibility lint,
and at least 4.5:1 contrast for normal muted text on the primary page and card
surfaces. It is not a claim of complete WCAG conformance and does not replace
manual keyboard, zoom, screen-reader, or browser contrast testing.

The local workstation built and validated the demonstrative Android debug APK
with Flutter 3.44.9, Android API 36, Build Tools 36.0.0, NDK 28.2, and Temurin
JDK 17. The artifact uses the reserved `https://api.example.invalid` endpoint,
requires API 24, targets API 36, and is signed by one Android debug signer with
APK Signature Scheme v2. Its validation evidence records SHA-256
`acbd95ec24fa399bb742287f2044148e64286451dbee252cd396e21f7f82f2c1`
and size 155,508,813 bytes. The APK remains a demonstrative build and is
ineligible for field execution, official reporting, and model training. The
[tracked artifact evidence](release-evidence/android-mvp-debug-apk-2026-08-14.json)
links the generated, ignored binary to source revision `8381f68`. Its versioned
schema and non-operational safety flags are checked in CI; a local release audit
additionally matches the available binary by byte size and SHA-256.

## External blockers for an operational pilot

- Replace the estimated road axis with an approved official axis and validate
  segment and zone geometry.
- Approve and retain a complete satellite source scene instead of relying on a
  partial development cache.
- Define operational identity, dispatch, GPS, geofence, team/equipment,
  weather, safety, and approval policies.
- Validate field measurements and photo/privacy controls, including retention,
  legal hold, EXIF handling, decoder checks, and malware scanning.
- Define key custody, rotation, backup, restore, and disaster-recovery
  procedures for encrypted media.
- Approve operational map/history promotion and an official report template.

Until those inputs and policies exist, `OFFICIAL_REPORTS_ENABLED` and
`TRAINING_DATA_ENABLED` must remain false and no prepared or simulated artifact
may be promoted to operational history.
