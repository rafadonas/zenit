"""GEO-002 protocol rules: ground truth eligibility and adjudication triggers.

Eligibility is inclusion-only: any missing field or unknown value excludes the
observation. Nothing here authorizes mowing or turns a photo reading into height.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum

PROTOCOL_VERSION = "gt-protocol-0.1"
EXCLUSION_CONFIRMATION = (
    "No demo, prepared, estimated, simulated or inconclusive data was used as ground truth, "
    "in the pilot or in training."
)


class ExclusionReason(StrEnum):
    DATA_STATUS_NOT_REAL = "data_status_not_real"
    CAMPAIGN_NOT_APPROVED = "campaign_not_approved"
    PROTOCOL_NOT_APPROVED = "protocol_not_approved"
    MISSING_CONSENT = "missing_consent_record"
    MISSING_LICENSE = "missing_license_record"
    DEVICE_NOT_REGISTERED = "device_not_registered"


class HeightExclusionReason(StrEnum):
    HEIGHT_STATUS_NOT_REAL = "height_data_status_not_real"
    HEIGHT_MISSING = "height_cm_missing_or_invalid"


@dataclass(frozen=True, slots=True)
class EligibilityPolicy:
    approved_campaigns: frozenset[str]
    approved_protocols: frozenset[str]
    registered_devices: frozenset[str]


@dataclass(frozen=True, slots=True)
class Eligibility:
    observation_id: str | None
    eligible: bool
    height_target_eligible: bool
    reasons: tuple[str, ...]


def _present(value: object) -> bool:
    return isinstance(value, str) and value.strip() != ""


def evaluate_eligibility(
    observation: Mapping[str, object], policy: EligibilityPolicy
) -> Eligibility:
    reasons: list[str] = []
    if observation.get("data_status") != "real":
        reasons.append(ExclusionReason.DATA_STATUS_NOT_REAL)
    if observation.get("campaign_id") not in policy.approved_campaigns:
        reasons.append(ExclusionReason.CAMPAIGN_NOT_APPROVED)
    if observation.get("protocol_version") not in policy.approved_protocols:
        reasons.append(ExclusionReason.PROTOCOL_NOT_APPROVED)
    if not _present(observation.get("consent_record_id")):
        reasons.append(ExclusionReason.MISSING_CONSENT)
    if not _present(observation.get("license_record_id")):
        reasons.append(ExclusionReason.MISSING_LICENSE)
    if observation.get("device_id") not in policy.registered_devices:
        reasons.append(ExclusionReason.DEVICE_NOT_REGISTERED)

    height_reasons: list[str] = []
    if observation.get("height_data_status") != "real":
        height_reasons.append(HeightExclusionReason.HEIGHT_STATUS_NOT_REAL)
    height = observation.get("height_cm")
    if isinstance(height, bool) or not isinstance(height, int | float) or height < 0:
        height_reasons.append(HeightExclusionReason.HEIGHT_MISSING)

    eligible = not reasons
    observation_id = observation.get("observation_id")
    return Eligibility(
        observation_id=observation_id if isinstance(observation_id, str) else None,
        eligible=eligible,
        height_target_eligible=eligible and not height_reasons,
        reasons=tuple(reasons + height_reasons),
    )


def summarize_eligibility(
    observations: Iterable[Mapping[str, object]], policy: EligibilityPolicy
) -> dict[str, object]:
    """Manifest-ready counts for section 9.3 of the protocol."""
    results = [(obs, evaluate_eligibility(obs, policy)) for obs in observations]
    excluded = Counter(
        reason
        for _, result in results
        if not result.eligible
        for reason in result.reasons
        if isinstance(reason, ExclusionReason)
    )
    height_excluded = Counter(
        reason
        for _, result in results
        if result.eligible and not result.height_target_eligible
        for reason in result.reasons
    )
    included = [result for _, result in results if result.eligible]
    return {
        "protocol_version": PROTOCOL_VERSION,
        "candidates": len(results),
        "included": len(included),
        "excluded": len(results) - len(included),
        "height_target_included": sum(1 for result in included if result.height_target_eligible),
        "excluded_by_reason": dict(sorted(excluded.items())),
        "height_target_excluded_by_reason": dict(sorted(height_excluded.items())),
        "data_statuses_seen": dict(
            sorted(Counter(str(obs.get("data_status")) for obs, _ in results).items())
        ),
        "included_observation_ids": [result.observation_id for result in included],
        "exclusion_confirmation": EXCLUSION_CONFIRMATION,
    }
