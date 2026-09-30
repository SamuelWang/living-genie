import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

from opentelemetry import trace

from app.observability import get_logger

WEB_API_ROOT = Path(__file__).resolve().parents[2]

# Run in a fresh interpreter: OTel's global providers can only be set once per process (app.main
# already set them for this test session), and it proves the JSON lines really go to stdout.
# os._exit skips the atexit OTLP exporter shutdown, which would otherwise retry against the
# unreachable alloy:4317 endpoint.
_LOGGING_SCRIPT = textwrap.dedent(
    """
    import json, os, sys
    from opentelemetry import trace
    from app.observability import configure_logging, configure_tracing, get_logger

    configure_tracing("test")
    configure_logging()
    logger = get_logger("tests.observability")
    logger.info("outside span")
    with trace.get_tracer("tests").start_as_current_span("test-span") as span:
        ctx = span.get_span_context()
        logger.info("inside span")
    sys.stderr.write(json.dumps(
        {"trace_id": format(ctx.trace_id, "032x"), "span_id": format(ctx.span_id, "016x")}
    ))
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(0)
    """
)


def test_configure_logging_emits_json_lines_to_stdout_with_trace_context():
    result = subprocess.run(
        [sys.executable, "-c", _LOGGING_SCRIPT],
        cwd=WEB_API_ROOT,
        env={**os.environ, "PYTHONPATH": str(WEB_API_ROOT)},
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr

    lines = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
    by_event = {line["event"]: line for line in lines}
    outside, inside = by_event["outside span"], by_event["inside span"]

    for line in (outside, inside):
        assert line["level"] == "info"
        assert line["logger"] == "tests.observability"
        assert "timestamp" in line

    assert "trace_id" not in outside
    assert "span_id" not in outside

    span_ids = json.loads(result.stderr.strip().splitlines()[-1])
    assert inside["trace_id"] == span_ids["trace_id"]
    assert inside["span_id"] == span_ids["span_id"]


def test_log_inside_span_produces_otel_log_record_with_matching_context(log_exporter):
    logger = get_logger("tests.observability")
    with trace.get_tracer("tests").start_as_current_span("test-span") as span:
        ctx = span.get_span_context()
        logger.info("otel record inside span")

    records = [
        record.log_record
        for record in log_exporter.get_finished_logs()
        if "otel record inside span" in str(record.log_record.body)
    ]
    assert len(records) == 1
    assert records[0].trace_id == ctx.trace_id
    assert records[0].span_id == ctx.span_id


# uvicorn applies its LOGGING_CONFIG (plain-text handlers, propagate=False) before importing the
# app; replay that ordering and check configure_logging() takes those loggers over.
_UVICORN_LOGGING_SCRIPT = textwrap.dedent(
    """
    import logging, logging.config, os, sys
    from uvicorn.config import LOGGING_CONFIG
    from app.observability import configure_logging, configure_tracing

    logging.config.dictConfig(LOGGING_CONFIG)
    configure_tracing("test")
    configure_logging(export=False)
    logging.getLogger("uvicorn.error").info("Application startup complete.")
    access = logging.getLogger("uvicorn.access")
    fmt = '%s - "%s %s HTTP/%s" %d'
    access.info(fmt, "10.0.0.1:1234", "GET", "/todos", "1.1", 200)
    access.info(fmt, "10.0.0.1:1234", "GET", "/metrics", "1.1", 200)
    access.info(fmt, "10.0.0.1:1234", "GET", "/health?probe=1", "1.1", 200)
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(0)
    """
)


def test_configure_logging_takes_over_uvicorn_loggers_and_drops_probe_access_lines():
    result = subprocess.run(
        [sys.executable, "-c", _UVICORN_LOGGING_SCRIPT],
        cwd=WEB_API_ROOT,
        env={**os.environ, "PYTHONPATH": str(WEB_API_ROOT)},
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    # Nothing left on uvicorn's own plain-text handlers (which write to stderr/stdout).
    assert result.stderr.strip() == ""

    lines = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
    events = {(line["logger"], line["event"]) for line in lines}
    assert events == {
        ("uvicorn.error", "Application startup complete."),
        ("uvicorn.access", '10.0.0.1:1234 - "GET /todos HTTP/1.1" 200'),
    }


_FORMATTING_SCRIPT = textwrap.dedent(
    """
    import logging, os, sys
    from app.observability import configure_logging, get_logger

    configure_logging(export=False)
    logger = get_logger("tests.observability")
    logger.info("Reset %d stuck job(s) %s", 3, "abc")
    try:
        raise ValueError("structlog failure")
    except ValueError:
        logger.exception("structlog exception %s", "c1")
    try:
        raise ValueError("stdlib failure")
    except ValueError:
        logging.getLogger("tests.stdlib").exception("stdlib exception %s", "c2")
    sys.stdout.flush()
    os._exit(0)
    """
)


def test_configure_logging_interpolates_args_and_renders_tracebacks():
    result = subprocess.run(
        [sys.executable, "-c", _FORMATTING_SCRIPT],
        cwd=WEB_API_ROOT,
        env={**os.environ, "PYTHONPATH": str(WEB_API_ROOT)},
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr

    lines = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
    by_event = {line["event"]: line for line in lines}

    assert "positional_args" not in by_event["Reset 3 stuck job(s) abc"]
    for event, message in (
        ("structlog exception c1", "structlog failure"),
        ("stdlib exception c2", "stdlib failure"),
    ):
        line = by_event[event]
        assert "exc_info" not in line
        assert line["exception"].startswith("Traceback (most recent call last):")
        assert f"ValueError: {message}" in line["exception"]


def test_otel_log_record_carries_interpolated_message_and_traceback(log_exporter):
    logger = get_logger("tests.observability")
    try:
        raise ValueError("otel failure")
    except ValueError:
        logger.exception("otel exception %s", "c3")

    bodies = [
        record.log_record.body
        for record in log_exporter.get_finished_logs()
        if "otel exception" in str(record.log_record.body)
    ]
    assert len(bodies) == 1
    assert bodies[0]["event"] == "otel exception c3"
    assert "ValueError: otel failure" in bodies[0]["exception"]
