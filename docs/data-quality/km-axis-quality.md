# Kilometer-marker and candidate-axis quality

Date: 2026-08-06

## Observed measurements

- Marker count: 30, labelled km 0 through km 29.
- Metric CRS used for QA: EPSG:31983.
- Candidate length in numeric label order: 30,854.03 m.
- Average straight gap between adjacent labels: 1,063.93 m.
- Maximum gap: 2,034.84 m between km 24 and km 25.
- km 2 and km 3 are spatially reversed relative to their neighbouring points.
- Other large deviations include nearly 1.94 km for km 1→2 and km 3→4.
- No km 29+300 marker or official centerline was supplied.

## Treatment

The candidate axis and its 309 segments exist to unblock map/API development.
Every row is `estimated`, `needs_validation`, and operationally blocked. No
silent label swap, missing-point interpolation, or geometry repair was applied.

Resolution requires one of:

1. official road axis and stationing from the concessionaire;
2. corrected marker dataset with confirmation of km 2/km 3 and km 24/km 25;
3. reviewed derivation from an authoritative road network, recorded as a new
   candidate version.
