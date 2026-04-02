from __future__ import annotations

import re
from pathlib import Path


def test_operator_ui_incident_summary_render_contract() -> None:
    html = (Path(__file__).resolve().parents[2] / "ui" / "index.html").read_text(encoding="utf-8")
    normalized = html.replace("\r\n", "\n")
    selected_session_pattern = (
        r'nodes\.selectedSession\.innerHTML = \'<div class="empty">'
        r"Select a session from the rail to inspect its detail surface\."
        r"</div>\';\s*"
        r"renderIncidentSummary\(\);\s*"
        r"return;"
    )
    no_session_activity_pattern = (
        r'nodes\.activitySignals\.innerHTML = \'<div class="empty">'
        r"Select a session to stream live activity\."
        r"</div>\';\s*"
        r'nodes\.activityFeed\.innerHTML = \'<div class="empty">'
        r"Activity feed appears after a session is selected\."
        r"</div>\';\s*"
        r"renderIncidentSummary\(\);\s*"
        r"return;"
    )
    rendered_activity_pattern = (
        r"nodes\.activityFeed\.innerHTML = renderTimelineFeed\(feed\);\s*"
        r"renderIncidentSummary\(\);"
    )

    assert re.search(
        selected_session_pattern,
        normalized,
        re.S,
    )
    assert re.search(
        no_session_activity_pattern,
        normalized,
        re.S,
    )
    assert re.search(rendered_activity_pattern, normalized, re.S)
