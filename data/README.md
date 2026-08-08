# ZENIT source data

## Handling policy

- Put supplied source files in `data/raw/`.
- Never edit or replace a raw file in place.
- Do not commit raw documents, imagery, spreadsheets, KMZ/KML files, personal
  data, or credentials.
- Record filename, byte size, SHA-256, import time, parser version, reference
  date, CRS, and validation status before promoting derived data.
- Write normalized outputs only to `data/processed/` or object storage.

## Expected initial inputs

- `Challenge CCR Motiva - Guia do Projeto.docx`
- `Inovacao Aberta_FIAP_04.26.pdf` (the exact supplied filename may differ)
- `Programa de Exploracao da Rodovia - PER - Volume I.pdf`
- `LOTE 2 - Anexo 06 - Servicos de Conservacao do Sistema Rodoviario.pdf`
- `RA-RET-ROC-LIMP-2026-03-13.xlsx`
- `RA-RET-ROC-LIMP-2026-03-20.xlsx`
- `Marco km_rodoanel 2.kmz`
- `classificacao_rocada.kmz`
- `ZENIT_Guia_Tecnico_APIs_Sentinel_CBers.pdf`

Filenames are descriptive expectations, not normalization instructions. Keep the
original supplied names unchanged.

## Known interpretation constraints

- Both spreadsheets have an internal reference date of 2025-03-28 and must be
  imported as separate document versions, not as a confirmed time series.
- `classificacao_rocada.kmz` may contain plain KML despite its extension and has
  an inconsistent attribute mapping. Any inferred mapping must remain marked
  `needs_validation`.
- KML coordinates must be preserved in WGS 84 (EPSG:4326); the metric SIRGAS
  2000 / UTM CRS for derived processing must be explicitly validated.
- The satellite API guide is a dated technical reference, not a credential file,
  satellite scene, or current observation. Provider details require production
  revalidation, and its ~1 km AOI suggestion does not override 100 m analysis.
