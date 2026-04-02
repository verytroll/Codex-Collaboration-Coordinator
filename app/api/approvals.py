"""Approval API routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import (
    get_approval_manager,
    get_approval_repository,
    get_authz_service,
    get_phase_gate_service,
    get_review_actor_identity,
)
from app.models.api.jobs import ApprovalDecisionRequest, ApprovalRequestResponse
from app.repositories.approvals import ApprovalRepository
from app.services.approval_manager import ApprovalManager
from app.services.authz_service import ActorIdentity, AuthzService
from app.services.phase_gate_service import PhaseGateService

router = APIRouter(prefix="/api/v1", tags=["approvals"])


def _approval_response(approval) -> ApprovalRequestResponse:
    from app.api.jobs import _approval_response as _job_approval_response

    return _job_approval_response(approval)


@router.post("/approvals/{approval_id}/accept", response_model=ApprovalRequestResponse)
async def accept_approval(
    approval_id: str,
    approval_repository: Annotated[ApprovalRepository, Depends(get_approval_repository)],
    approval_manager: Annotated[ApprovalManager, Depends(get_approval_manager)],
    phase_gate_service: Annotated[PhaseGateService, Depends(get_phase_gate_service)],
    authz_service: Annotated[AuthzService, Depends(get_authz_service)],
    actor_identity: Annotated[ActorIdentity, Depends(get_review_actor_identity)],
    payload: ApprovalDecisionRequest | None = None,
) -> ApprovalRequestResponse:
    authz_service.require_approval_action(actor_identity, action="accept")
    approval = await approval_repository.get(approval_id)
    if approval is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Approval request not found: {approval_id}",
        )
    try:
        decision = await approval_manager.accept(
            approval_id,
            decision_payload=payload.decision_payload if payload else None,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    await phase_gate_service.resolve_approval_decision(
        decision,
        decision_payload=payload.decision_payload if payload else None,
    )
    return _approval_response(decision.approval)


@router.post("/approvals/{approval_id}/decline", response_model=ApprovalRequestResponse)
async def decline_approval(
    approval_id: str,
    approval_repository: Annotated[ApprovalRepository, Depends(get_approval_repository)],
    approval_manager: Annotated[ApprovalManager, Depends(get_approval_manager)],
    phase_gate_service: Annotated[PhaseGateService, Depends(get_phase_gate_service)],
    authz_service: Annotated[AuthzService, Depends(get_authz_service)],
    actor_identity: Annotated[ActorIdentity, Depends(get_review_actor_identity)],
    payload: ApprovalDecisionRequest | None = None,
) -> ApprovalRequestResponse:
    authz_service.require_approval_action(actor_identity, action="decline")
    approval = await approval_repository.get(approval_id)
    if approval is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Approval request not found: {approval_id}",
        )
    try:
        decision = await approval_manager.decline(
            approval_id,
            decision_payload=payload.decision_payload if payload else None,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    await phase_gate_service.resolve_approval_decision(
        decision,
        decision_payload=payload.decision_payload if payload else None,
    )
    return _approval_response(decision.approval)
