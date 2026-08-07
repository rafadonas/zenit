from __future__ import annotations

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field, model_validator

RULE_VERSION = "baseline-2026-08-07.1"
GENERAL_THRESHOLD_CM = 30.0
SPECIAL_THRESHOLD_CM = 10.0
MIN_VALID_PIXEL_PERCENT = 70.0

ZoneType = Literal["left", "right", "median", "special"]
DataStatus = Literal["real", "estimated", "simulated", "prepared", "inconclusive"]


class AnalysisPreviewRequest(BaseModel):
    zone_type: ZoneType
    red_reflectance: float = Field(ge=0)
    nir_reflectance: float = Field(ge=0)
    valid_pixel_percent: float = Field(ge=0, le=100)
    scene_quality: Literal["acceptable", "low", "rejected"]
    scene_data_status: DataStatus
    observed_height_cm: float | None = Field(default=None, ge=0)
    height_data_status: DataStatus | None = None

    @model_validator(mode="after")
    def require_height_provenance(self) -> AnalysisPreviewRequest:
        if (self.observed_height_cm is None) != (self.height_data_status is None):
            raise ValueError("observed height and its data status must be supplied together")
        return self


class AnalysisPreviewResponse(BaseModel):
    rule_version: str
    threshold_cm: float
    mean_ndvi: float | None
    conclusion: Literal["conclusive", "inconclusive"]
    recommendation: Literal["monitor", "inspect", "mowing_review"]
    confidence_band: Literal["low", "medium", "high"]
    requires_human_approval: bool
    eligible_for_official_reporting: bool
    reasons: list[str]


def calculate_ndvi(red_reflectance: float, nir_reflectance: float) -> float | None:
    denominator = nir_reflectance + red_reflectance
    if denominator == 0:
        return None
    return round((nir_reflectance - red_reflectance) / denominator, 6)


def evaluate_analysis(request: AnalysisPreviewRequest) -> AnalysisPreviewResponse:
    threshold = SPECIAL_THRESHOLD_CM if request.zone_type == "special" else GENERAL_THRESHOLD_CM
    ndvi = calculate_ndvi(request.red_reflectance, request.nir_reflectance)
    reasons: list[str] = []

    poor_scene = (
        request.scene_quality != "acceptable"
        or request.valid_pixel_percent < MIN_VALID_PIXEL_PERCENT
        or ndvi is None
    )
    non_real_input = request.scene_data_status != "real"
    if poor_scene:
        reasons.append("Satellite quality is insufficient for a conclusive baseline.")
    if non_real_input:
        reasons.append(
            f"Scene data is labelled {request.scene_data_status}; inspection is required."
        )

    if poor_scene or non_real_input:
        return AnalysisPreviewResponse(
            rule_version=RULE_VERSION,
            threshold_cm=threshold,
            mean_ndvi=ndvi,
            conclusion="inconclusive",
            recommendation="inspect",
            confidence_band="low",
            requires_human_approval=True,
            eligible_for_official_reporting=False,
            reasons=reasons,
        )

    if request.observed_height_cm is None or request.height_data_status != "real":
        reasons.append("NDVI does not measure vegetation height; a field measurement is required.")
        return AnalysisPreviewResponse(
            rule_version=RULE_VERSION,
            threshold_cm=threshold,
            mean_ndvi=ndvi,
            conclusion="inconclusive",
            recommendation="inspect",
            confidence_band="low",
            requires_human_approval=True,
            eligible_for_official_reporting=False,
            reasons=reasons,
        )

    exceeds_threshold = request.observed_height_cm > threshold
    reasons.append(
        f"Real observed height ({request.observed_height_cm:g} cm) "
        f"{'exceeds' if exceeds_threshold else 'does not exceed'} the {threshold:g} cm threshold."
    )
    return AnalysisPreviewResponse(
        rule_version=RULE_VERSION,
        threshold_cm=threshold,
        mean_ndvi=ndvi,
        conclusion="conclusive",
        recommendation="mowing_review" if exceeds_threshold else "monitor",
        confidence_band="high",
        requires_human_approval=True,
        eligible_for_official_reporting=True,
        reasons=reasons,
    )


router = APIRouter(prefix="/v1/analysis", tags=["analysis"])


@router.post("/preview", response_model=AnalysisPreviewResponse)
async def preview_analysis(request: AnalysisPreviewRequest) -> AnalysisPreviewResponse:
    """Evaluate versioned rules without persisting or authorizing field work."""

    return evaluate_analysis(request)
