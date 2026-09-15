from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal, Protocol, Self
from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, model_validator

from zenit_api.auth import AuthenticatedUser, get_current_user
from zenit_api.config import get_settings

CoverType = Literal[
    "unknown",
    "grass_herbaceous",
    "shrub",
    "tree",
    "mixed",
    "non_vegetation",
]
UnknownReason = Literal[
    "insufficient_resolution",
    "shadow",
    "cloud_or_haze",
    "blur_or_exposure",
    "canopy_occlusion",
    "vehicle_or_structure_occlusion",
    "mixed_without_dominance",
    "source_conflict",
    "out_of_zone",
    "privacy_redaction",
    "other",
]
CoverMethod = Literal["model_estimated", "human_reviewed"]
SourceType = Literal[
    "satellite",
    "field_photo",
    "manual_annotation",
    "model_output",
    "other",
]
ValidityStatus = Literal["valid", "limited", "invalid"]
ConfidenceBand = Literal["low", "medium", "high"]
QualityStatus = Literal["accepted", "limited", "rejected"]
ReviewState = Literal["pending", "accepted", "corrected", "rejected"]
DataStatus = Literal["real", "estimated", "simulated", "prepared", "inconclusive"]
GpsStatus = Literal["simulated", "unavailable"]


class VegetationCoverObservation(BaseModel):
    observation_id: UUID
    segment_id: UUID
    segment_zone_id: UUID
    segment_index: int = Field(ge=0)
    zone_type: Literal["left", "right", "median", "special"]
    cover_type: CoverType
    unknown_reason: UnknownReason | None
    cover_type_method: CoverMethod
    source_type: SourceType
    source_reference: str = Field(min_length=1)
    source_acquired_at: datetime | None
    source_checksum_sha256: str | None = Field(default=None, min_length=64, max_length=64)
    validity_status: ValidityStatus
    confidence_band: ConfidenceBand
    quality_status: QualityStatus
    review_state: ReviewState
    taxonomy_version: str = Field(min_length=1)
    model_version: str | None
    coverage_band: Literal["none", "sparse", "partial", "dominant"] | None
    visibility: Literal["clear", "partially_occluded", "mostly_occluded", "illegible"] | None
    dominance: Literal["dominant", "co-dominant", "not_dominant", "not_applicable"] | None
    spatial_relation: Literal["inside_zone", "overhang", "adjacent", "uncertain"] | None
    rationale: str | None
    gps_status: GpsStatus
    gps_accuracy_m: float | None = Field(default=None, ge=0)
    data_status: DataStatus
    provenance: dict[str, Any]
    supersedes_observation_id: UUID | None
    reviewed_by_user_id: UUID | None
    reviewed_at: datetime | None
    created_at: datetime
    eligible_for_official_reporting: Literal[False] = False

    @model_validator(mode="after")
    def validate_draft_contract_invariants(self) -> Self:
        if self.cover_type == "unknown" and self.unknown_reason is None:
            raise ValueError("unknown cover type requires an unknown reason")
        if self.cover_type not in {"unknown", "mixed"} and self.unknown_reason is not None:
            raise ValueError("unknown reason is only valid for unknown or mixed cover")
        if self.cover_type in {"unknown", "mixed"} and not (self.rationale or "").strip():
            raise ValueError("unknown or mixed cover requires a rationale")
        if self.cover_type_method == "model_estimated" and not (self.model_version or "").strip():
            raise ValueError("model-estimated cover requires a model version")
        if self.gps_accuracy_m is not None:
            raise ValueError("GPS accuracy is unavailable in the draft GPS scope")
        return self


class VegetationCoverMetadata(BaseModel):
    segment_id: UUID
    result_count: int = Field(ge=0)
    total_count: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)
    truncated: bool
    warning: str


class VegetationCoverCollection(BaseModel):
    items: list[VegetationCoverObservation]
    metadata: VegetationCoverMetadata


class VegetationCoverReader(Protocol):
    async def by_segment(
        self,
        segment_id: UUID,
        *,
        actor: AuthenticatedUser,
        limit: int,
    ) -> VegetationCoverCollection: ...


class VegetationCoverSegmentNotFoundError(Exception):
    pass


class VegetationCoverPermissionError(Exception):
    pass


class PostgresVegetationCoverRepository:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url.replace("postgresql+psycopg://", "postgresql://", 1)

    async def by_segment(
        self,
        segment_id: UUID,
        *,
        actor: AuthenticatedUser,
        limit: int,
    ) -> VegetationCoverCollection:
        connection = await psycopg.AsyncConnection.connect(self._database_url)
        async with connection, connection.cursor() as cursor:
            await cursor.execute(
                """
                SELECT axis.road_id
                FROM road_segment segment
                JOIN road_axis_candidate axis ON axis.id = segment.road_axis_candidate_id
                WHERE segment.id = %s
                """,
                (segment_id,),
            )
            segment = await cursor.fetchone()
            if segment is None:
                raise VegetationCoverSegmentNotFoundError

            await cursor.execute(
                """
                SELECT 1
                FROM road_user_role assignment
                WHERE assignment.user_id = %s
                  AND assignment.road_id = %s
                  AND assignment.role IN ('manager', 'supervisor')
                  AND assignment.data_status <> 'simulated'
                LIMIT 1
                """,
                (actor.id, segment[0]),
            )
            if await cursor.fetchone() is None:
                raise VegetationCoverPermissionError

            await cursor.execute(
                """
                SELECT
                    observation.id,
                    segment.id,
                    observation.segment_zone_id,
                    segment.segment_index,
                    zone.zone_type,
                    observation.cover_type,
                    observation.unknown_reason,
                    observation.cover_type_method,
                    observation.source_type,
                    observation.source_reference,
                    observation.source_acquired_at,
                    observation.source_checksum_sha256,
                    observation.validity_status,
                    observation.confidence_band,
                    observation.quality_status,
                    observation.review_state,
                    observation.taxonomy_version,
                    observation.model_version,
                    observation.coverage_band,
                    observation.visibility,
                    observation.dominance,
                    observation.spatial_relation,
                    observation.rationale,
                    observation.gps_status,
                    observation.gps_accuracy_m,
                    observation.data_status,
                    observation.provenance,
                    observation.supersedes_observation_id,
                    observation.reviewed_by_user_id,
                    observation.reviewed_at,
                    observation.created_at,
                    observation.eligible_for_official_reporting,
                    COUNT(*) OVER ()
                FROM vegetation_cover_observation observation
                JOIN segment_zone zone ON zone.id = observation.segment_zone_id
                JOIN road_segment segment ON segment.id = zone.road_segment_id
                WHERE segment.id = %s
                  AND NOT EXISTS (
                      SELECT 1
                      FROM vegetation_cover_observation newer
                      WHERE newer.supersedes_observation_id = observation.id
                  )
                ORDER BY observation.created_at DESC, observation.id DESC
                LIMIT %s
                """,
                (segment_id, limit),
            )
            rows = await cursor.fetchall()

        items = [
            VegetationCoverObservation(
                observation_id=row[0],
                segment_id=row[1],
                segment_zone_id=row[2],
                segment_index=row[3],
                zone_type=row[4],
                cover_type=row[5],
                unknown_reason=row[6],
                cover_type_method=row[7],
                source_type=row[8],
                source_reference=row[9],
                source_acquired_at=row[10],
                source_checksum_sha256=row[11].strip() if row[11] is not None else None,
                validity_status=row[12],
                confidence_band=row[13],
                quality_status=row[14],
                review_state=row[15],
                taxonomy_version=row[16],
                model_version=row[17],
                coverage_band=row[18],
                visibility=row[19],
                dominance=row[20],
                spatial_relation=row[21],
                rationale=row[22],
                gps_status=row[23],
                gps_accuracy_m=float(row[24]) if row[24] is not None else None,
                data_status=row[25],
                provenance=row[26],
                supersedes_observation_id=row[27],
                reviewed_by_user_id=row[28],
                reviewed_at=row[29],
                created_at=row[30],
                eligible_for_official_reporting=row[31],
            )
            for row in rows
        ]
        total_count = int(rows[0][32]) if rows else 0
        return VegetationCoverCollection(
            items=items,
            metadata=VegetationCoverMetadata(
                segment_id=segment_id,
                result_count=len(items),
                total_count=total_count,
                limit=limit,
                truncated=total_count > len(items),
                warning=(
                    "Cover type is versioned evidence, not vegetation height, current condition, "
                    "or authorization for mowing."
                ),
            ),
        )


async def get_vegetation_cover_reader() -> VegetationCoverReader:
    return PostgresVegetationCoverRepository(get_settings().database_url)


router = APIRouter(prefix="/v1/segments", tags=["vegetation-cover"])


@router.get(
    "/{segment_id}/vegetation-cover",
    response_model=VegetationCoverCollection,
)
async def list_vegetation_cover(
    segment_id: UUID,
    actor: Annotated[AuthenticatedUser, Depends(get_current_user)],
    reader: Annotated[VegetationCoverReader, Depends(get_vegetation_cover_reader)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> VegetationCoverCollection:
    try:
        return await reader.by_segment(segment_id, actor=actor, limit=limit)
    except VegetationCoverSegmentNotFoundError:
        raise HTTPException(status_code=404, detail="Segment not found") from None
    except VegetationCoverPermissionError:
        raise HTTPException(status_code=403, detail="No access to this road") from None
