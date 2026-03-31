"""Collaboration rules API routes."""

from __future__ import annotations

import json
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_rule_engine_service, get_session_repository
from app.models.api.rules import RuleCreateRequest, RuleEnvelope, RuleListEnvelope, RuleResponse
from app.repositories.rules import RuleRecord
from app.repositories.sessions import SessionRepository
from app.services.rule_engine import RuleEngineService

router = APIRouter(prefix="/api/v1", tags=["rules"])


def _parse_json(payload: str | None) -> dict[str, Any] | None:
    if payload is None:
        return None
    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _rule_response(record: RuleRecord) -> RuleResponse:
    return RuleResponse(
        id=record.id,
        session_id=record.session_id,
        rule_type=record.rule_type,  # type: ignore[arg-type]
        name=record.name,
        description=record.description,
        is_active=bool(record.is_active),
        priority=record.priority,
        conditions=_parse_json(record.conditions_json),
        actions=_parse_json(record.actions_json),
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


async def _ensure_session_exists(
    session_repository: SessionRepository,
    session_id: str,
) -> None:
    if await session_repository.get(session_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session not found: {session_id}",
        )


async def _ensure_rule_in_session(
    rule_engine_service: RuleEngineService,
    *,
    session_id: str,
    rule_id: str,
) -> RuleRecord:
    rule = await rule_engine_service.get_rule(rule_id)
    if rule is None or rule.session_id != session_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule not found in session {session_id}: {rule_id}",
        )
    return rule


@router.get("/sessions/{session_id}/rules", response_model=RuleListEnvelope)
async def list_rules(
    session_id: str,
    session_repository: Annotated[SessionRepository, Depends(get_session_repository)],
    rule_engine_service: Annotated[RuleEngineService, Depends(get_rule_engine_service)],
) -> RuleListEnvelope:
    await _ensure_session_exists(session_repository, session_id)
    return RuleListEnvelope(
        rules=[_rule_response(rule) for rule in await rule_engine_service.list_rules(session_id)]
    )


@router.post("/sessions/{session_id}/rules", response_model=RuleEnvelope, status_code=status.HTTP_201_CREATED)
async def create_rule(
    session_id: str,
    payload: RuleCreateRequest,
    session_repository: Annotated[SessionRepository, Depends(get_session_repository)],
    rule_engine_service: Annotated[RuleEngineService, Depends(get_rule_engine_service)],
) -> RuleEnvelope:
    await _ensure_session_exists(session_repository, session_id)
    try:
        rule = await rule_engine_service.create_rule(
            session_id=session_id,
            rule_type=payload.rule_type,
            name=payload.name,
            description=payload.description,
            priority=payload.priority,
            is_active=payload.is_active,
            conditions=payload.conditions,
            actions=payload.actions,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return RuleEnvelope(rule=_rule_response(rule))


@router.post("/sessions/{session_id}/rules/{rule_id}/activate", response_model=RuleEnvelope)
async def activate_rule(
    session_id: str,
    rule_id: str,
    session_repository: Annotated[SessionRepository, Depends(get_session_repository)],
    rule_engine_service: Annotated[RuleEngineService, Depends(get_rule_engine_service)],
) -> RuleEnvelope:
    await _ensure_session_exists(session_repository, session_id)
    await _ensure_rule_in_session(rule_engine_service, session_id=session_id, rule_id=rule_id)
    try:
        rule = await rule_engine_service.activate_rule(rule_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return RuleEnvelope(rule=_rule_response(rule))


@router.post("/sessions/{session_id}/rules/{rule_id}/deactivate", response_model=RuleEnvelope)
async def deactivate_rule(
    session_id: str,
    rule_id: str,
    session_repository: Annotated[SessionRepository, Depends(get_session_repository)],
    rule_engine_service: Annotated[RuleEngineService, Depends(get_rule_engine_service)],
) -> RuleEnvelope:
    await _ensure_session_exists(session_repository, session_id)
    await _ensure_rule_in_session(rule_engine_service, session_id=session_id, rule_id=rule_id)
    try:
        rule = await rule_engine_service.deactivate_rule(rule_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return RuleEnvelope(rule=_rule_response(rule))
