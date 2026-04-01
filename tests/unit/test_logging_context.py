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
    assert record.request_method == "-"
    assert record.request_path == "-"
    assert record.session_id == "-"
    assert record.agent_id == "-"
    assert record.job_id == "-"
    assert record.phase_id == "-"
    assert record.review_id == "-"
    assert record.runtime_pool_id == "-"
    assert record.runtime_id == "-"
    assert record.codex_thread_id == "-"
    assert record.task_id == "-"
    assert record.subscription_id == "-"
    assert record.event_type == "-"


def test_request_id_filter_uses_bound_operator_fields() -> None:
    tokens = bind_log_context(
        request_method="GET",
        request_path="/api/v1/system/status",
        session_id="ses_1",
        agent_id="agt_1",
        job_id="job_1",
        phase_id="ph_1",
        review_id="rvw_1",
        runtime_pool_id="rpl_1",
        runtime_id="rt_1",
        codex_thread_id="thr_1",
        task_id="task_1",
        subscription_id="sub_1",
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
        assert record.request_method == "GET"
        assert record.request_path == "/api/v1/system/status"
        assert record.session_id == "ses_1"
        assert record.agent_id == "agt_1"
        assert record.job_id == "job_1"
        assert record.phase_id == "ph_1"
        assert record.review_id == "rvw_1"
        assert record.runtime_pool_id == "rpl_1"
        assert record.runtime_id == "rt_1"
        assert record.codex_thread_id == "thr_1"
        assert record.task_id == "task_1"
        assert record.subscription_id == "sub_1"
        assert record.event_type == "turn.started"
    finally:
        reset_log_context(tokens)
