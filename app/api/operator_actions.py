"""Operator action write routes."""

from __future__ import annotations

import json
from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import get_operator_action_service
from app.models.api.jobs import ApprovalRequestResponse, JobResponse
from app.models.api.operator_actions import (
    OperatorActionAuditResponse,
    OperatorActionEnvelope,
    OperatorActionRequest,
    OperatorActionResponse,
)
from app.models.api.phases import PhaseResponse
from app.services.operator_actions import OperatorActionService

router = APIRouter(prefix="/api/v1/operator", tags=["operator"])


def _parse_json(payload: str | None) -> dict[str, object] | None:
    if payload is None:
        return None
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return {"raw": payload}
    return data if isinstance(data, dict) else {"value": data}


def _build_response(result) -> OperatorActionEnvelope:
    return OperatorActionEnvelope(
        action=OperatorActionResponse(
            action=result.action,
            outcome=result.outcome,
            session_id=result.session_id,
            target_type=result.target_type,
            target_id=result.target_id,
            target_state_before=result.target_state_before,
            target_state_after=result.target_state_after,
            message=result.message,
            audit=OperatorActionAuditResponse(
                event_id=result.audit.event_id,
                event_type=result.audit.event_type,
                actor_type=result.audit.actor_type,
                actor_id=result.audit.actor_id,
                session_id=result.audit.session_id,
                target_type=result.audit.target_type,
                target_id=result.audit.target_id,
                result=result.audit.result,
                reason=result.audit.reason,
                note=result.audit.note,
                failure_mode=result.audit.failure_mode,
                detail=result.audit.detail,
                created_at=result.audit.created_at,
            ),
            job=(
                None
                if result.job is None
                else JobResponse.model_validate(result.job, from_attributes=True)
            ),
            approval=(
                None
                if result.approval is None
                else ApprovalRequestResponse(
                    id=result.approval.id,
                    job_id=result.approval.job_id,
                    agent_id=result.approval.agent_id,
                    approval_type=result.approval.approval_type,
                    status=result.approval.status,
                    request_payload=_parse_json(result.approval.request_payload_json) or {},
                    decision_payload=_parse_json(result.approval.decision_payload_json),
                    requested_at=result.approval.requested_at,
                    resolved_at=result.approval.resolved_at,
                    created_at=result.approval.created_at,
                    updated_at=result.approval.updated_at,
                )
            ),
            phase=(
                None
                if result.phase is None
                else PhaseResponse(
                    id=result.phase.id,
                    session_id=result.phase.session_id,
                    phase_key=result.phase.phase_key,
                    title=result.phase.title,
                    description=result.phase.description,
                    relay_template_key=result.phase.relay_template_key,
                    default_channel_key=result.phase.default_channel_key,
                    sort_order=result.phase.sort_order,
                    is_default=bool(result.phase.is_default),
                    is_active=True,
                    created_at=result.phase.created_at,
                    updated_at=result.phase.updated_at,
                )
            ),
        )
    )


@router.post("/jobs/{job_id}/retry", response_model=OperatorActionEnvelope)
async def retry_job(
    job_id: str,
    action_service: Annotated[OperatorActionService, Depends(get_operator_action_service)],
    payload: OperatorActionRequest | None = None,
) -> OperatorActionEnvelope:
    return _build_response(
        await action_service.retry_job(
            job_id,
            actor_id=payload.actor_id if payload is not None else None,
            reason=payload.reason if payload is not None else None,
            note=payload.note if payload is not None else None,
            context=payload.context if payload is not None else None,
        )
    )


@router.post("/jobs/{job_id}/resume", response_model=OperatorActionEnvelope)
async def resume_job(
    job_id: str,
    action_service: Annotated[OperatorActionService, Depends(get_operator_action_service)],
    payload: OperatorActionRequest | None = None,
) -> OperatorActionEnvelope:
    return _build_response(
        await action_service.resume_job(
            job_id,
            actor_id=payload.actor_id if payload is not None else None,
            reason=payload.reason if payload is not None else None,
            note=payload.note if payload is not None else None,
            context=payload.context if payload is not None else None,
        )
    )


@router.post("/jobs/{job_id}/cancel", response_model=OperatorActionEnvelope)
async def cancel_job(
    job_id: str,
    action_service: Annotated[OperatorActionService, Depends(get_operator_action_service)],
    payload: OperatorActionRequest | None = None,
) -> OperatorActionEnvelope:
    return _build_response(
        await action_service.cancel_job(
            job_id,
            actor_id=payload.actor_id if payload is not None else None,
            reason=payload.reason if payload is not None else None,
            note=payload.note if payload is not None else None,
            context=payload.context if payload is not None else None,
        )
    )


@router.post("/approvals/{approval_id}/approve", response_model=OperatorActionEnvelope)
async def approve_approval(
    approval_id: str,
    action_service: Annotated[OperatorActionService, Depends(get_operator_action_service)],
    payload: OperatorActionRequest | None = None,
) -> OperatorActionEnvelope:
    return _build_response(
        await action_service.approve_approval(
            approval_id,
            actor_id=payload.actor_id if payload is not None else None,
            reason=payload.reason if payload is not None else None,
            note=payload.note if payload is not None else None,
            context=payload.context if payload is not None else None,
        )
    )


@router.post("/approvals/{approval_id}/reject", response_model=OperatorActionEnvelope)
async def reject_approval(
    approval_id: str,
    action_service: Annotated[OperatorActionService, Depends(get_operator_action_service)],
    payload: OperatorActionRequest | None = None,
) -> OperatorActionEnvelope:
    return _build_response(
        await action_service.reject_approval(
            approval_id,
            actor_id=payload.actor_id if payload is not None else None,
            reason=payload.reason if payload is not None else None,
            note=payload.note if payload is not None else None,
            context=payload.context if payload is not None else None,
        )
    )


@router.post(
    "/sessions/{session_id}/phases/{phase_key}/activate",
    response_model=OperatorActionEnvelope,
)
async def activate_phase(
    session_id: str,
    phase_key: str,
    action_service: Annotated[OperatorActionService, Depends(get_operator_action_service)],
    payload: OperatorActionRequest | None = None,
) -> OperatorActionEnvelope:
    return _build_response(
        await action_service.activate_phase(
            session_id,
            phase_key,
            actor_id=payload.actor_id if payload is not None else None,
            reason=payload.reason if payload is not None else None,
            note=payload.note if payload is not None else None,
            context=payload.context if payload is not None else None,
        )
    )
