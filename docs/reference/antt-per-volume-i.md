# ANTT PER Volume I companion

- Source: `data/raw/03. Obrigações Contratuais/ANTT/Programa de Exploração da
  Rodovia - PER - Volume I - Pós Esclarecimentos.pdf`, 129 pages
- SHA-256: `6b41d221b92c6d685c1a67e5292d25770ec8a2073782ad19efb224bb8a445896`

This companion is a ZENIT-oriented index and paraphrased extract. It is not a legal
opinion, an official consolidated regulation, or proof that this particular PER
governs the road used in the academic demonstration. Consult the original instrument,
its contract, amendments, regulations, and qualified legal/engineering reviewers
before operational use.

## Instrument structure relevant to ZENIT

The PER organizes road obligations across recovery, maintenance, conservation,
operational services, monitoring, reporting, GIS, and asset management. Vegetation is
not an isolated image-classification problem: it is part of central median/right-of-way
integrity, visibility, drainage, fencing, access, safety, monitoring, planning, and
service history.

### Whole-document outline

| PDF pages | Major content |
| ---: | --- |
| 1-7 | cover, contents, and abbreviations |
| 8-10 | introduction and road-system description |
| 11-38 | structural services: pavement, signs/safety, structures, drainage, earthworks, right of way, buildings, lighting, and tunnels |
| 39-54 | works front: capacity, improvements, emergencies, geometry, and technical parameters |
| 55-58 | conservation front |
| 59-108 | operational services, monitoring/ITS, user service, tolling, weighing, data, security, tunnels, and inspection |
| 109-116 | monitoring, reports, GIS, and concession asset management |
| 117-125 | environmental management and sustainability reporting |
| 125-128 | technical, normative, and bibliographic references |
| 129 | Volume II reference |

Principal source locations:

| PDF page | Section | ZENIT relevance |
| ---: | --- | --- |
| 30-31 | 3.1.6 Central median and right of way | recovery/maintenance scope and vegetation performance parameters |
| 55-58 | 3.3 Conservation front, especially 3.3.6 | routine conservation and vegetation/removal coverage |
| 80 onward | traffic inspection and operational services | detection, location, response, and records |
| 109-113 | 4 Monitoring and reports | annual monitoring, method, parameters, actions and results |
| 111 | 4.2.6 Median/right-of-way monitoring report | occupation/access inventory and risky trees |
| 114-116 | 4.7 GIS and 4.8 SIGACO | georeferenced integration, inventory, inspections, plans and history |

PDF pages are used here, even where the printed footer differs.

## Vegetation performance parameters

Section 3.1.6 describes recovery and maintenance of the central median and right of
way based on monitoring. Its performance table includes:

- in access, interchange, toll-plaza, and weighing-station areas, ground vegetation
  should not exceed 10 cm within a stated minimum 10 m width;
- in other right-of-way locations, ground vegetation should not exceed 30 cm within a
  stated minimum 4 m width;
- inside curves, the treated width must support adequate visibility;
- mowing, weeding, pruning, and removal of resulting material cover the road right of
  way, including the median;
- fence firebreak/protection strips should remain free of vegetation or residual
  material; and
- vegetation must not impair user visibility, traffic/structure safety, or remain
  dead/diseased where the parameter prohibits it.

ZENIT preserves 30 cm as its general threshold and 10 cm for explicitly modeled
special/operational zones. The source's width and area language must remain attached
to the applicable geometry; it must not be converted into a universal fixed buffer.

## Conservation scope

Section 3.3 defines conservation as preventive, routine, and emergency operations
that preserve technical, physical, and operational characteristics. Section 3.3.6
includes mowing, weeding, pruning, removal of resulting material, vegetation cover
recovery, care around operational buildings, firebreaks/fences, and protection from
irregular occupation.

This supports a workflow that separates:

- observed condition;
- safety/visibility exception;
- recommended maintenance;
- scheduled service;
- performed service and removed material; and
- later monitored result.

It does not support automatic dispatch from an image classification. The source
assigns duties to a concessionaire within its contract; ZENIT's academic prototype is
not that concessionaire.

## Monitoring and reporting

Section 4 states that monitoring reports are periodic and must explain performance
parameters, methodology, and updated functional-element inventory. The median and
right-of-way report includes authorizations/occupations, irregular occupation and
access, actions and effectiveness, plus evaluation of trees presenting road-safety
risk and a corrective schedule.

The GIS provisions describe geoprocessing as an integration layer for physical asset
monitoring and management information. The asset-management provisions call for
georeferenced inventory, inspection history, plans, interventions, and current state.

For ZENIT, this motivates — but does not legally prescribe — these data requirements:

- versioned segment/zone geometry and applicable rule set;
- observation and reference time;
- evidence source, method, quality, and location;
- condition, recommendation, human decision, work plan, and completion as separate
  records;
- tree-risk/visibility exceptions separate from grass-height classification;
- performed-versus-planned comparison; and
- spatially searchable history with immutable audit links.

## What ZENIT must not infer

- that this PER applies to SP-021 or every Motiva concession;
- that all performance periods and reporting frequencies apply to the academic demo;
- that a 10 cm/30 cm source threshold can be measured exactly by satellite NDVI;
- that annual or monthly reporting language authorizes a ZENIT official report;
- that a detected tree should be removed without environmental/safety authorization;
  or
- that source use of traffic-light colors defines ZENIT's vegetation taxonomy.

## Suggested source mapping

| Source concept | ZENIT concept |
| --- | --- |
| central median/right of way | separate `median`, `left`, `right`, and explicit `special` zones |
| vegetation threshold | versioned zone threshold, not cover type |
| monitoring | dated observation with method and quality |
| risk tree/visibility issue | explicit exception requiring human review |
| conservation programming | prepared plan distinct from execution authorization |
| action and effectiveness | work event plus later comparable observation |
| GIS/asset history | PostGIS geometry, provenance, inspection, and intervention links |

## Operational verification checklist

Before citing this source as an obligation, identify the road and concession, confirm
the instrument/version and amendments, map the exact clause and performance phase,
obtain authoritative geometry, confirm environmental and safety rules, and record the
reviewer and date. Until then, the companion is academic domain evidence only.
