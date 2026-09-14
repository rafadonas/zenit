import pytest

from zenit_geospatial.ground_truth_rules import (
    EXCLUSION_CONFIRMATION,
    EligibilityPolicy,
    ExclusionReason,
    HeightExclusionReason,
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
