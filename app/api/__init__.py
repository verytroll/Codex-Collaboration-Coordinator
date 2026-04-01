"""API layer package."""

from fastapi import APIRouter, Depends

from app.api.a2a_adapter import router as a2a_adapter_router
from app.api.a2a_events import router as a2a_events_router
from app.api.a2a_placeholder import router as a2a_placeholder_router
from app.api.a2a_public import router as a2a_public_router
from app.api.agents import router as agents_router
from app.api.approvals import router as approvals_router
from app.api.artifacts import router as artifacts_router
from app.api.channels import router as channels_router
from app.api.dependencies import require_operator_access, require_public_access
from app.api.health import router as health_router
from app.api.jobs import router as jobs_router
from app.api.messages import router as messages_router
from app.api.operator_dashboard import router as operator_dashboard_router
from app.api.operator_ui import shell_router as operator_shell_router
from app.api.operator_ui import ui_router as operator_ui_router
from app.api.orchestration import router as orchestration_router
from app.api.participants import router as participants_router
from app.api.phases import router as phases_router
from app.api.policies import router as policies_router
from app.api.presence import router as presence_router
from app.api.review import router as review_router
from app.api.rules import router as rules_router
from app.api.runtime_pools import router as runtime_pools_router
from app.api.session_templates import router as session_templates_router
from app.api.sessions import router as sessions_router
from app.api.system import router as system_router

router = APIRouter()

# Public and operator-facing surfaces use the same baseline access boundary.
router.include_router(a2a_placeholder_router, dependencies=[Depends(require_public_access)])
router.include_router(a2a_public_router, dependencies=[Depends(require_public_access)])
router.include_router(a2a_events_router, dependencies=[Depends(require_public_access)])
router.include_router(a2a_adapter_router, dependencies=[Depends(require_public_access)])
router.include_router(health_router)

# Internal coordinator routes stay on the local-first path.
router.include_router(system_router, dependencies=[Depends(require_operator_access)])
router.include_router(sessions_router)
router.include_router(phases_router)
router.include_router(artifacts_router)
router.include_router(channels_router)
router.include_router(rules_router)
router.include_router(agents_router)
router.include_router(presence_router)
router.include_router(participants_router)
router.include_router(messages_router)
router.include_router(jobs_router)
router.include_router(approvals_router)
router.include_router(review_router, dependencies=[Depends(require_operator_access)])
router.include_router(session_templates_router, dependencies=[Depends(require_operator_access)])
router.include_router(runtime_pools_router, dependencies=[Depends(require_operator_access)])
router.include_router(orchestration_router, dependencies=[Depends(require_operator_access)])
router.include_router(policies_router, dependencies=[Depends(require_operator_access)])
router.include_router(operator_dashboard_router, dependencies=[Depends(require_operator_access)])
router.include_router(operator_ui_router, dependencies=[Depends(require_operator_access)])
router.include_router(operator_shell_router, dependencies=[Depends(require_operator_access)])

__all__ = ["router"]
