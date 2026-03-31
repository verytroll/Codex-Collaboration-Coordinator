"""Message parsing helpers for mentions and commands."""

from __future__ import annotations

import re
from dataclasses import dataclass

MENTION_PATTERN = re.compile(r"(?<!\w)#(?P<name>[A-Za-z][A-Za-z0-9_-]*)")
COMMAND_PATTERN = re.compile(
    r"^/(?P<name>new|interrupt|compact)(?:\s+(?P<args>.*))?$",
    re.IGNORECASE,
)


def _normalize_token(value: str) -> str:
    """Normalize a token for case-insensitive matching."""
    return re.sub(r"[^a-z0-9]+", "", value.lower())


@dataclass(frozen=True, slots=True)
class ParsedMention:
    """A parsed mention token."""

    mention_text: str
    mention_name: str
    mention_order: int
    start: int
    end: int

    @property
    def normalized_name(self) -> str:
        """Return the normalized mention name."""
        return _normalize_token(self.mention_name)


@dataclass(frozen=True, slots=True)
class ParsedCommand:
    """A parsed command token."""

    command_text: str
    command_name: str
    arguments: str
    start: int
    end: int


@dataclass(frozen=True, slots=True)
class ParsedMessage:
    """Parsed message structure."""

    content: str
    mentions: list[ParsedMention]
    commands: list[ParsedCommand]

    @property
    def has_command(self) -> bool:
        """Return whether the message is a command message."""
        return bool(self.commands)


class MessageParser:
    """Parse raw message text into mentions and commands."""

    def parse(self, content: str) -> ParsedMessage:
        """Parse the provided content."""
        return ParsedMessage(
            content=content,
            mentions=self._parse_mentions(content),
            commands=self._parse_commands(content),
        )

    def _parse_mentions(self, content: str) -> list[ParsedMention]:
        """Extract mentions from content in textual order."""
        mentions: list[ParsedMention] = []
        for order, match in enumerate(MENTION_PATTERN.finditer(content)):
            mention_name = match.group("name")
            mentions.append(
                ParsedMention(
                    mention_text=match.group(0),
                    mention_name=mention_name,
                    mention_order=order,
                    start=match.start(),
                    end=match.end(),
                )
            )
        return mentions

    def _parse_commands(self, content: str) -> list[ParsedCommand]:
        """Extract a leading command from content."""
        stripped = content.lstrip()
        if not stripped.startswith("/"):
            return []

        offset = len(content) - len(stripped)
        match = COMMAND_PATTERN.match(stripped)
        if match is None:
            return []

        command_name = match.group("name").lower()
        arguments = (match.group("args") or "").strip()
        return [
            ParsedCommand(
                command_text=stripped[: match.end()],
                command_name=command_name,
                arguments=arguments,
                start=offset,
                end=offset + match.end(),
            )
        ]
