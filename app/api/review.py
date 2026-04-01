"""Review mode and structured relay template API routes."""

from __future__ import annotations

import json
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_job_repository, get_review_mode_service, get_session_repository
from app.models.api.review import (
    RelayTemplateEnvelope,
    RelayTemplateListEnvelope,
    RelayTemplateResponse,
    ReviewCreateRequest,
    ReviewDecisionRequest,
    ReviewEnvelope,
    ReviewListEnvelope,
    ReviewResponse,
)
from app.repositories.jobs import JobRepository
from app.repositories.sessions import SessionRepository
from app.services.review_mode import ReviewModeService

router = APIRouter(prefix="/api/v1", tags=["review"])


def _parse_json(payload: str | None) -> dict[str, Any] | None:
    if payload is None:
        return None
    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _review_response(review) -> ReviewResponse:
    return ReviewResponse(
        id=review.id,
        session_id=review.session_id,
        source_job_id=review.source_job_id,
        reviewer_agent_id=review.reviewer_agent_id,
        requested_by_agent_id=review.requested_by_agent_id,
        review_scope=review.review_scope,  # type: ignore[arg-type]
        review_status=review.review_status,  # type: ignore[arg-type]
        review_channel_key=review.review_channel_key,
        template_key=review.template_key,
        request_message_id=review.request_message_id,
        decision_message_id=review.decision_message_id,
        summary_artifact_id=review.summary_artifact_id,
        revision_job_id=review.revision_job_id,
        request_payload=_parse_json(review.request_payload_json),
        decision_payload=_parse_json(review.decision_payload_json),
        requested_at=review.requested_at,
        decided_at=review.decided_at,
        created_at=review.created_at,
        updated_at=review.updated_at,
    )


def _template_response(template) -> RelayTemplateResponse:
    return RelayTemplateResponse(
        template_key=template.template_key,
        title=template.title,
        source_role=template.source_role,
        target_role=template.target_role,
        description=template.description,
        default_channel_key=template.default_channel_key,
        section_keys=list(template.section_keys),
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


@router.get("/review/templates", response_model=RelayTemplateListEnvelope)
async def list_templates(
    review_mode_service: Annotated[ReviewModeService, Depends(get_review_mode_service)],
) -> RelayTemplateListEnvelope:
    return RelayTemplateListEnvelope(
        templates=[
            _template_response(template) for template in await review_mode_service.list_templates()
        ]
    )


@router.get("/review/templates/{template_key}", response_model=RelayTemplateEnvelope)
async def get_template(
    template_key: str,
    review_mode_service: Annotated[ReviewModeService, Depends(get_review_mode_service)],
) -> RelayTemplateEnvelope:
    try:
        template = await review_mode_service.get_template(template_key)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return RelayTemplateEnvelope(template=_template_response(template))


@router.get("/sessions/{session_id}/reviews", response_model=ReviewListEnvelope)
async def list_reviews(
    session_id: str,
    session_repository: Annotated[SessionRepository, Depends(get_session_repository)],
    review_mode_service: Annotated[ReviewModeService, Depends(get_review_mode_service)],
) -> ReviewListEnvelope:
    await _ensure_session_exists(session_repository, session_id)
    return ReviewListEnvelope(
        reviews=[
            _review_response(review)
            for review in await review_mode_service.list_reviews(session_id)
        ]
    )


@router.post(
    "/sessions/{session_id}/reviews",
    response_model=ReviewEnvelope,
    status_code=status.HTTP_201_CREATED,
)
async def create_review(
    session_id: str,
    payload: ReviewCreateRequest,
    session_repository: Annotated[SessionRepository, Depends(get_session_repository)],
    job_repository: Annotated[JobRepository, Depends(get_job_repository)],
    review_mode_service: Annotated[ReviewModeService, Depends(get_review_mode_service)],
) -> ReviewEnvelope:
    await _ensure_session_exists(session_repository, session_id)
    job = await job_repository.get(payload.source_job_id)
    if job is None or job.session_id != session_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job not found in session {session_id}: {payload.source_job_id}",
        )
    try:
        result = await review_mode_service.request_review(
            source_job_id=payload.source_job_id,
            reviewer_agent_id=payload.reviewer_agent_id,
            review_scope=payload.review_scope,
            review_channel_key=payload.review_channel_key,
            notes=payload.notes,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return ReviewEnvelope(review=_review_response(result.review))


@router.get("/reviews/{review_id}", response_model=ReviewEnvelope)
async def get_review(
    review_id: str,
    review_mode_service: Annotated[ReviewModeService, Depends(get_review_mode_service)],
) -> ReviewEnvelope:
    review = await review_mode_service.get_review(review_id)
    if review is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Review not found: {review_id}",
        )
    return ReviewEnvelope(review=_review_response(review))


@router.post("/reviews/{review_id}/decision", response_model=ReviewEnvelope)
async def submit_review_decision(
    review_id: str,
    payload: ReviewDecisionRequest,
    review_mode_service: Annotated[ReviewModeService, Depends(get_review_mode_service)],
) -> ReviewEnvelope:
    try:
        result = await review_mode_service.submit_decision(
            review_id=review_id,
            decision=payload.decision,
            summary=payload.summary,
            required_changes=payload.required_changes,
            notes=payload.notes,
            revision_priority=payload.revision_priority,
            revision_instructions=payload.revision_instructions,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return ReviewEnvelope(review=_review_response(result.review))
