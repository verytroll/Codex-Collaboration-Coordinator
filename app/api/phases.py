"""Session phase API routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_phase_service, get_session_repository
from app.models.api.phases import (
    PhaseEnvelope,
    PhaseListEnvelope,
    PhasePresetListEnvelope,
    PhasePresetResponse,
    PhaseResponse,
)
from app.repositories.sessions import SessionRepository
from app.services.phase_service import PhaseService

router = APIRouter(prefix="/api/v1", tags=["phases"])


def _phase_response(phase, *, active_phase_id: str | None) -> PhaseResponse:
    return PhaseResponse(
        id=phase.id,
        session_id=phase.session_id,
        phase_key=phase.phase_key,
        title=phase.title,
        description=phase.description,
        relay_template_key=phase.relay_template_key,
        default_channel_key=phase.default_channel_key,
        sort_order=phase.sort_order,
        is_default=bool(phase.is_default),
        is_active=phase.id == active_phase_id,
        created_at=phase.created_at,
        updated_at=phase.updated_at,
    )


def _preset_response(preset) -> PhasePresetResponse:
    return PhasePresetResponse(
        phase_key=preset.phase_key,
        title=preset.title,
        description=preset.description,
        relay_template_key=preset.relay_template_key,
        default_channel_key=preset.default_channel_key,
        sort_order=preset.sort_order,
        is_default=preset.is_default,
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


@router.get("/phases/presets", response_model=PhasePresetListEnvelope)
async def list_phase_presets(
    phase_service: Annotated[PhaseService, Depends(get_phase_service)],
) -> PhasePresetListEnvelope:
    return PhasePresetListEnvelope(
        presets=[_preset_response(preset) for preset in phase_service.list_presets()]
    )


@router.get("/sessions/{session_id}/phases", response_model=PhaseListEnvelope)
async def list_session_phases(
    session_id: str,
    session_repository: Annotated[SessionRepository, Depends(get_session_repository)],
    phase_service: Annotated[PhaseService, Depends(get_phase_service)],
) -> PhaseListEnvelope:
    await _ensure_session_exists(session_repository, session_id)
    phases = await phase_service.list_phases(session_id)
    session = await session_repository.get(session_id)
    active_phase_id = session.active_phase_id if session is not None else None
    return PhaseListEnvelope(
        phases=[_phase_response(phase, active_phase_id=active_phase_id) for phase in phases]
    )


@router.post(
    "/sessions/{session_id}/phases/{phase_key}/activate",
    response_model=PhaseEnvelope,
)
async def activate_phase(
    session_id: str,
    phase_key: str,
    session_repository: Annotated[SessionRepository, Depends(get_session_repository)],
    phase_service: Annotated[PhaseService, Depends(get_phase_service)],
) -> PhaseEnvelope:
    await _ensure_session_exists(session_repository, session_id)
    try:
        result = await phase_service.activate_phase_by_key(session_id, phase_key)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return PhaseEnvelope(
        phase=_phase_response(result.phase, active_phase_id=result.session.active_phase_id)
    )
