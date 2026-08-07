# Initial source-data audit

Date: 2026-08-06

Status: observed from the supplied files
Machine-readable manifest: `data/manifests/initial-source-audit.json`

## Scope and method

This audit inventories the eight supplied ZENIT source files now stored under
`data/raw/`. Files were moved into the protected raw directory without renaming or
content modification. SHA-256 checksums were calculated from their current bytes.

The reproducible standard-library script `scripts/audit_sources.py` detects file
formats from signatures, inspects Office Open XML containers, parses KML/KMZ, and
records geometry and attribute summaries. PDF metadata and text extractability
were checked with `pdfinfo` and `pdftotext`.

## Inventory

| Source | Bytes | SHA-256 | Detected format |
| --- | ---: | --- | --- |
| `01. Rodovia Motiva - Rodoanel/Marco km_rodoanel 2.kmz` | 3,104 | `f457d3a9aca27ea5e2ee7527f2efb80c38cd87a1b280d675a3d1881b186b11e4` | KMZ/ZIP |
| `01. Rodovia Motiva - Rodoanel/classificacao_rocada.kmz` | 1,893,845 | `7cfb094262d3c6e8485eb5f466a222dd9cb96e7157a0f4c4004c30685ba24dac` | plain KML/XML |
| `02. Dados Gestão verde - Atual/Retigrafico/RA-RET-ROÇ-LIMP-2026-03-13.xlsx` | 120,808 | `b88a8e394a291ac1cf885f4bb4a27e4e81bd7d467272608a519eaa5deaceb4aa` | XLSX |
| `02. Dados Gestão verde - Atual/Retigrafico/RA-RET-ROÇ-LIMP-2026-03-20.xlsx` | 120,783 | `516e64c1fc3574e33f956a6f24d7725626f01b6e9d1d83be05d469ea86a20466` | XLSX |
| `03. Obrigações Contratuais/ANTT/Programa de Exploração da Rodovia - PER - Volume I - Pós Esclarecimentos.pdf` | 1,905,342 | `6b41d221b92c6d685c1a67e5292d25770ec8a2073782ad19efb224bb8a445896` | PDF, 129 pages |
| `03. Obrigações Contratuais/Artesp/LOTE 2 - Anexo 06 - Serviços de Conservação do Sistema Rodoviário.pdf` | 1,166,452 | `94f186f5608cfe68e122d729830d6f9f2da8db2f39f9d8ba4481bf65344d62c1` | PDF, 116 pages |
| `Challenge CCR Motiva – Guia do Projeto.docx` | 18,199 | `5bad7edfd72ab8f86461c07ab0508d82214cf607a96bc52e888a33c7e9d2f090` | DOCX |
| `Inovação Aberta_FIAP_04.26.pdf` | 4,913,119 | `7bbd8a74c63f89b1e42bec838f2d32fd206c9e39458ddfc35af916631c198958` | PDF, 15 pages |

All three PDFs are unencrypted and text-extractable. The DOCX contains 58
non-empty paragraphs and opens as a valid Office Open XML container.

## Kilometer markers (F7)

- Valid KMZ containing one `doc.kml` member.
- 30 placemarks, all Point geometries.
- Descriptions represent SP021 km 0 through km 29 exactly once.
- Source order is not numeric: km 3 appears before km 2, km 9 before km 8, and
  km 11 appears near the end.
- Description whitespace is inconsistent (`km20` and tab/newline before km 8),
  so the parser must use a whitespace-tolerant regular expression.
- Coordinate bounds: longitude -46.83184134075487 to -46.73676819732765;
  latitude -23.63253885917052 to -23.41620665170857.
- KML coordinates are interpreted as EPSG:4326. A metric SIRGAS 2000 / UTM CRS
  must be validated before distance or segment generation.
- No explicit 29+300 marker exists.

## Mowing-classification polygons (F8)

- The `.kmz` extension is incorrect: the content is uncompressed KML/XML.
- 642 placemarks, all Polygon geometries.
- Coordinate bounds: longitude -46.8303484225394 to -46.728624868219;
  latitude -23.6292698139127 to -23.4078190380033.
- Operational category is carried by Placemark `name`:
  - Apenas manual: 342
  - Spider, Giro-Zero ou Trator com trincheira: 180
  - Trator com braço articulado: 106
  - Spider, com ancoragem: 14
- Only `classe`, `KM`, and `Latitude` are populated, each 642 times.
- Observed values demonstrate a shifted schema:
  - `classe` contains latitude-like values (-23.6284 to -23.4080).
  - `KM` contains longitude-like values (-46.8302 to -46.7294).
  - `Latitude` contains positive area-like values; sum 981,817.2701.
  - Declared longitude and area fields are absent from Placemark data.
- Placemark descriptions contain integer kilometer-like values from 0 to 28,
  with no value for 3, 7, 8, 11, or 29 observed in the category summary.

The normalized interpretation must therefore remain an inference with
`inference_status=needs_validation`. The source must not be repaired in place.

## Classification spreadsheets (F5/F6)

Both workbooks are valid XLSX containers with the same physical structure:

- one sheet named `ROÇADA`;
- 27 XML row records;
- maximum referenced column 67;
- 1,676 cell records;
- 40 merged ranges;
- Excel serial `45744` present in the worksheet content.

Serial 45744 corresponds to 2025-03-28 in the workbook date system and is the
reference date to persist. The dates embedded in filenames must be retained as
version labels, not treated as survey dates. Until their relationship is
confirmed, the files are separate versions of the same reference date and must
not be used to calculate growth.

The typed semantic decoder now produces 480 observations per workbook: 248
classified and 232 `X`/not-applicable values. Observed distributions over the 248
classified values are:

| Version label | N1 | N2 | N3 |
| --- | ---: | ---: | ---: |
| `RA-RET-ROÇ-LIMP-2026-03-13` | 163 (65.73%) | 49 (19.76%) | 36 (14.52%) |
| `RA-RET-ROÇ-LIMP-2026-03-20` | 179 (72.18%) | 56 (22.58%) | 13 (5.24%) |

The comparison finds 86 changed classification cells, confirming the manual.
These are document-version differences, not vegetation growth. `X` and `N/A`
are preserved as not applicable and are never normalized to N1.

## Typed parser validation

The parser package under `services/geospatial-worker/src/zenit_geospatial`
was executed against all four structured source files:

- marker parser: 30 records, no errors, one warning for non-sequential order;
- polygon parser: 642 records, no geometry errors, warnings for the false KMZ
  extension and shifted attribute inference;
- workbook parsers: 480 observations each, no parsing errors;
- workbook comparison: 86 differences at matching item/station keys.

Six deterministic standard-library tests cover content detection, manifest
hashing, whitespace-tolerant and unordered KM descriptions, shifted polygon
attributes, internal workbook dates, N1/N2/N3/X decoding, and version comparison.

PostGIS topology validation later identified 13 source polygons with
self-intersections. They remain unchanged in staging and each has a structured
`invalid_geometry` warning containing `ST_IsValidReason`. This distinction is
intentional: the standard-library parser validates ring structure and closure;
PostGIS performs the authoritative topology check.

## Contract and challenge documents (F1-F4)

The files are readable and consistent with the expected document types. Text
extraction confirms that the PER contains section 3.1.6 on the median and
right-of-way and that the ARTESP annex contains requirements for vegetation
cover and right-of-way conservation. Detailed legal-rule extraction remains a
human-reviewed documentation task; parser output must not reinterpret contract
language automatically.

## Proposed staging schema

- `source_file`: identity, original path/name, size, checksum, media type,
  received time, sensitivity, and immutable storage URI.
- `import_run`: source, parser name/version, start/end, status, parameters,
  anomaly counts, and report URI.
- `staging_km_marker`: source feature id, raw description, parsed road/km,
  original geometry EPSG:4326, parse status, and anomaly list.
- `staging_mowing_polygon`: source feature id, raw name/description/attributes,
  original geometry, inferred latitude/longitude/area, equipment class, and
  `inference_status`.
- `staging_vegetation_cell`: source version, sheet/cell coordinates, raw and
  decoded values, interval, section item, class, reference date, and parse status.
- Domain promotion tables should reference `source_file` and `import_run` and
  retain lineage to each staging record.

## Sprint 1 implementation plan

1. Add deterministic fixtures for unordered markers, shifted polygon attributes,
   and N1/N2/N3/X workbook values.
2. Implement typed parsers without writing to the database.
3. Add anomaly codes and JSON/Markdown report generation.
4. Define PostGIS staging/domain migrations with explicit SRIDs and constraints.
5. Add idempotent import-run orchestration keyed by checksum and parser version.
6. Load into staging, compare counts/checksums, and require explicit promotion.

Acceptance remains: 30 markers and 642 polygons parsed; shifted fields reported;
both spreadsheets share reference date 2025-03-28 as document versions; tests use
small deterministic fixtures; raw bytes remain unchanged.
