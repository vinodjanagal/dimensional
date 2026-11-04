
import json
import logging
import sys

import pytest

from app.core.logging import (
    JsonFormatter,
    configure_logging,
    request_id_var,
)


def make_record(message: str, **extra) -> logging.LogRecord:
    """Create a log record without configuring global logging."""
    return logging.getLogger("test.logging").makeRecord(
        name="test.logging",
        level=logging.INFO,
        fn=__file__,
        lno=10,
        msg=message,
        args=(),
        exc_info=None,
        extra=extra,
    )


def test_json_formatter_includes_standard_and_custom_fields():
    record = make_record(
        "http.request.completed",
        event="http.request.completed",
        status_code=200,
        duration_ms=12.5,
    )

    output = JsonFormatter().format(record)
    parsed = json.loads(output)

    assert parsed["level"] == "INFO"
    assert parsed["logger"] == "test.logging"
    assert parsed["message"] == "http.request.completed"
    assert parsed["event"] == "http.request.completed"
    assert parsed["status_code"] == 200
    assert parsed["duration_ms"] == 12.5
    assert parsed["timestamp"].endswith("Z")


def test_json_formatter_includes_request_id_from_context():
    token = request_id_var.set("test-request-123")

    try:
        output = JsonFormatter().format(make_record("request.processed"))
        parsed = json.loads(output)

        assert parsed["request_id"] == "test-request-123"
    finally:
        request_id_var.reset(token)


def test_json_formatter_omits_request_id_when_context_is_empty():
    token = request_id_var.set(None)

    try:
        output = JsonFormatter().format(make_record("application.started"))
        parsed = json.loads(output)

        assert "request_id" not in parsed
    finally:
        request_id_var.reset(token)


def test_json_formatter_includes_exception_traceback():
    try:
        raise ValueError("example failure")
    except ValueError:
        record = logging.getLogger("test.logging").makeRecord(
            name="test.logging",
            level=logging.ERROR,
            fn=__file__,
            lno=20,
            msg="operation.failed",
            args=(),
            exc_info=sys.exc_info(),
        )

    parsed = json.loads(JsonFormatter().format(record))

    assert parsed["message"] == "operation.failed"
    assert "exception" in parsed
    assert "ValueError: example failure" in parsed["exception"]


def test_json_formatter_does_not_allow_extra_fields_to_overwrite_metadata():
    record = make_record(
        "actual.message",
        timestamp="fake timestamp",
        level="FAKE",
        logger="fake.logger",
    )

    parsed = json.loads(JsonFormatter().format(record))

    assert parsed["message"] == "actual.message"
    assert parsed["level"] == "INFO"
    assert parsed["logger"] == "test.logging"
    assert parsed["timestamp"] != "fake timestamp"


def test_configure_logging_rejects_invalid_level():
    with pytest.raises(ValueError, match="Invalid logging level"):
        configure_logging("NOT_A_REAL_LEVEL")