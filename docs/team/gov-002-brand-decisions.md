# GOV-002: Academic brand boundary

- Responsavel: Guilherme
- Branch: `docs/gov-002-academic-brand-boundary`
- Status: ready for review
- Decision record: [`ADR-0069`](../decisions/ADR-0069-academic-brand-boundary.md)

## Confirmed decision

ZENIT is an academic/student project. The team has no direct relationship,
sponsorship, authorization, or brand license from Motiva.

The accepted direction is therefore:

- use ZENIT as the product brand;
- keep the current palette as ZENIT academic placeholders;
- mention Motiva only as challenge/source context when needed;
- avoid Motiva logo, official brand assets, official colors, slogans, and
  endorsement language;
- keep all operational, official-reporting, legal, privacy, and field-authority
  gates separate from this brand decision.

## Files updated

- `docs/decisions/ADR-0069-academic-brand-boundary.md`
- `docs/team/design-system.md`
- `docs/reference/design-system-source.md`
- `docs/reference/fiap-motiva-challenge-brief.md`
- `docs/manual/README.md`
- `docs/manual/delivery-validation-and-governance.md`
- `docs/team/team-assignments.md`
- `docs/team/work-packages.md`
- `README.md`
- `apps/dashboard/src/styles/tokens.css`

## Acceptance evidence

| Criterion | Evidence |
| --- | --- |
| Name, logo, colors, and Motiva mentions have an explicit rule | ADR-0069 defines ZENIT-only academic identity and Motiva-use boundaries. |
| Dashboard tokens are updated or classified | Token comments and design docs state values are ZENIT academic placeholders, not Motiva colors. |
| No official affiliation is implied | README, manual, source companions, and design system prohibit endorsement or official brand use. |
| Blocker is not over-bypassed | WEB-010 and official Motiva usage remain blocked until separate approvals. |

## Remaining blocked cases

- official Motiva logo or brand asset usage;
- public/customer-facing deployment that implies Motiva sponsorship;
- official report templates or marketing claims;
- telemetry or screenshot monitoring without privacy/tooling approval.
