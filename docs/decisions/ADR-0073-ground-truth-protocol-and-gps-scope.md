# ADR-0073: Ground-truth protocol and GPS scope

- Status: proposed, project-owner scope decision recorded
- Date: 2026-09-14

## Context

The project intends to train an AI classifier for the vegetation-cover taxonomy,
but it does not yet have a validated dataset or a dedicated specialist. The
mobile demonstrator currently uses simulated locations. A protocol is needed
before real photos, GPS, or labels are collected.

## Decision

Define a draft ground-truth protocol around 100 m road segments and independent
left, right, median, and special zones. Stratify by road, zone, historical
context, period, lighting, device/source, and quality, and reserve spatial and
temporal holdouts. Include difficult and inconclusive cases instead of silently
discarding them.

Include GPS in the intended field scope with `gps_status`, timestamp, SRID,
device precision, consent reference, and a pseudonymized device reference. The
current app remains `simulated` until a permission/consent policy and device
pilot exist. Real photos require privacy handling, context/measurement views,
quality checks, checksums, and provenance.

Allow AI suggestions as `model_estimated` only. Human labels, model suggestions,
and accepted corrections remain separate. A future dataset requires independent
double annotation, adjudication, agreement metrics, licensing/consent, and
retention. Prepared or simulated evidence is never eligible for training or
official reporting.

## Consequences

- GPS is part of the planned protocol without falsely claiming that the current
  demonstrator captures real location.
- The project owner can define the academic procedure without claiming external
  scientific certification.
- GEO-003, GEO-004, MOB-005, and AI-001 remain gated on the documented quality,
  privacy, dataset, and review steps.
- A real Planet download or operational provider flow remains a separate ticket
  requiring account, licence, quota, and source-quality decisions.
