import pytest

from zenit_geospatial.ground_truth_rules import (
    EXCLUSION_CONFIRMATION,
    AdjudicationPolicy,
    AdjudicationTrigger,
    EligibilityPolicy,
    ExclusionReason,
    HeightExclusionReason,
    adjudication_triggers,
    evaluate_eligibility,
    summarize_eligibility,
)

POLICY = EligibilityPolicy(
    approved_campaigns=frozenset({"pilot-2026-wet"}),
    approved_protocols=frozenset({"gt-protocol-0.1"}),
    registered_devices=frozenset({"device-1"}),
)


def real_observation(**overrides: object) -> dict[str, object]:
    observation: dict[str, object] = {
        "observation_id": "obs-1",
        "data_status": "real",
        "campaign_id": "pilot-2026-wet",
        "protocol_version": "gt-protocol-0.1",
        "consent_record_id": "consent-7",
        "license_record_id": "license-2",
        "device_id": "device-1",
        "height_data_status": "real",
        "height_cm": 24,
    }
    observation.update(overrides)
    return observation


def test_fully_approved_real_observation_is_eligible_for_height_target() -> None:
    result = evaluate_eligibility(real_observation(), POLICY)

    assert result.eligible
    assert result.height_target_eligible
    assert result.reasons == ()


@pytest.mark.parametrize("status", ["prepared", "estimated", "simulated", "inconclusive", None])
def test_every_non_real_data_status_is_excluded(status: object) -> None:
    result = evaluate_eligibility(real_observation(data_status=status), POLICY)

    assert not result.eligible
    assert not result.height_target_eligible
    assert ExclusionReason.DATA_STATUS_NOT_REAL in result.reasons


@pytest.mark.parametrize(
    ("overrides", "reason"),
    [
        ({"campaign_id": "local-dev"}, ExclusionReason.CAMPAIGN_NOT_APPROVED),
        ({"protocol_version": "gt-protocol-0.0"}, ExclusionReason.PROTOCOL_NOT_APPROVED),
        ({"consent_record_id": "  "}, ExclusionReason.MISSING_CONSENT),
        ({"license_record_id": None}, ExclusionReason.MISSING_LICENSE),
        ({"device_id": "unregistered"}, ExclusionReason.DEVICE_NOT_REGISTERED),
    ],
)
def test_governance_gates_exclude_real_observations(overrides, reason) -> None:
    result = evaluate_eligibility(real_observation(**overrides), POLICY)

    assert not result.eligible
    assert result.reasons == (reason,)


def test_missing_fields_are_excluded_not_defaulted() -> None:
    result = evaluate_eligibility({"observation_id": "obs-empty"}, POLICY)

    assert not result.eligible
    assert set(ExclusionReason) <= set(result.reasons)


@pytest.mark.parametrize(
    ("overrides", "reason"),
    [
        ({"height_data_status": "estimated"}, HeightExclusionReason.HEIGHT_STATUS_NOT_REAL),
        ({"height_cm": None}, HeightExclusionReason.HEIGHT_MISSING),
        ({"height_cm": -1}, HeightExclusionReason.HEIGHT_MISSING),
        ({"height_cm": True}, HeightExclusionReason.HEIGHT_MISSING),
        ({"height_cm": "24"}, HeightExclusionReason.HEIGHT_MISSING),
    ],
)
def test_height_target_needs_real_numeric_height(overrides, reason) -> None:
    result = evaluate_eligibility(real_observation(**overrides), POLICY)

    assert result.eligible
    assert not result.height_target_eligible
    assert result.reasons == (reason,)


def test_summary_counts_exclusions_and_keeps_confirmation() -> None:
    observations = [
        real_observation(),
        real_observation(observation_id="obs-2", height_cm=None),
        real_observation(observation_id="obs-3", data_status="simulated"),
        real_observation(observation_id="obs-4", data_status="prepared", campaign_id="demo"),
    ]

    summary = summarize_eligibility(observations, POLICY)

    assert summary["candidates"] == 4
    assert summary["included"] == 2
    assert summary["excluded"] == 2
    assert summary["height_target_included"] == 1
    assert summary["excluded_by_reason"] == {
        "campaign_not_approved": 1,
        "data_status_not_real": 2,
    }
    assert summary["height_target_excluded_by_reason"] == {"height_cm_missing_or_invalid": 1}
    assert summary["data_statuses_seen"] == {"prepared": 1, "real": 2, "simulated": 1}
    assert summary["included_observation_ids"] == ["obs-1", "obs-2"]
    assert summary["exclusion_confirmation"] == EXCLUSION_CONFIRMATION


def annotation(**overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "cover_class": "grass_herbaceous",
        "cover_band": "50-75",
        "quality": "ok",
        "photo_height_cm": 20,
    }
    value.update(overrides)
    return value


def test_matching_annotations_within_tolerance_need_no_adjudication() -> None:
    assert adjudication_triggers((annotation(), annotation(photo_height_cm=24)), 22) == ()


@pytest.mark.parametrize(
    ("second", "field", "expected"),
    [
        ({"cover_class": "shrub"}, None, (AdjudicationTrigger.CLASS_MISMATCH,)),
        ({"cover_band": "10-25"}, None, (AdjudicationTrigger.COVER_BAND_NOT_ADJACENT,)),
        ({"quality": "rejected"}, None, (AdjudicationTrigger.QUALITY_REJECTED,)),
        (
            {"photo_height_cm": None},
            None,
            (AdjudicationTrigger.PHOTO_HEIGHT_READABILITY_MISMATCH,),
        ),
        ({"photo_height_cm": 26}, None, (AdjudicationTrigger.PHOTO_HEIGHT_DIFFERENCE,)),
    ],
)
def test_each_protocol_condition_triggers_adjudication(second, field, expected) -> None:
    assert adjudication_triggers((annotation(), annotation(**second)), field) == expected


def test_adjacent_cover_bands_do_not_trigger() -> None:
    assert adjudication_triggers((annotation(), annotation(cover_band="75-100")), None) == ()


def test_small_difference_across_threshold_still_triggers() -> None:
    triggers = adjudication_triggers(
        (annotation(photo_height_cm=29), annotation(photo_height_cm=31)), None
    )

    assert triggers == (AdjudicationTrigger.PHOTO_HEIGHT_THRESHOLD_CROSSING,)


def test_threshold_is_strict_exceedance() -> None:
    pair = (annotation(photo_height_cm=10), annotation(photo_height_cm=9))

    assert adjudication_triggers(pair, None) == ()


def test_photo_reading_diverging_from_field_height_triggers() -> None:
    pair = (annotation(photo_height_cm=20), annotation(photo_height_cm=21))

    assert adjudication_triggers(pair, 27) == (AdjudicationTrigger.FIELD_PHOTO_DIFFERENCE,)
    assert adjudication_triggers(pair, 32) == (
        AdjudicationTrigger.FIELD_PHOTO_DIFFERENCE,
        AdjudicationTrigger.FIELD_PHOTO_THRESHOLD_CROSSING,
    )


def test_policy_overrides_tolerance_and_bands() -> None:
    policy = AdjudicationPolicy(height_tolerance_cm=1, cover_bands=("low", "high"))
    pair = (
        annotation(cover_band="low", photo_height_cm=20),
        annotation(cover_band="high", photo_height_cm=22),
    )

    assert adjudication_triggers(pair, None, policy) == (
        AdjudicationTrigger.PHOTO_HEIGHT_DIFFERENCE,
    )


def test_invalid_annotation_values_are_rejected() -> None:
    with pytest.raises(ValueError, match="cover_band"):
        adjudication_triggers((annotation(cover_band="90%"), annotation()), None)
    with pytest.raises(ValueError, match="photo_height_cm"):
        adjudication_triggers((annotation(photo_height_cm=-3), annotation()), None)
