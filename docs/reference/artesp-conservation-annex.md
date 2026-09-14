# ARTESP road-conservation annex companion

- Source: `data/raw/03. Obrigações Contratuais/Artesp/LOTE 2 - Anexo 06 - Serviços
  de Conservação do Sistema Rodoviário.pdf`, 116 pages
- SHA-256: `94f186f5608cfe68e122d729830d6f9f2da8db2f39f9d8ba4481bf65344d62c1`

This companion is a ZENIT-oriented index and paraphrased extract. It does not replace
the annex, determine which concession it governs, or provide legal/engineering
certification. Before operational use, consult the original contract set, amendments,
current rules, and appropriate reviewers.

## Instrument structure relevant to ZENIT

The annex treats routine conservation as a managed program with asset inventory,
quality standards, service identification, planning, execution records, and digital
reports. Right-of-way work includes vegetation cover, cleaning, erosion, drainage,
fences, paved medians, stops, monuments, and related safety conditions.

### Whole-document outline

| PDF pages | Major content |
| ---: | --- |
| 1 | cover and identification of the Rota Sorocabana concession annex |
| 2-19 | introduction, initial intensive/adequacy programs, georeferenced survey, right of way, drainage, containment, signs, structures, buildings, automation, lighting, and program deadlines |
| 20-47 | routine-conservation concepts, program structure, and standards for road assets |
| 21-28 | detailed right-of-way and vegetation standards within the routine-conservation section |
| 48-76 | reporting/programming, inspection, and special/emergency conservation requirements |
| 77-116 | environment, health, safety, social programs, governance requirements, and associated schedules/tables |

Principal source locations:

| PDF page | Section | ZENIT relevance |
| ---: | --- | --- |
| 1-19 | purpose, definitions, mobilization and management | program context and reporting expectations |
| 21-28 | `b. Faixa de Domínio`, especially `b.1` | vegetation coverage, thresholds, maintenance types and response times |
| 48 onward | 3.4 reports and programming | service location/type, monthly record, programs and activities |
| 57 onward | annual/monthly programming | planned versus executed conservation work |
| 83-116 | environmental/social and other contractual programs | authorization, biodiversity, safety and broader governance context |

## Vegetation coverage and thresholds

Section `b.1` describes manual/mechanical trimming, edging, and removal of resulting
material along grassed medians and roads. It states a minimum 4 m treatment width from
the outer edge of the shoulder or the outermost drainage element, including slopes.
For interchanges, ramps, marginal roads, at-grade intersections, operational/support
buildings and yards, monuments, and rest areas, the described treatment extends to the
right-of-way limit.

The annex distinguishes:

- 30 cm for vegetation height generally within the right of way; and
- 10 cm around operational/support installations, monuments, and obelisks.

These values support ZENIT's general and special thresholds. They do not prove that
remote imagery can measure height, and their spatial scope cannot be implemented as a
single undifferentiated corridor buffer.

## Vegetation activity types

The annex separates activities that a useful domain model should not collapse:

- manual or mechanical vegetation cutting;
- weeding;
- removal of cut mass;
- edging;
- firebreak maintenance;
- removal of invasive/unwanted plants in managed grass;
- tree/shrub maintenance;
- removal/pruning of dead, diseased, dangerous, drainage-affecting, or
  visibility-obstructing trees/shrubs;
- vegetation-cover restoration; and
- cleaning/removal of plant waste and vegetation from paved areas.

It also introduces different frequencies or response periods for different activities.
Those source periods are contractual context, not automatically ZENIT schedules.

## Tree, shrub, and environmental constraints

The source treats tree/shrub danger as more than height. Relevant conditions include
death/disease, fall radius, free-zone exposure, roots affecting drainage, branches over
traffic areas, and obstruction of signs. Some interventions require environmental
authorization; where suppression is not authorized, another protective response may
be necessary.

Later environmental/social sections refer to biodiversity, fauna, vegetation
suppression, flora rescue, compensatory planting, integrated vegetation/pest
management, contractor controls, and health/safety. Therefore:

- `tree` and `shrub` cannot be modeled as mowing classes;
- a safety flag needs evidence and human review;
- cutting/pruning/suppression are distinct actions;
- environmental authorization status must be separate from recommendation status;
  and
- the academic project must not imply that an image or AI output satisfies legal or
  professional review.

## Waste, drainage, and service evidence

Cut material must be handled so it does not obstruct road or natural drainage, cover
remaining vegetation, harm safety, or create an unacceptable condition. Plant waste
and other debris require suitable removal and destination. Restoration of eroded or
uncovered areas can depend on geotechnical and professionally justified solutions.

ZENIT should therefore preserve, when an operational policy eventually exists:

- service type and exact segment/zone;
- start/finish and responsible actor/team;
- before/after evidence with compatible date/method;
- removed-material and destination status when required;
- drainage/visibility/safety exceptions;
- authorization and professional-report references; and
- reason for delay, rejection, or alternative treatment.

None of these fields should be simulated as an official record.

## Reports and programming

The conservation reporting sections require structured identification of performed
services by location and activity and organize right-of-way work into programs,
subprograms, and activities. They distinguish monthly reporting from annual/monthly
programming and support comparison of planned and performed work.

This motivates a traceable hierarchy:

```text
applicable program/rule version
  -> inspected condition
  -> planned activity and schedule
  -> approval/authorization
  -> work event
  -> evidence and exception
  -> reviewed result and report
```

The current ZENIT mowing rehearsal deliberately stops short of the work-event claim;
its records remain simulated and ineligible for official reporting.

## What ZENIT must not infer

- that this Lote 2 annex governs the Rodoanel demonstration or an ANTT concession;
- that every activity period in the annex is a universal maintenance schedule;
- that `poda` in this source is equivalent to every use of “mowing” in software;
- that grass, tree, shrub, urgency, and N1/N2/N3 are the same classification axis;
- that reaching 30 cm or 10 cm can be confirmed from NDVI alone;
- that detection is authorization for cutting, pruning, suppression, or dispatch;
- that an academic export is an ARTESP report; or
- that a generated summary replaces a professional report required by a contract.

## Suggested source mapping

| Source concept | ZENIT concept |
| --- | --- |
| minimum treatment width / right-of-way extent | authoritative zone geometry and applicable rule scope |
| 30 cm / 10 cm | versioned general/special thresholds |
| cutting, weeding, pruning, removal, restoration | distinct activity types |
| dangerous tree/shrub | reviewed safety/environmental exception |
| programmed frequency or response period | policy/schedule version, not hardcoded universal value |
| monthly service report | performed events grouped by road/location/activity |
| annual/monthly program | planning artifact separate from execution |
| photographic/professional evidence | typed evidence with source, checksum, reviewer and limitations |

## Operational verification checklist

Before treating a clause as applicable, identify the concession and contract version,
confirm amendments and referenced standards, validate right-of-way and operational
geometry, identify required environmental/professional authorization, define evidence
and reporting ownership, and document the approving authority and date.
