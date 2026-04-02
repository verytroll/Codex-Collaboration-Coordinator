"""FastAPI dependencies for repository access."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import suppress
from typing import Annotated

from fastapi import Depends, Request

from app.codex_bridge import CodexProcessManager, LazyCodexBridgeClient
from app.core.config import get_config
from app.repositories.a2a_tasks import A2ATaskRepository
from app.repositories.agents import AgentRepository, AgentRuntimeRepository
from app.repositories.approvals import ApprovalRepository
from app.repositories.artifacts import ArtifactRepository
from app.repositories.channels import SessionChannelRepository
from app.repositories.job_inputs import JobInputRepository
from app.repositories.jobs import JobEventRepository, JobRepository
from app.repositories.messages import MessageMentionRepository, MessageRepository
from app.repositories.orchestration_runs import OrchestrationRunRepository
from app.repositories.participants import ParticipantRepository
from app.repositories.phases import PhaseRepository
from app.repositories.policies import PolicyRepository
from app.repositories.presence import PresenceRepository
from app.repositories.public_events import PublicTaskEventRepository
from app.repositories.public_subscriptions import PublicTaskSubscriptionRepository
from app.repositories.relay_edges import RelayEdgeRepository
from app.repositories.reviews import ReviewRepository
from app.repositories.rules import RuleRepository
from app.repositories.runtime_pools import RuntimePoolRepository, WorkContextRepository
from app.repositories.session_events import SessionEventRepository
from app.repositories.session_templates import SessionTemplateRepository
from app.repositories.sessions import SessionRepository
from app.repositories.transcript_exports import TranscriptExportRepository
from app.services.a2a_adapter import A2AAdapterService
from app.services.a2a_public_service import A2APublicService
from app.services.access_boundary import AccessBoundaryService
from app.services.approval_manager import ApprovalManager
from app.services.artifact_manager import ArtifactManager
from app.services.channel_service import ChannelService
from app.services.command_handler import CommandHandler
from app.services.debug_service import DebugService
from app.services.deployment_readiness import DeploymentReadinessService
from app.services.job_service import JobService
from app.services.loop_guard import LoopGuardService
from app.services.message_routing import MessageRoutingService
from app.services.offline_queue import OfflineQueueService
from app.services.operator_actions import OperatorActionService
from app.services.operator_dashboard import OperatorDashboardService
from app.services.operator_realtime import OperatorRealtimeService
from app.services.operator_shell import OperatorShellService
from app.services.orchestration_engine import OrchestrationEngineService
from app.services.participant_policy import ParticipantPolicyService
from app.services.permissions import CommandPermissions
from app.services.phase_gate_service import PhaseGateService
from app.services.phase_service import PhaseService
from app.services.policy_engine_v2 import PolicyEngineV2Service
from app.services.presence import PresenceService
from app.services.public_event_stream import PublicEventStreamService
from app.services.recovery import RecoveryService
from app.services.relay_engine import CodexRelayBridge, RelayEngine
from app.services.relay_templates import RelayTemplatesService
from app.services.review_mode import ReviewModeService
from app.services.rule_engine import RuleEngineService
from app.services.runtime_pool_service import RuntimePoolService
from app.services.runtime_service import RuntimeService
from app.services.session_template_service import SessionTemplateService
from app.services.streaming import StreamingService
from app.services.system_status import SystemStatusService
from app.services.thread_mapping import ThreadMappingService, ThreadMappingStore
from app.services.transcript_export import TranscriptExportService
from app.services.work_context_service import WorkContextService

_THREAD_MAPPING_STORE = ThreadMappingStore()


def get_database_url() -> str:
    """Return the active database URL from application config."""
    return get_config().database_url


def get_access_boundary_service() -> AccessBoundaryService:
    """Provide the configured access boundary service."""
    config = get_config()
    return AccessBoundaryService(
        access_boundary_mode=config.access_boundary_mode,
        access_token=config.access_token,
        access_token_header=config.access_token_header,
    )


async def require_operator_access(
    request: Request,
    access_boundary_service: Annotated[
        AccessBoundaryService,
        Depends(get_access_boundary_service),
    ],
) -> None:
    """Authorize access to operator-facing routes."""
    await access_boundary_service.require_operator_access(request)


async def require_public_access(
    request: Request,
    access_boundary_service: Annotated[
        AccessBoundaryService,
        Depends(get_access_boundary_service),
    ],
) -> None:
    """Authorize access to public and A2A routes."""
    await access_boundary_service.require_public_access(request)


def get_session_repository(
    database_url: Annotated[str, Depends(get_database_url)],
) -> SessionRepository:
    """Provide a session repository bound to the configured database."""
    return SessionRepository(database_url)


def get_session_template_repository(
    database_url: Annotated[str, Depends(get_database_url)],
) -> SessionTemplateRepository:
    """Provide a session template repository bound to the configured database."""
    return SessionTemplateRepository(database_url)


def get_agent_repository(
    database_url: Annotated[str, Depends(get_database_url)],
) -> AgentRepository:
    """Provide an agent repository bound to the configured database."""
    return AgentRepository(database_url)


def get_agent_runtime_repository(
    database_url: Annotated[str, Depends(get_database_url)],
) -> AgentRuntimeRepository:
    """Provide an agent runtime repository bound to the configured database."""
    return AgentRuntimeRepository(database_url)


def get_artifact_repository(
    database_url: Annotated[str, Depends(get_database_url)],
) -> ArtifactRepository:
    """Provide an artifact repository bound to the configured database."""
    return ArtifactRepository(database_url)


def get_review_repository(
    database_url: Annotated[str, Depends(get_database_url)],
) -> ReviewRepository:
    """Provide a review repository bound to the configured database."""
    return ReviewRepository(database_url)


def get_transcript_export_repository(
    database_url: Annotated[str, Depends(get_database_url)],
) -> TranscriptExportRepository:
    """Provide a transcript export repository bound to the configured database."""
    return TranscriptExportRepository(database_url)


def get_channel_repository(
    database_url: Annotated[str, Depends(get_database_url)],
) -> SessionChannelRepository:
    """Provide a channel repository bound to the configured database."""
    return SessionChannelRepository(database_url)


def get_approval_repository(
    database_url: Annotated[str, Depends(get_database_url)],
) -> ApprovalRepository:
    """Provide an approval repository bound to the configured database."""
    return ApprovalRepository(database_url)


def get_runtime_service(
    runtime_repository: Annotated[AgentRuntimeRepository, Depends(get_agent_runtime_repository)],
) -> RuntimeService:
    """Provide a runtime service bound to the configured repositories."""
    return RuntimeService(runtime_repository)


def get_system_status_service(
    database_url: Annotated[str, Depends(get_database_url)],
    session_repository: Annotated[SessionRepository, Depends(get_session_repository)],
    agent_repository: Annotated[AgentRepository, Depends(get_agent_repository)],
    runtime_repository: Annotated[AgentRuntimeRepository, Depends(get_agent_runtime_repository)],
    job_repository: Annotated[JobRepository, Depends(get_job_repository)],
    approval_repository: Annotated[ApprovalRepository, Depends(get_approval_repository)],
    phase_repository: Annotated[PhaseRepository, Depends(get_phase_repository)],
    review_repository: Annotated[ReviewRepository, Depends(get_review_repository)],
) -> SystemStatusService:
    """Provide operator-facing system status aggregation."""
    config = get_config()
    return SystemStatusService(
        database_url=database_url,
        codex_bridge_mode=config.codex_bridge_mode,
        session_repository=session_repository,
        agent_repository=agent_repository,
        runtime_repository=runtime_repository,
        job_repository=job_repository,
        approval_repository=approval_repository,
        phase_repository=phase_repository,
        review_repository=review_repository,
    )


def get_deployment_readiness_service(
    database_url: Annotated[str, Depends(get_database_url)],
) -> DeploymentReadinessService:
    """Provide the deployment readiness service."""
    return DeploymentReadinessService(database_url=database_url)


def get_debug_service(
    session_repository: Annotated[SessionRepository, Depends(get_session_repository)],
    runtime_repository: Annotated[AgentRuntimeRepository, Depends(get_agent_runtime_repository)],
    job_repository: Annotated[JobRepository, Depends(get_job_repository)],
    approval_repository: Annotated[ApprovalRepository, Depends(get_approval_repository)],
    system_status_service: Annotated[SystemStatusService, Depends(get_system_status_service)],
) -> DebugService:
    """Provide the operator-facing debug surface service."""
    return DebugService(
        session_repository=session_repository,
        runtime_repository=runtime_repository,
        job_repository=job_repository,
        approval_repository=approval_repository,
        system_status_service=system_status_service,
    )


def get_operator_dashboard_service(
    session_repository: Annotated[SessionRepository, Depends(get_session_repository)],
    phase_repository: Annotated[PhaseRepository, Depends(get_phase_repository)],
    job_repository: Annotated[JobRepository, Depends(get_job_repository)],
    review_repository: Annotated[ReviewRepository, Depends(get_review_repository)],
    orchestration_run_repository: Annotated[
        OrchestrationRunRepository,
        Depends(get_orchestration_run_repository),
    ],
    runtime_pool_service: Annotated[RuntimePoolService, Depends(get_runtime_pool_service)],
    work_context_repository: Annotated[
        WorkContextRepository,
        Depends(get_work_context_repository),
    ],
    a2a_task_repository: Annotated[A2ATaskRepository, Depends(get_a2a_task_repository)],
    approval_repository: Annotated[ApprovalRepository, Depends(get_approval_repository)],
    debug_service: Annotated[DebugService, Depends(get_debug_service)],
) -> OperatorDashboardService:
    """Provide the operator dashboard service."""
    return OperatorDashboardService(
        session_repository=session_repository,
        phase_repository=phase_repository,
        job_repository=job_repository,
        review_repository=review_repository,
        orchestration_run_repository=orchestration_run_repository,
        runtime_pool_service=runtime_pool_service,
        work_context_repository=work_context_repository,
        a2a_task_repository=a2a_task_repository,
        approval_repository=approval_repository,
        debug_service=debug_service,
    )


def get_operator_action_service(
    session_repository: Annotated[SessionRepository, Depends(get_session_repository)],
    job_repository: Annotated[JobRepository, Depends(get_job_repository)],
    approval_repository: Annotated[ApprovalRepository, Depends(get_approval_repository)],
    session_event_repository: Annotated[
        SessionEventRepository,
        Depends(get_session_event_repository),
    ],
    approval_manager: Annotated[ApprovalManager, Depends(get_approval_manager)],
    offline_queue_service: Annotated[OfflineQueueService, Depends(get_offline_queue_service)],
    phase_service: Annotated[PhaseService, Depends(get_phase_service)],
    relay_engine: Annotated[RelayEngine, Depends(get_relay_engine)],
) -> OperatorActionService:
    """Provide the operator action service."""
    return OperatorActionService(
        session_repository=session_repository,
        job_repository=job_repository,
        approval_repository=approval_repository,
        session_event_repository=session_event_repository,
        approval_manager=approval_manager,
        offline_queue_service=offline_queue_service,
        phase_service=phase_service,
        relay_engine=relay_engine,
    )


def get_operator_shell_service(
    dashboard_service: Annotated[OperatorDashboardService, Depends(get_operator_dashboard_service)],
    session_repository: Annotated[SessionRepository, Depends(get_session_repository)],
    phase_repository: Annotated[PhaseRepository, Depends(get_phase_repository)],
    job_repository: Annotated[JobRepository, Depends(get_job_repository)],
    approval_repository: Annotated[ApprovalRepository, Depends(get_approval_repository)],
    artifact_repository: Annotated[ArtifactRepository, Depends(get_artifact_repository)],
    transcript_export_repository: Annotated[
        TranscriptExportRepository,
        Depends(get_transcript_export_repository),
    ],
    message_repository: Annotated[MessageRepository, Depends(get_message_repository)],
    message_mention_repository: Annotated[
        MessageMentionRepository,
        Depends(get_message_mention_repository),
    ],
    participant_repository: Annotated[
        ParticipantRepository,
        Depends(get_participant_repository),
    ],
    agent_repository: Annotated[AgentRepository, Depends(get_agent_repository)],
    participant_policy_service: Annotated[
        ParticipantPolicyService,
        Depends(get_participant_policy_service),
    ],
) -> OperatorShellService:
    """Provide the thin operator shell bootstrap service."""
    return OperatorShellService(
        dashboard_service=dashboard_service,
        session_repository=session_repository,
        phase_repository=phase_repository,
        job_repository=job_repository,
        approval_repository=approval_repository,
        artifact_repository=artifact_repository,
        transcript_export_repository=transcript_export_repository,
        message_repository=message_repository,
        message_mention_repository=message_mention_repository,
        participant_repository=participant_repository,
        agent_repository=agent_repository,
        participant_policy_service=participant_policy_service,
    )


def get_operator_realtime_service(
    dashboard_service: Annotated[OperatorDashboardService, Depends(get_operator_dashboard_service)],
    session_repository: Annotated[SessionRepository, Depends(get_session_repository)],
    phase_repository: Annotated[PhaseRepository, Depends(get_phase_repository)],
    job_repository: Annotated[JobRepository, Depends(get_job_repository)],
    job_event_repository: Annotated[JobEventRepository, Depends(get_job_event_repository)],
    approval_repository: Annotated[ApprovalRepository, Depends(get_approval_repository)],
    message_repository: Annotated[MessageRepository, Depends(get_message_repository)],
    session_event_repository: Annotated[
        SessionEventRepository,
        Depends(get_session_event_repository),
    ],
    runtime_pool_repository: Annotated[
        RuntimePoolRepository,
        Depends(get_runtime_pool_repository),
    ],
    work_context_repository: Annotated[
        WorkContextRepository,
        Depends(get_work_context_repository),
    ],
) -> OperatorRealtimeService:
    """Provide the operator realtime activity service."""
    return OperatorRealtimeService(
        dashboard_service=dashboard_service,
        session_repository=session_repository,
        phase_repository=phase_repository,
        job_repository=job_repository,
        job_event_repository=job_event_repository,
        approval_repository=approval_repository,
        message_repository=message_repository,
        session_event_repository=session_event_repository,
        runtime_pool_repository=runtime_pool_repository,
        work_context_repository=work_context_repository,
    )


def get_presence_repository(
    database_url: Annotated[str, Depends(get_database_url)],
) -> PresenceRepository:
    """Provide a presence repository bound to the configured database."""
    return PresenceRepository(database_url)


def get_presence_service(
    presence_repository: Annotated[PresenceRepository, Depends(get_presence_repository)],
    runtime_repository: Annotated[AgentRuntimeRepository, Depends(get_agent_runtime_repository)],
    runtime_service: Annotated[RuntimeService, Depends(get_runtime_service)],
) -> PresenceService:
    """Provide the presence tracking service."""
    return PresenceService(
        presence_repository=presence_repository,
        runtime_repository=runtime_repository,
        runtime_service=runtime_service,
    )


def get_participant_repository(
    database_url: Annotated[str, Depends(get_database_url)],
) -> ParticipantRepository:
    """Provide a participant repository bound to the configured database."""
    return ParticipantRepository(database_url)


def get_participant_policy_service() -> ParticipantPolicyService:
    """Provide the participant role and policy service."""
    return ParticipantPolicyService()


def get_phase_repository(
    database_url: Annotated[str, Depends(get_database_url)],
) -> PhaseRepository:
    """Provide a phase repository bound to the configured database."""
    return PhaseRepository(database_url)


def get_orchestration_run_repository(
    database_url: Annotated[str, Depends(get_database_url)],
) -> OrchestrationRunRepository:
    """Provide an orchestration run repository bound to the configured database."""
    return OrchestrationRunRepository(database_url)


def get_message_repository(
    database_url: Annotated[str, Depends(get_database_url)],
) -> MessageRepository:
    """Provide a message repository bound to the configured database."""
    return MessageRepository(database_url)


def get_message_mention_repository(
    database_url: Annotated[str, Depends(get_database_url)],
) -> MessageMentionRepository:
    """Provide a message mention repository bound to the configured database."""
    return MessageMentionRepository(database_url)


def get_job_repository(
    database_url: Annotated[str, Depends(get_database_url)],
) -> JobRepository:
    """Provide a job repository bound to the configured database."""
    return JobRepository(database_url)


def get_job_event_repository(
    database_url: Annotated[str, Depends(get_database_url)],
) -> JobEventRepository:
    """Provide a job event repository bound to the configured database."""
    return JobEventRepository(database_url)


def get_job_input_repository(
    database_url: Annotated[str, Depends(get_database_url)],
) -> JobInputRepository:
    """Provide a job input repository bound to the configured database."""
    return JobInputRepository(database_url)


def get_rule_repository(
    database_url: Annotated[str, Depends(get_database_url)],
) -> RuleRepository:
    """Provide a rule repository bound to the configured database."""
    return RuleRepository(database_url)


def get_runtime_pool_repository(
    database_url: Annotated[str, Depends(get_database_url)],
) -> RuntimePoolRepository:
    """Provide a runtime pool repository bound to the configured database."""
    return RuntimePoolRepository(database_url)


def get_work_context_repository(
    database_url: Annotated[str, Depends(get_database_url)],
) -> WorkContextRepository:
    """Provide a work context repository bound to the configured database."""
    return WorkContextRepository(database_url)


def get_policy_repository(
    database_url: Annotated[str, Depends(get_database_url)],
) -> PolicyRepository:
    """Provide a policy repository bound to the configured database."""
    return PolicyRepository(database_url)


def get_work_context_service(
    work_context_repository: Annotated[
        WorkContextRepository,
        Depends(get_work_context_repository),
    ],
    runtime_repository: Annotated[AgentRuntimeRepository, Depends(get_agent_runtime_repository)],
    agent_repository: Annotated[AgentRepository, Depends(get_agent_repository)],
) -> WorkContextService:
    """Provide the work context orchestration service."""
    return WorkContextService(
        work_context_repository=work_context_repository,
        runtime_repository=runtime_repository,
        agent_repository=agent_repository,
    )


def get_runtime_pool_service(
    runtime_pool_repository: Annotated[
        RuntimePoolRepository,
        Depends(get_runtime_pool_repository),
    ],
    work_context_service: Annotated[WorkContextService, Depends(get_work_context_service)],
    agent_repository: Annotated[AgentRepository, Depends(get_agent_repository)],
    runtime_repository: Annotated[AgentRuntimeRepository, Depends(get_agent_runtime_repository)],
    job_repository: Annotated[JobRepository, Depends(get_job_repository)],
) -> RuntimePoolService:
    """Provide the runtime pool orchestration service."""
    return RuntimePoolService(
        runtime_pool_repository=runtime_pool_repository,
        work_context_service=work_context_service,
        agent_repository=agent_repository,
        runtime_repository=runtime_repository,
        job_repository=job_repository,
    )


def get_a2a_task_repository(
    database_url: Annotated[str, Depends(get_database_url)],
) -> A2ATaskRepository:
    """Provide an experimental A2A task repository bound to the configured database."""
    return A2ATaskRepository(database_url)


def get_public_task_event_repository(
    database_url: Annotated[str, Depends(get_database_url)],
) -> PublicTaskEventRepository:
    """Provide a public A2A task event repository bound to the configured database."""
    return PublicTaskEventRepository(database_url)


def get_public_task_subscription_repository(
    database_url: Annotated[str, Depends(get_database_url)],
) -> PublicTaskSubscriptionRepository:
    """Provide a public A2A task subscription repository bound to the configured database."""
    return PublicTaskSubscriptionRepository(database_url)


def get_rule_engine_service(
    rule_repository: Annotated[RuleRepository, Depends(get_rule_repository)],
) -> RuleEngineService:
    """Provide the basic collaboration rules engine."""
    return RuleEngineService(rule_repository)


def get_relay_templates_service() -> RelayTemplatesService:
    """Provide the structured relay template service."""
    return RelayTemplatesService()


def get_phase_service(
    phase_repository: Annotated[PhaseRepository, Depends(get_phase_repository)],
    session_repository: Annotated[SessionRepository, Depends(get_session_repository)],
    relay_templates_service: Annotated[
        RelayTemplatesService,
        Depends(get_relay_templates_service),
    ],
) -> PhaseService:
    """Provide the phase preset and activation service."""
    return PhaseService(
        phase_repository=phase_repository,
        session_repository=session_repository,
        relay_templates_service=relay_templates_service,
    )


def get_orchestration_engine_service(
    orchestration_run_repository: Annotated[
        OrchestrationRunRepository,
        Depends(get_orchestration_run_repository),
    ],
    session_repository: Annotated[SessionRepository, Depends(get_session_repository)],
    phase_service: Annotated[PhaseService, Depends(get_phase_service)],
) -> OrchestrationEngineService:
    """Provide the orchestration run state service."""
    return OrchestrationEngineService(
        orchestration_run_repository=orchestration_run_repository,
        session_repository=session_repository,
        phase_service=phase_service,
    )


def get_job_service(
    job_repository: Annotated[JobRepository, Depends(get_job_repository)],
    runtime_service: Annotated[RuntimeService, Depends(get_runtime_service)],
    runtime_pool_service: Annotated[
        RuntimePoolService,
        Depends(get_runtime_pool_service),
    ],
) -> JobService:
    """Provide a job service bound to the configured repositories."""
    return JobService(
        job_repository,
        runtime_service,
        runtime_pool_service=runtime_pool_service,
    )


def get_thread_mapping_service(
    runtime_service: Annotated[RuntimeService, Depends(get_runtime_service)],
) -> ThreadMappingService:
    """Provide the session-thread mapping service."""
    return ThreadMappingService(runtime_service, store=_THREAD_MAPPING_STORE)


async def get_codex_bridge_client() -> AsyncIterator[CodexRelayBridge]:
    """Provide a lazily started Codex JSON-RPC client for the current request."""
    manager = CodexProcessManager()
    client = LazyCodexBridgeClient(manager)
    try:
        yield client
    finally:
        with suppress(Exception):
            await client.aclose()


def get_message_routing_service(
    message_mention_repository: Annotated[
        MessageMentionRepository,
        Depends(get_message_mention_repository),
    ],
    participant_repository: Annotated[ParticipantRepository, Depends(get_participant_repository)],
    agent_repository: Annotated[AgentRepository, Depends(get_agent_repository)],
    job_service: Annotated[JobService, Depends(get_job_service)],
    rule_engine_service: Annotated[RuleEngineService, Depends(get_rule_engine_service)],
) -> MessageRoutingService:
    """Provide the message routing service."""
    return MessageRoutingService(
        message_mention_repository=message_mention_repository,
        participant_repository=participant_repository,
        agent_repository=agent_repository,
        job_service=job_service,
        rule_engine_service=rule_engine_service,
    )


def get_command_permissions(
    participant_repository: Annotated[ParticipantRepository, Depends(get_participant_repository)],
    participant_policy_service: Annotated[
        ParticipantPolicyService,
        Depends(get_participant_policy_service),
    ],
) -> CommandPermissions:
    """Provide command permission checks."""
    return CommandPermissions(
        participant_repository,
        participant_policy_service=participant_policy_service,
    )


def get_relay_engine(
    job_repository: Annotated[JobRepository, Depends(get_job_repository)],
    job_event_repository: Annotated[JobEventRepository, Depends(get_job_event_repository)],
    relay_edge_repository: Annotated[RelayEdgeRepository, Depends(get_relay_edge_repository)],
    message_repository: Annotated[MessageRepository, Depends(get_message_repository)],
    session_repository: Annotated[SessionRepository, Depends(get_session_repository)],
    session_event_repository: Annotated[
        SessionEventRepository, Depends(get_session_event_repository)
    ],
    agent_repository: Annotated[AgentRepository, Depends(get_agent_repository)],
    runtime_service: Annotated[RuntimeService, Depends(get_runtime_service)],
    thread_mapping_service: Annotated[ThreadMappingService, Depends(get_thread_mapping_service)],
    loop_guard_service: Annotated[LoopGuardService, Depends(get_loop_guard_service)],
    artifact_manager: Annotated[ArtifactManager, Depends(get_artifact_manager)],
    approval_manager: Annotated[ApprovalManager, Depends(get_approval_manager)],
    bridge: Annotated[CodexRelayBridge, Depends(get_codex_bridge_client)],
) -> RelayEngine:
    """Provide the relay engine."""
    return RelayEngine(
        job_repository=job_repository,
        job_event_repository=job_event_repository,
        relay_edge_repository=relay_edge_repository,
        message_repository=message_repository,
        session_repository=session_repository,
        session_event_repository=session_event_repository,
        agent_repository=agent_repository,
        runtime_service=runtime_service,
        thread_mapping_service=thread_mapping_service,
        loop_guard_service=loop_guard_service,
        artifact_manager=artifact_manager,
        approval_manager=approval_manager,
        bridge=bridge,
    )


def get_command_handler(
    job_service: Annotated[JobService, Depends(get_job_service)],
    job_repository: Annotated[JobRepository, Depends(get_job_repository)],
    participant_repository: Annotated[ParticipantRepository, Depends(get_participant_repository)],
    agent_repository: Annotated[AgentRepository, Depends(get_agent_repository)],
    session_repository: Annotated[SessionRepository, Depends(get_session_repository)],
    session_event_repository: Annotated[
        SessionEventRepository, Depends(get_session_event_repository)
    ],
    permissions: Annotated[CommandPermissions, Depends(get_command_permissions)],
    relay_engine: Annotated[RelayEngine, Depends(get_relay_engine)],
    offline_queue_service: Annotated[OfflineQueueService, Depends(get_offline_queue_service)],
    review_mode_service: Annotated[ReviewModeService, Depends(get_review_mode_service)],
    phase_service: Annotated[PhaseService, Depends(get_phase_service)],
) -> CommandHandler:
    """Provide the command handler."""
    return CommandHandler(
        job_service=job_service,
        job_repository=job_repository,
        participant_repository=participant_repository,
        agent_repository=agent_repository,
        session_repository=session_repository,
        session_event_repository=session_event_repository,
        permissions=permissions,
        relay_engine=relay_engine,
        offline_queue_service=offline_queue_service,
        review_mode_service=review_mode_service,
        phase_service=phase_service,
    )


def get_session_event_repository(
    database_url: Annotated[str, Depends(get_database_url)],
) -> SessionEventRepository:
    """Provide a session event repository bound to the configured database."""
    return SessionEventRepository(database_url)


def get_policy_engine_v2_service(
    policy_repository: Annotated[PolicyRepository, Depends(get_policy_repository)],
    session_repository: Annotated[SessionRepository, Depends(get_session_repository)],
    job_repository: Annotated[JobRepository, Depends(get_job_repository)],
    phase_service: Annotated[PhaseService, Depends(get_phase_service)],
    session_event_repository: Annotated[
        SessionEventRepository,
        Depends(get_session_event_repository),
    ],
) -> PolicyEngineV2Service:
    """Provide the advanced policy engine service."""
    return PolicyEngineV2Service(
        policy_repository=policy_repository,
        session_repository=session_repository,
        job_repository=job_repository,
        phase_service=phase_service,
        session_event_repository=session_event_repository,
    )


def get_artifact_manager(
    artifact_repository: Annotated[ArtifactRepository, Depends(get_artifact_repository)],
    job_event_repository: Annotated[JobEventRepository, Depends(get_job_event_repository)],
) -> ArtifactManager:
    """Provide the artifact manager."""
    return ArtifactManager(
        artifact_repository=artifact_repository,
        job_event_repository=job_event_repository,
    )


def get_review_mode_service(
    review_repository: Annotated[ReviewRepository, Depends(get_review_repository)],
    job_repository: Annotated[JobRepository, Depends(get_job_repository)],
    message_repository: Annotated[MessageRepository, Depends(get_message_repository)],
    artifact_repository: Annotated[ArtifactRepository, Depends(get_artifact_repository)],
    artifact_manager: Annotated[ArtifactManager, Depends(get_artifact_manager)],
    job_service: Annotated[JobService, Depends(get_job_service)],
    offline_queue_service: Annotated[OfflineQueueService, Depends(get_offline_queue_service)],
    session_repository: Annotated[SessionRepository, Depends(get_session_repository)],
    participant_repository: Annotated[ParticipantRepository, Depends(get_participant_repository)],
    channel_service: Annotated[ChannelService, Depends(get_channel_service)],
    session_event_repository: Annotated[
        SessionEventRepository, Depends(get_session_event_repository)
    ],
    relay_templates_service: Annotated[
        RelayTemplatesService,
        Depends(get_relay_templates_service),
    ],
) -> ReviewModeService:
    """Provide the review mode service."""
    return ReviewModeService(
        review_repository=review_repository,
        job_repository=job_repository,
        message_repository=message_repository,
        artifact_repository=artifact_repository,
        artifact_manager=artifact_manager,
        job_service=job_service,
        offline_queue_service=offline_queue_service,
        session_repository=session_repository,
        participant_repository=participant_repository,
        channel_service=channel_service,
        session_event_repository=session_event_repository,
        relay_templates_service=relay_templates_service,
    )


def get_channel_service(
    channel_repository: Annotated[SessionChannelRepository, Depends(get_channel_repository)],
) -> ChannelService:
    """Provide the session channel orchestration service."""
    return ChannelService(channel_repository)


def get_session_template_service(
    session_template_repository: Annotated[
        SessionTemplateRepository,
        Depends(get_session_template_repository),
    ],
    session_repository: Annotated[SessionRepository, Depends(get_session_repository)],
    channel_repository: Annotated[SessionChannelRepository, Depends(get_channel_repository)],
    phase_repository: Annotated[PhaseRepository, Depends(get_phase_repository)],
    agent_repository: Annotated[AgentRepository, Depends(get_agent_repository)],
    phase_service: Annotated[PhaseService, Depends(get_phase_service)],
    rule_engine_service: Annotated[RuleEngineService, Depends(get_rule_engine_service)],
) -> SessionTemplateService:
    """Provide the session template orchestration service."""
    return SessionTemplateService(
        session_template_repository=session_template_repository,
        session_repository=session_repository,
        channel_repository=channel_repository,
        phase_repository=phase_repository,
        agent_repository=agent_repository,
        phase_service=phase_service,
        rule_engine_service=rule_engine_service,
    )


def get_a2a_adapter_service(
    task_repository: Annotated[A2ATaskRepository, Depends(get_a2a_task_repository)],
    job_repository: Annotated[JobRepository, Depends(get_job_repository)],
    artifact_repository: Annotated[ArtifactRepository, Depends(get_artifact_repository)],
    session_repository: Annotated[SessionRepository, Depends(get_session_repository)],
    phase_service: Annotated[PhaseService, Depends(get_phase_service)],
) -> A2AAdapterService:
    """Provide the experimental A2A adapter bridge service."""
    return A2AAdapterService(
        task_repository=task_repository,
        job_repository=job_repository,
        artifact_repository=artifact_repository,
        session_repository=session_repository,
        phase_service=phase_service,
    )


def get_a2a_public_service(
    task_repository: Annotated[A2ATaskRepository, Depends(get_a2a_task_repository)],
    job_repository: Annotated[JobRepository, Depends(get_job_repository)],
    artifact_repository: Annotated[ArtifactRepository, Depends(get_artifact_repository)],
    session_repository: Annotated[SessionRepository, Depends(get_session_repository)],
    phase_service: Annotated[PhaseService, Depends(get_phase_service)],
    event_stream_service: Annotated[
        PublicEventStreamService,
        Depends(get_a2a_public_event_stream_service),
    ],
) -> A2APublicService:
    """Provide the public A2A task surface service."""
    return A2APublicService(
        adapter_service=A2AAdapterService(
            task_repository=task_repository,
            job_repository=job_repository,
            artifact_repository=artifact_repository,
            session_repository=session_repository,
            phase_service=phase_service,
        ),
        task_repository=task_repository,
        session_repository=session_repository,
        event_stream_service=event_stream_service,
    )


def get_a2a_public_event_stream_service(
    task_repository: Annotated[A2ATaskRepository, Depends(get_a2a_task_repository)],
    event_repository: Annotated[
        PublicTaskEventRepository,
        Depends(get_public_task_event_repository),
    ],
    subscription_repository: Annotated[
        PublicTaskSubscriptionRepository,
        Depends(get_public_task_subscription_repository),
    ],
    review_repository: Annotated[ReviewRepository, Depends(get_review_repository)],
) -> PublicEventStreamService:
    """Provide the public A2A event stream service."""
    return PublicEventStreamService(
        task_repository=task_repository,
        event_repository=event_repository,
        subscription_repository=subscription_repository,
        review_repository=review_repository,
    )


def get_transcript_export_service(
    session_repository: Annotated[SessionRepository, Depends(get_session_repository)],
    message_repository: Annotated[MessageRepository, Depends(get_message_repository)],
    message_mention_repository: Annotated[
        MessageMentionRepository,
        Depends(get_message_mention_repository),
    ],
    job_repository: Annotated[JobRepository, Depends(get_job_repository)],
    artifact_repository: Annotated[ArtifactRepository, Depends(get_artifact_repository)],
    transcript_export_repository: Annotated[
        TranscriptExportRepository,
        Depends(get_transcript_export_repository),
    ],
    session_event_repository: Annotated[
        SessionEventRepository,
        Depends(get_session_event_repository),
    ],
) -> TranscriptExportService:
    """Provide the transcript export service."""
    return TranscriptExportService(
        session_repository=session_repository,
        message_repository=message_repository,
        message_mention_repository=message_mention_repository,
        job_repository=job_repository,
        artifact_repository=artifact_repository,
        transcript_export_repository=transcript_export_repository,
        session_event_repository=session_event_repository,
    )


def get_approval_manager(
    approval_repository: Annotated[ApprovalRepository, Depends(get_approval_repository)],
    job_repository: Annotated[JobRepository, Depends(get_job_repository)],
    job_event_repository: Annotated[JobEventRepository, Depends(get_job_event_repository)],
    session_event_repository: Annotated[
        SessionEventRepository, Depends(get_session_event_repository)
    ],
) -> ApprovalManager:
    """Provide the approval manager."""
    return ApprovalManager(
        approval_repository=approval_repository,
        job_repository=job_repository,
        job_event_repository=job_event_repository,
        session_event_repository=session_event_repository,
    )


def get_phase_gate_service(
    orchestration_engine_service: Annotated[
        OrchestrationEngineService,
        Depends(get_orchestration_engine_service),
    ],
    review_mode_service: Annotated[ReviewModeService, Depends(get_review_mode_service)],
    approval_manager: Annotated[ApprovalManager, Depends(get_approval_manager)],
    policy_engine_v2_service: Annotated[
        PolicyEngineV2Service,
        Depends(get_policy_engine_v2_service),
    ],
    job_service: Annotated[JobService, Depends(get_job_service)],
    artifact_manager: Annotated[ArtifactManager, Depends(get_artifact_manager)],
    session_repository: Annotated[SessionRepository, Depends(get_session_repository)],
    job_repository: Annotated[JobRepository, Depends(get_job_repository)],
    participant_repository: Annotated[
        ParticipantRepository,
        Depends(get_participant_repository),
    ],
    channel_service: Annotated[ChannelService, Depends(get_channel_service)],
    phase_service: Annotated[PhaseService, Depends(get_phase_service)],
    relay_templates_service: Annotated[
        RelayTemplatesService,
        Depends(get_relay_templates_service),
    ],
    session_event_repository: Annotated[
        SessionEventRepository,
        Depends(get_session_event_repository),
    ],
) -> PhaseGateService:
    """Provide the orchestration phase gate service."""
    return PhaseGateService(
        orchestration_engine_service=orchestration_engine_service,
        review_mode_service=review_mode_service,
        approval_manager=approval_manager,
        policy_engine_v2_service=policy_engine_v2_service,
        job_service=job_service,
        artifact_manager=artifact_manager,
        session_repository=session_repository,
        job_repository=job_repository,
        participant_repository=participant_repository,
        channel_service=channel_service,
        phase_service=phase_service,
        relay_templates_service=relay_templates_service,
        session_event_repository=session_event_repository,
    )


def get_offline_queue_service(
    job_repository: Annotated[JobRepository, Depends(get_job_repository)],
    job_input_repository: Annotated[JobInputRepository, Depends(get_job_input_repository)],
    runtime_service: Annotated[RuntimeService, Depends(get_runtime_service)],
    relay_engine: Annotated[RelayEngine, Depends(get_relay_engine)],
    rule_engine_service: Annotated[RuleEngineService, Depends(get_rule_engine_service)],
) -> OfflineQueueService:
    """Provide the offline queue service."""
    return OfflineQueueService(
        job_repository=job_repository,
        job_input_repository=job_input_repository,
        runtime_service=runtime_service,
        relay_engine=relay_engine,
        rule_engine_service=rule_engine_service,
    )


def get_loop_guard_service(
    relay_edge_repository: Annotated[RelayEdgeRepository, Depends(get_relay_edge_repository)],
    job_repository: Annotated[JobRepository, Depends(get_job_repository)],
    job_event_repository: Annotated[JobEventRepository, Depends(get_job_event_repository)],
    session_repository: Annotated[SessionRepository, Depends(get_session_repository)],
    session_event_repository: Annotated[
        SessionEventRepository, Depends(get_session_event_repository)
    ],
) -> LoopGuardService:
    """Provide the loop guard service."""
    return LoopGuardService(
        relay_edge_repository=relay_edge_repository,
        job_repository=job_repository,
        job_event_repository=job_event_repository,
        session_repository=session_repository,
        session_event_repository=session_event_repository,
    )


def get_streaming_service(
    job_repository: Annotated[JobRepository, Depends(get_job_repository)],
    job_event_repository: Annotated[JobEventRepository, Depends(get_job_event_repository)],
    artifact_repository: Annotated[ArtifactRepository, Depends(get_artifact_repository)],
    session_repository: Annotated[SessionRepository, Depends(get_session_repository)],
    session_event_repository: Annotated[
        SessionEventRepository, Depends(get_session_event_repository)
    ],
    message_repository: Annotated[MessageRepository, Depends(get_message_repository)],
) -> StreamingService:
    """Provide the streaming service."""
    return StreamingService(
        job_repository=job_repository,
        job_event_repository=job_event_repository,
        artifact_repository=artifact_repository,
        session_repository=session_repository,
        session_event_repository=session_event_repository,
        message_repository=message_repository,
    )


def get_recovery_service(
    job_repository: Annotated[JobRepository, Depends(get_job_repository)],
    runtime_repository: Annotated[AgentRuntimeRepository, Depends(get_agent_runtime_repository)],
    presence_repository: Annotated[PresenceRepository, Depends(get_presence_repository)],
    session_repository: Annotated[SessionRepository, Depends(get_session_repository)],
    session_event_repository: Annotated[
        SessionEventRepository, Depends(get_session_event_repository)
    ],
    runtime_service: Annotated[RuntimeService, Depends(get_runtime_service)],
    thread_mapping_store: ThreadMappingStore | None = None,
) -> RecoveryService:
    """Provide the recovery service."""
    return RecoveryService(
        job_repository=job_repository,
        runtime_repository=runtime_repository,
        presence_repository=presence_repository,
        session_repository=session_repository,
        session_event_repository=session_event_repository,
        runtime_service=runtime_service,
        thread_mapping_store=thread_mapping_store or _THREAD_MAPPING_STORE,
    )


def get_thread_mapping_store() -> ThreadMappingStore:
    """Expose the shared in-memory thread mapping store."""
    return _THREAD_MAPPING_STORE


def get_relay_edge_repository(
    database_url: Annotated[str, Depends(get_database_url)],
) -> RelayEdgeRepository:
    """Provide a relay edge repository bound to the configured database."""
    return RelayEdgeRepository(database_url)
