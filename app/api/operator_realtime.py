"""Realtime operator activity routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import get_operator_realtime_service
from app.models.api.operator_realtime import OperatorSessionActivityResponse
from app.services.operator_realtime import OperatorRealtimeService

router = APIRouter(prefix="/api/v1/operator", tags=["operator-ui"])


@router.get("/sessions/{session_id}/activity", response_model=OperatorSessionActivityResponse)
async def get_session_activity(
    session_id: str,
    realtime_service: Annotated[OperatorRealtimeService, Depends(get_operator_realtime_service)],
    since_sequence: int = Query(default=0, ge=0),
    limit: int = Query(default=25, ge=1, le=100),
) -> OperatorSessionActivityResponse:
    """Return replayable activity for a selected operator session."""
    try:
        return await realtime_service.get_session_activity(
            session_id=session_id,
            since_sequence=since_sequence,
            limit=limit,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


__all__ = ["router"]
