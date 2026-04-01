"""Advanced policy API routes."""

from __future__ import annotations

import json
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_policy_engine_v2_service
from app.models.api.policies import (
    PolicyControlRequest,
    PolicyCreateRequest,
    PolicyDecisionListEnvelope,
    PolicyDecisionResponse,
    PolicyEnvelope,
    PolicyListEnvelope,
    PolicyResponse,
)
from app.repositories.policies import PolicyDecisionRecord, PolicyRecord
from app.services.policy_engine_v2 import PolicyEngineV2Service

router = APIRouter(prefix="/api/v1", tags=["policies"])


def _parse_json(payload: str | None) -> dict[str, Any] | None:
    if payload is None:
        return None
    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _policy_response(policy: PolicyRecord) -> PolicyResponse:
    return PolicyResponse(
        id=policy.id,
        session_id=policy.session_id,
        template_key=policy.template_key,
        phase_key=policy.phase_key,
        policy_type=policy.policy_type,  # type: ignore[arg-type]
        name=policy.name,
        description=policy.description,
        is_active=bool(policy.is_active),
        automation_paused=bool(policy.automation_paused),
        pause_reason=policy.pause_reason,
        priority=policy.priority,
        conditions=_parse_json(policy.conditions_json),
        actions=_parse_json(policy.actions_json),
        created_at=policy.created_at,
        updated_at=policy.updated_at,
    )


def _decision_response(decision: PolicyDecisionRecord) -> PolicyDecisionResponse:
    context = _parse_json(decision.context_json) or {}
    return PolicyDecisionResponse(
        id=decision.id,
        policy_id=decision.policy_id,
        session_id=decision.session_id,
        subject_type=decision.subject_type,  # type: ignore[arg-type]
        subject_id=decision.subject_id,
        gate_type=decision.gate_type,  # type: ignore[arg-type]
        decision=decision.decision,  # type: ignore[arg-type]
        matched=bool(decision.matched),
        reason=decision.reason,
        context=context,
        created_at=decision.created_at,
    )


@router.get("/policies", response_model=PolicyListEnvelope)
async def list_policies(
    policy_engine: Annotated[PolicyEngineV2Service, Depends(get_policy_engine_v2_service)],
    session_id: str | None = None,
    template_key: str | None = None,
    phase_key: str | None = None,
) -> PolicyListEnvelope:
    policies = await policy_engine.list_policies(
        session_id=session_id,
        template_key=template_key,
        phase_key=phase_key,
    )
    return PolicyListEnvelope(policies=[_policy_response(policy) for policy in policies])


@router.post("/policies", response_model=PolicyEnvelope, status_code=status.HTTP_201_CREATED)
async def create_policy(
    payload: PolicyCreateRequest,
    policy_engine: Annotated[PolicyEngineV2Service, Depends(get_policy_engine_v2_service)],
) -> PolicyEnvelope:
    try:
        policy = await policy_engine.create_policy(
            session_id=payload.session_id,
            template_key=payload.template_key,
            phase_key=payload.phase_key,
            policy_type=payload.policy_type,
            name=payload.name,
            description=payload.description,
            is_active=payload.is_active,
            automation_paused=payload.automation_paused,
            pause_reason=payload.pause_reason,
            priority=payload.priority,
            conditions=payload.conditions,
            actions=payload.actions,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return PolicyEnvelope(policy=_policy_response(policy))


@router.get("/policies/{policy_id}", response_model=PolicyEnvelope)
async def get_policy(
    policy_id: str,
    policy_engine: Annotated[PolicyEngineV2Service, Depends(get_policy_engine_v2_service)],
) -> PolicyEnvelope:
    policy = await policy_engine.get_policy(policy_id)
    if policy is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy not found: {policy_id}",
        )
    return PolicyEnvelope(policy=_policy_response(policy))


@router.post("/policies/{policy_id}/activate", response_model=PolicyEnvelope)
async def activate_policy(
    policy_id: str,
    policy_engine: Annotated[PolicyEngineV2Service, Depends(get_policy_engine_v2_service)],
) -> PolicyEnvelope:
    try:
        policy = await policy_engine.activate_policy(policy_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return PolicyEnvelope(policy=_policy_response(policy))


@router.post("/policies/{policy_id}/deactivate", response_model=PolicyEnvelope)
async def deactivate_policy(
    policy_id: str,
    policy_engine: Annotated[PolicyEngineV2Service, Depends(get_policy_engine_v2_service)],
) -> PolicyEnvelope:
    try:
        policy = await policy_engine.deactivate_policy(policy_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return PolicyEnvelope(policy=_policy_response(policy))


@router.post("/policies/{policy_id}/pause", response_model=PolicyEnvelope)
async def pause_policy(
    policy_id: str,
    policy_engine: Annotated[PolicyEngineV2Service, Depends(get_policy_engine_v2_service)],
    payload: PolicyControlRequest | None = None,
) -> PolicyEnvelope:
    try:
        policy = await policy_engine.pause_automation(
            policy_id,
            reason=payload.reason if payload is not None else None,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return PolicyEnvelope(policy=_policy_response(policy))


@router.post("/policies/{policy_id}/resume", response_model=PolicyEnvelope)
async def resume_policy(
    policy_id: str,
    policy_engine: Annotated[PolicyEngineV2Service, Depends(get_policy_engine_v2_service)],
    payload: PolicyControlRequest | None = None,
) -> PolicyEnvelope:
    try:
        policy = await policy_engine.resume_automation(
            policy_id,
            reason=payload.reason if payload is not None else None,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return PolicyEnvelope(policy=_policy_response(policy))


@router.get("/policies/{policy_id}/decisions", response_model=PolicyDecisionListEnvelope)
async def list_policy_decisions(
    policy_id: str,
    policy_engine: Annotated[PolicyEngineV2Service, Depends(get_policy_engine_v2_service)],
) -> PolicyDecisionListEnvelope:
    decisions = await policy_engine.list_decisions(policy_id=policy_id)
    return PolicyDecisionListEnvelope(
        decisions=[_decision_response(decision) for decision in decisions]
    )


@router.get("/policy-decisions", response_model=PolicyDecisionListEnvelope)
async def list_policy_decisions_for_session(
    policy_engine: Annotated[PolicyEngineV2Service, Depends(get_policy_engine_v2_service)],
    session_id: str | None = None,
) -> PolicyDecisionListEnvelope:
    decisions = await policy_engine.list_decisions(session_id=session_id)
    return PolicyDecisionListEnvelope(
        decisions=[_decision_response(decision) for decision in decisions]
    )
