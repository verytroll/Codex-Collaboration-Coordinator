"""Session template API routes."""

from __future__ import annotations

from typing import Annotated, cast

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_session_template_service
from app.models.api.session_templates import (
    SessionTemplateCreateRequest,
    SessionTemplateEnvelope,
    SessionTemplateInstantiateEnvelope,
    SessionTemplateInstantiateRequest,
    SessionTemplateListEnvelope,
    SessionTemplateResponse,
)
from app.models.api.sessions import SessionResponse, SessionStatus
from app.repositories.sessions import SessionRecord
from app.services.session_template_service import SessionTemplateDefinition, SessionTemplateService

router = APIRouter(prefix="/api/v1", tags=["session-templates"])


def _session_response(record: SessionRecord) -> SessionResponse:
    return SessionResponse(
        id=record.id,
        title=record.title,
        goal=record.goal,
        status=cast(SessionStatus, record.status),
        lead_agent_id=record.lead_agent_id,
        active_phase_id=record.active_phase_id,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _template_response(template: SessionTemplateDefinition) -> SessionTemplateResponse:
    return SessionTemplateResponse(
        id=template.id,
        template_key=template.template_key,
        title=template.title,
        description=template.description,
        default_goal=template.default_goal,
        participant_roles=list(template.participant_roles),
        channels=list(template.channels),
        phase_order=list(template.phase_order),
        rule_presets=list(template.rule_presets),
        orchestration=template.orchestration,
        is_default=template.is_default,
        sort_order=template.sort_order,
        created_at=template.created_at,
        updated_at=template.updated_at,
    )


@router.get("/session-templates", response_model=SessionTemplateListEnvelope)
async def list_session_templates(
    session_template_service: Annotated[
        SessionTemplateService,
        Depends(get_session_template_service),
    ],
) -> SessionTemplateListEnvelope:
    templates = await session_template_service.list_templates()
    return SessionTemplateListEnvelope(
        templates=[_template_response(template) for template in templates]
    )


@router.post(
    "/session-templates",
    response_model=SessionTemplateEnvelope,
    status_code=status.HTTP_201_CREATED,
)
async def create_session_template(
    payload: SessionTemplateCreateRequest,
    session_template_service: Annotated[
        SessionTemplateService,
        Depends(get_session_template_service),
    ],
) -> SessionTemplateEnvelope:
    try:
        template = await session_template_service.create_template(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return SessionTemplateEnvelope(template=_template_response(template))


@router.get("/session-templates/{template_key}", response_model=SessionTemplateEnvelope)
async def get_session_template(
    template_key: str,
    session_template_service: Annotated[
        SessionTemplateService,
        Depends(get_session_template_service),
    ],
) -> SessionTemplateEnvelope:
    try:
        template = await session_template_service.get_template(template_key)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return SessionTemplateEnvelope(template=_template_response(template))


@router.post(
    "/session-templates/{template_key}/instantiate",
    response_model=SessionTemplateInstantiateEnvelope,
    status_code=status.HTTP_201_CREATED,
)
async def instantiate_session_template(
    template_key: str,
    payload: SessionTemplateInstantiateRequest,
    session_template_service: Annotated[
        SessionTemplateService,
        Depends(get_session_template_service),
    ],
) -> SessionTemplateInstantiateEnvelope:
    try:
        session = await session_template_service.instantiate_session(
            template_key,
            title=payload.title,
            goal=payload.goal,
            lead_agent_id=payload.lead_agent_id,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return SessionTemplateInstantiateEnvelope(session=_session_response(session))
