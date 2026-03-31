from __future__ import annotations

import logging

from app.core.logging import RequestIdFilter, bind_log_context, reset_log_context


def test_request_id_filter_injects_default_operator_fields() -> None:
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="hello",
        args=(),
        exc_info=None,
    )

    assert RequestIdFilter().filter(record) is True
    assert record.request_id == "-"
    assert record.session_id == "-"
    assert record.agent_id == "-"
    assert record.job_id == "-"
    assert record.codex_thread_id == "-"
    assert record.event_type == "-"



def test_request_id_filter_uses_bound_operator_fields() -> None:
    tokens = bind_log_context(
        session_id="ses_1",
        agent_id="agt_1",
        job_id="job_1",
        codex_thread_id="thr_1",
        event_type="turn.started",
    )
    try:
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="hello",
            args=(),
            exc_info=None,
        )
        RequestIdFilter().filter(record)
        assert record.session_id == "ses_1"
        assert record.agent_id == "agt_1"
        assert record.job_id == "job_1"
        assert record.codex_thread_id == "thr_1"
        assert record.event_type == "turn.started"
    finally:
        reset_log_context(tokens)
