# Sprint 4 — dashboard screen evidence

Real ZENIT dashboard (Next.js) served by the full Docker Compose stack in GitHub
Actions run [39344479914](https://github.com/rafadonas/zenit/actions/runs/39344479914)
and captured with `apps/dashboard/scripts/capture-gov-001.mjs` (headless Chrome).

- **Empty demo database.** The original challenge source files (KMZ and
  workbooks) are not in Git, so no segments, recommendations, photos or results
  were imported; queues show their real empty states. Only the road code
  `SP021` and the two local fixture identities (`manager@example.com`,
  `supervisor@example.com`) were created.
- **Object storage stub.** MinIO images are no longer publicly downloadable;
  the run replaced MinIO with a stub that only answers the API health probe.
  No screen captured here reads or writes object storage.
- **Defects found and kept visible:** `web-defeito-tablet-768.png` (compact
  sidebar labels break at 768 px) and `web-resultados-com-defeito-alerta.png`
  ("Escopo seguro" notice renders unstyled on the post-service pages).
- Not field data; not eligible for training, official reporting or field
  authorization.
