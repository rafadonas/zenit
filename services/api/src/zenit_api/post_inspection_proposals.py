from __future__ import annotations

import hashlib
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal, Protocol
from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends, Header, HTTPException
from psycopg.errors import UniqueViolation
from pydantic import BaseModel, ConfigDict, Field, field_validator

from zenit_api.auth import AuthenticatedUser, get_current_user
from zenit_api.config import get_settings


class PreparedProposalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    creation_rationale: str = Field(min_length=1, max_length=2000)

    @field_validator("creation_rationale")
    @classmethod
    def normalize_rationale(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("creation rationale cannot be blank")
        return normalized


class PreparedProposalResponse(BaseModel):
    proposal_id: UUID
    summary_id: UUID
    work_order_id: UUID
    road_code: str
    segment_index: int
    zone_type: Literal["left", "right", "median", "special"]
    policy_version: str
    creation_rationale: str
    recommendation: Literal["monitor", "mowing_review"]
    applicable_threshold_cm: Decimal
    maximum_height_cm: Decimal
    threshold_exceeded: bool
    requires_human_review: Literal[True] = True
    location_status: Literal["simulated"] = "simulated"
    evidence_status: Literal["prepared_reviewed_non_operational"] = (
        "prepared_reviewed_non_operational"
    )
    data_status: Literal["prepared"] = "prepared"
    eligible_for_model_training: Literal[False] = False
    eligible_for_official_reporting: Literal[False] = False
    authorizes_field_work: Literal[False] = False
    created_at: datetime


class PreparedProposalCollection(BaseModel):
    items: list[PreparedProposalResponse]
    result_count: int
    limit: int
    truncated: bool
    warning: str = (
        "Prepared proposals require a separate human decision and never authorize mowing."
    )


class ProposalNotFoundError(Exception):
    pass


class ProposalPermissionError(Exception):
    pass


class ProposalPolicyUnavailableError(Exception):
    pass


class ProposalIdempotencyConflictError(Exception):
    pass


class ProposalAlreadyExistsError(Exception):
    pass


class PreparedProposalWriter(Protocol):
    async def create(
        self,
        *,
        summary_id: UUID,
        actor: AuthenticatedUser,
        idempotency_key: str,
        request: PreparedProposalRequest,
    ) -> PreparedProposalResponse: ...


class PreparedProposalReader(Protocol):
    async def list_for_actor(
        self, *, actor: AuthenticatedUser, limit: int
    ) -> PreparedProposalCollection: ...


class PostgresPreparedProposalRepository:
    def __init__(self, database_url: str, policy_version: str) -> None:
        self._database_url = database_url.replace("postgresql+psycopg://", "postgresql://", 1)
        self._policy_version = policy_version

    async def create(
        self,
        *,
        summary_id: UUID,
        actor: AuthenticatedUser,
        idempotency_key: str,
        request: PreparedProposalRequest,
    ) -> PreparedProposalResponse:
        key_hash = hashlib.sha256(idempotency_key.encode()).hexdigest()
        connection = await psycopg.AsyncConnection.connect(self._database_url)
        try:
            async with connection, connection.cursor() as cursor:
                existing = await self._by_key(cursor, key_hash)
                if existing:
                    if existing[1:4] != (summary_id, actor.id, request.creation_rationale):
                        raise ProposalIdempotencyConflictError
                    return await self._response(cursor, existing[0])
                await cursor.execute(
                    "SELECT 1 FROM prepared_post_inspection_proposal WHERE summary_id = %s",
                    (summary_id,),
                )
                if await cursor.fetchone():
                    raise ProposalAlreadyExistsError
                return await self._insert(cursor, summary_id, actor, key_hash, request)
        except UniqueViolation as error:
            if error.diag.constraint_name == "prepared_post_inspection_proposal_summary_id_key":
                raise ProposalAlreadyExistsError from None
            raise

    async def _insert(self, cursor, summary_id, actor, key_hash, request):
        await cursor.execute(
            """
            SELECT summary.maximum_height_cm, zone.zone_type, axis.road_id
            FROM prepared_inspection_summary summary
            JOIN work_order order_record ON order_record.id = summary.work_order_id
            JOIN segment_zone zone ON zone.id = order_record.segment_zone_id
            JOIN road_segment segment ON segment.id = zone.road_segment_id
            JOIN road_axis_candidate axis ON axis.id = segment.road_axis_candidate_id
            WHERE summary.id = %s AND summary.location_status = 'simulated'
              AND summary.data_status = 'prepared'
              AND NOT summary.eligible_for_official_reporting
              AND NOT summary.authorizes_field_work
            """,
            (summary_id,),
        )
        target = await cursor.fetchone()
        if not target:
            raise ProposalNotFoundError
        await cursor.execute(
            """SELECT id, allowed_roles, general_threshold_cm, special_threshold_cm
               FROM prepared_post_inspection_policy
               WHERE version = %s AND data_status = 'prepared'
                 AND requires_human_review AND NOT authorizes_field_work""",
            (self._policy_version,),
        )
        policy = await cursor.fetchone()
        if not policy:
            raise ProposalPolicyUnavailableError
        await cursor.execute(
            """SELECT 1 FROM road_user_role WHERE user_id = %s AND road_id = %s
               AND role = ANY(%s) AND data_status <> 'simulated' LIMIT 1""",
            (actor.id, target[2], policy[1]),
        )
        if not await cursor.fetchone():
            raise ProposalPermissionError
        threshold = policy[3] if target[1] == "special" else policy[2]
        exceeded = target[0] > threshold
        recommendation = "mowing_review" if exceeded else "monitor"
        await cursor.execute(
            """
            INSERT INTO prepared_post_inspection_proposal (
                summary_id, created_by_user_id, policy_id, idempotency_key,
                creation_rationale, recommendation, applicable_threshold_cm,
                maximum_height_cm, threshold_exceeded, requires_human_review,
                location_status, evidence_status, data_status,
                eligible_for_model_training, eligible_for_official_reporting,
                authorizes_field_work)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, true, 'simulated',
                    'prepared_reviewed_non_operational', 'prepared', false, false, false)
            ON CONFLICT (idempotency_key) DO NOTHING
            RETURNING id
            """,
            (
                summary_id, actor.id, policy[0], key_hash, request.creation_rationale,
                recommendation, threshold, target[0], exceeded,
            ),
        )
        inserted = await cursor.fetchone()
        if inserted is None:
            existing = await self._by_key(cursor, key_hash)
            if existing is None:
                raise ProposalIdempotencyConflictError
            if existing[1:4] != (summary_id, actor.id, request.creation_rationale):
                raise ProposalIdempotencyConflictError
            return await self._response(cursor, existing[0])
        return await self._response(cursor, inserted[0])

    async def list_for_actor(
        self, *, actor: AuthenticatedUser, limit: int
    ) -> PreparedProposalCollection:
        connection = await psycopg.AsyncConnection.connect(self._database_url)
        async with connection, connection.cursor() as cursor:
            await cursor.execute(
                self._response_query(
                    """EXISTS (SELECT 1 FROM road_user_role assignment
                        WHERE assignment.user_id = %s AND assignment.road_id = road.id
                          AND assignment.role IN ('manager', 'supervisor')
                          AND assignment.data_status <> 'simulated')
                        ORDER BY proposal.created_at DESC, proposal.id LIMIT %s"""
                ),
                (actor.id, limit + 1),
            )
            rows = await cursor.fetchall()
        truncated = len(rows) > limit
        visible = rows[:limit]
        return PreparedProposalCollection(
            items=[self._from_row(row) for row in visible],
            result_count=len(visible), limit=limit, truncated=truncated,
        )

    async def _by_key(self, cursor, key_hash):
        await cursor.execute(
            """SELECT id, summary_id, created_by_user_id, creation_rationale
               FROM prepared_post_inspection_proposal WHERE idempotency_key = %s""",
            (key_hash,),
        )
        return await cursor.fetchone()

    async def _response(self, cursor, proposal_id):
        await cursor.execute(self._response_query("proposal.id = %s"), (proposal_id,))
        return self._from_row(await cursor.fetchone())

    @staticmethod
    def _response_query(where_clause: str) -> str:
        return f"""SELECT proposal.id, proposal.summary_id, summary.work_order_id,
                   road.code, segment.segment_index, zone.zone_type, policy.version,
                   proposal.creation_rationale, proposal.recommendation,
                   proposal.applicable_threshold_cm, proposal.maximum_height_cm,
                   proposal.threshold_exceeded, proposal.created_at
            FROM prepared_post_inspection_proposal proposal
            JOIN prepared_post_inspection_policy policy ON policy.id = proposal.policy_id
            JOIN prepared_inspection_summary summary ON summary.id = proposal.summary_id
            JOIN work_order order_record ON order_record.id = summary.work_order_id
            JOIN segment_zone zone ON zone.id = order_record.segment_zone_id
            JOIN road_segment segment ON segment.id = zone.road_segment_id
            JOIN road_axis_candidate axis ON axis.id = segment.road_axis_candidate_id
            JOIN road ON road.id = axis.road_id
            WHERE proposal.location_status = 'simulated' AND proposal.data_status = 'prepared'
              AND NOT proposal.eligible_for_official_reporting
              AND NOT proposal.authorizes_field_work AND {where_clause}"""

    @staticmethod
    def _from_row(row: tuple) -> PreparedProposalResponse:
        return PreparedProposalResponse(
            proposal_id=row[0], summary_id=row[1], work_order_id=row[2], road_code=row[3],
            segment_index=row[4], zone_type=row[5], policy_version=row[6],
            creation_rationale=row[7], recommendation=row[8],
            applicable_threshold_cm=row[9], maximum_height_cm=row[10],
            threshold_exceeded=row[11], created_at=row[12],
        )


async def get_prepared_proposal_repository():
    settings = get_settings()
    return PostgresPreparedProposalRepository(
        settings.database_url, settings.prepared_post_inspection_policy_version
    )


summary_router = APIRouter(prefix="/v1/prepared-inspection-summaries", tags=["work-orders"])
collection_router = APIRouter(prefix="/v1/prepared-post-inspection-proposals", tags=["work-orders"])


@summary_router.post(
    "/{summary_id}/post-inspection-proposal", response_model=PreparedProposalResponse
)
async def create_prepared_proposal(
    summary_id: UUID,
    request: PreparedProposalRequest,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=8, max_length=200)],
    actor: Annotated[AuthenticatedUser, Depends(get_current_user)],
    writer: Annotated[PreparedProposalWriter, Depends(get_prepared_proposal_repository)],
) -> PreparedProposalResponse:
    try:
        return await writer.create(
            summary_id=summary_id, actor=actor, idempotency_key=idempotency_key, request=request
        )
    except ProposalNotFoundError:
        raise HTTPException(404, "Prepared summary not found") from None
    except ProposalPermissionError:
        raise HTTPException(403, "User cannot create a proposal for this road") from None
    except ProposalPolicyUnavailableError:
        raise HTTPException(503, "Prepared proposal policy unavailable") from None
    except ProposalIdempotencyConflictError:
        raise HTTPException(409, "Idempotency-Key conflict") from None
    except ProposalAlreadyExistsError:
        raise HTTPException(409, "Prepared proposal already exists") from None


@collection_router.get("", response_model=PreparedProposalCollection)
async def list_prepared_proposals(
    actor: Annotated[AuthenticatedUser, Depends(get_current_user)],
    reader: Annotated[PreparedProposalReader, Depends(get_prepared_proposal_repository)],
    limit: Annotated[int, Field(ge=1, le=100)] = 50,
) -> PreparedProposalCollection:
    return await reader.list_for_actor(actor=actor, limit=limit)
