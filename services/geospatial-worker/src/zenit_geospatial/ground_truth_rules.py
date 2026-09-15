"""GEO-002 protocol rules: ground truth eligibility and adjudication triggers.

Eligibility is inclusion-only: any missing field or unknown value excludes the
observation. Nothing here authorizes mowing or turns a photo reading into height.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum

PROTOCOL_VERSION = "zenit-ground-truth-v0.1-draft"
EXCLUSION_CONFIRMATION = (
    "No demo, prepared, estimated, simulated or inconclusive data was used as ground truth, "
    "in the pilot or in training."
)


class ExclusionReason(StrEnum):
    MISSING_OBSERVATION_ID = "missing_observation_id"
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
    if not _present(observation.get("observation_id")):
        reasons.append(ExclusionReason.MISSING_OBSERVATION_ID)
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
        "eligible_for_model_training": False,
        "eligible_for_official_reporting": False,
        "eligible_for_operations": False,
        "authorizes_field_work": False,
        "authorizes_mowing": False,
    }


class AdjudicationTrigger(StrEnum):
    CLASS_MISMATCH = "cover_class_mismatch"
    COVER_BAND_NOT_ADJACENT = "cover_band_not_adjacent"
    QUALITY_REJECTED = "quality_rejected"
    PHOTO_HEIGHT_READABILITY_MISMATCH = "photo_height_readability_mismatch"
    PHOTO_HEIGHT_DIFFERENCE = "photo_height_difference"
    PHOTO_HEIGHT_THRESHOLD_CROSSING = "photo_height_threshold_crossing"
    FIELD_PHOTO_DIFFERENCE = "field_photo_height_difference"
    FIELD_PHOTO_THRESHOLD_CROSSING = "field_photo_threshold_crossing"


@dataclass(frozen=True, slots=True)
class AdjudicationPolicy:
    # Academic assumptions: tolerance from protocol section 7.3, cover bands from the
    # GEO-001 cover taxonomy section 4.1 (share of the annotated unit).
    height_tolerance_cm: float = 5.0
    thresholds_cm: tuple[float, ...] = (10.0, 30.0)
    cover_bands: tuple[str, ...] = ("0", "1-10", "10-25", "25-50", "50-75", "75-100")


def _crosses(first: float, second: float, thresholds: tuple[float, ...]) -> bool:
    return any((first > threshold) != (second > threshold) for threshold in thresholds)


def _height(annotation: Mapping[str, object]) -> float | None:
    value = annotation.get("photo_height_cm")
    if value is None or isinstance(value, bool):
        return None
    if not isinstance(value, int | float) or value < 0:
        raise ValueError("photo_height_cm must be a non-negative number or null (not readable)")
    return float(value)


def adjudication_triggers(
    annotations: tuple[Mapping[str, object], Mapping[str, object]],
    field_height_cm: float | None,
    policy: AdjudicationPolicy | None = None,
) -> tuple[AdjudicationTrigger, ...]:
    """Section 7.3 triggers for one double-annotated observation, in a stable order."""
    active = policy or AdjudicationPolicy()
    first, second = annotations
    triggers: list[AdjudicationTrigger] = []

    if first.get("cover_class") != second.get("cover_class"):
        triggers.append(AdjudicationTrigger.CLASS_MISMATCH)

    bands = [annotation.get("cover_band") for annotation in annotations]
    if any(band is not None for band in bands):
        unknown = [band for band in bands if band not in active.cover_bands]
        if unknown:
            raise ValueError(f"cover_band outside the configured bands: {unknown}")
        ranks = [active.cover_bands.index(str(band)) for band in bands]
        if abs(ranks[0] - ranks[1]) > 1:
            triggers.append(AdjudicationTrigger.COVER_BAND_NOT_ADJACENT)

    if "rejected" in (first.get("quality"), second.get("quality")):
        triggers.append(AdjudicationTrigger.QUALITY_REJECTED)

    heights = [_height(first), _height(second)]
    readable = [height for height in heights if height is not None]
    if len(readable) == 1:
        triggers.append(AdjudicationTrigger.PHOTO_HEIGHT_READABILITY_MISMATCH)
    if len(readable) == 2:
        if abs(readable[0] - readable[1]) > active.height_tolerance_cm:
            triggers.append(AdjudicationTrigger.PHOTO_HEIGHT_DIFFERENCE)
        if _crosses(readable[0], readable[1], active.thresholds_cm):
            triggers.append(AdjudicationTrigger.PHOTO_HEIGHT_THRESHOLD_CROSSING)

    if field_height_cm is not None:
        if any(abs(height - field_height_cm) > active.height_tolerance_cm for height in readable):
            triggers.append(AdjudicationTrigger.FIELD_PHOTO_DIFFERENCE)
        if any(_crosses(height, field_height_cm, active.thresholds_cm) for height in readable):
            triggers.append(AdjudicationTrigger.FIELD_PHOTO_THRESHOLD_CROSSING)

    return tuple(triggers)
