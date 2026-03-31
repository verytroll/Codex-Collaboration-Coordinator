"""Session channel orchestration."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.repositories.channels import SessionChannelRecord, SessionChannelRepository


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


DEFAULT_CHANNELS: tuple[tuple[str, str, str | None, int], ...] = (
    ("general", "General", "Default coordination channel", 10),
    ("planning", "Planning", "Planning and scoping", 20),
    ("review", "Review", "Review and feedback", 30),
    ("debug", "Debug", "Operator diagnostics and debugging", 40),
)


class ChannelService:
    """Create and resolve session channels."""

    def __init__(self, channel_repository: SessionChannelRepository) -> None:
        self.channel_repository = channel_repository

    async def list_channels(self, session_id: str) -> list[SessionChannelRecord]:
        """Return channels for a session, seeding defaults if needed."""
        await self.ensure_default_channels(session_id)
        return await self.channel_repository.list_by_session(session_id)

    async def ensure_default_channels(self, session_id: str) -> list[SessionChannelRecord]:
        """Create the default channel set when a session has none."""
        existing = await self.channel_repository.list_by_session(session_id)
        existing_keys = {channel.channel_key for channel in existing}
        created = False
        for channel_key, display_name, description, sort_order in DEFAULT_CHANNELS:
            if channel_key in existing_keys:
                continue
            now = _utc_now()
            await self.channel_repository.create(
                SessionChannelRecord(
                    id=f"chn_{uuid4().hex}",
                    session_id=session_id,
                    channel_key=channel_key,
                    display_name=display_name,
                    description=description,
                    is_default=True,
                    sort_order=sort_order,
                    created_at=now,
                    updated_at=now,
                )
            )
            created = True
        if created:
            existing = await self.channel_repository.list_by_session(session_id)
        return existing

    async def create_channel(
        self,
        *,
        session_id: str,
        channel_key: str,
        display_name: str,
        description: str | None = None,
    ) -> SessionChannelRecord:
        """Create a new session channel."""
        await self.ensure_default_channels(session_id)
        existing = await self.channel_repository.get_by_session_and_key(session_id, channel_key)
        if existing is not None:
            raise ValueError(f"Channel already exists in session {session_id}: {channel_key}")

        channels = await self.channel_repository.list_by_session(session_id)
        next_sort_order = max((channel.sort_order for channel in channels), default=0) + 10
        created_at = _utc_now()
        channel = SessionChannelRecord(
            id=f"chn_{uuid4().hex}",
            session_id=session_id,
            channel_key=channel_key,
            display_name=display_name,
            description=description,
            is_default=False,
            sort_order=next_sort_order,
            created_at=created_at,
            updated_at=created_at,
        )
        return await self.channel_repository.create(channel)

    async def ensure_channel_exists(
        self,
        *,
        session_id: str,
        channel_key: str,
    ) -> SessionChannelRecord:
        """Resolve a channel by key and seed defaults if needed."""
        await self.ensure_default_channels(session_id)
        channel = await self.channel_repository.get_by_session_and_key(session_id, channel_key)
        if channel is None:
            raise LookupError(f"Channel not found in session {session_id}: {channel_key}")
        return channel
