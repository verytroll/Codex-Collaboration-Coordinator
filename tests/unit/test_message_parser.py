from __future__ import annotations

from app.services.message_parser import MessageParser


def test_message_parser_extracts_mentions_and_ignores_nonleading_slash_text() -> None:
    parser = MessageParser()

    parsed = parser.parse("#builder fix this bug /interrupt now")

    assert [mention.mention_text for mention in parsed.mentions] == ["#builder"]
    assert [mention.mention_name for mention in parsed.mentions] == ["builder"]
    assert [command.command_name for command in parsed.commands] == []


def test_message_parser_extracts_leading_command_arguments() -> None:
    parser = MessageParser()

    parsed = parser.parse("/new #planner split the task into 3 steps")

    assert parsed.has_command is True
    assert [command.command_name for command in parsed.commands] == ["new"]
    assert parsed.commands[0].arguments == "#planner split the task into 3 steps"
    assert parsed.mentions[0].mention_text == "#planner"
