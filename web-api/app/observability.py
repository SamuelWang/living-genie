import logging
import sys

import structlog
from opentelemetry import trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import TraceIdRatioBased

from app.settings import get_settings


def configure_tracing(service_name: str) -> None:
    settings = get_settings()
    resource = Resource.create({SERVICE_NAME: service_name})
    provider = TracerProvider(
        resource=resource,
        sampler=TraceIdRatioBased(settings.otel_traces_sampler_ratio),
    )
    exporter = OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint, insecure=True)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)


def _add_trace_context(logger, method_name, event_dict):
    ctx = trace.get_current_span().get_span_context()
    if ctx.is_valid:
        event_dict["trace_id"] = format(ctx.trace_id, "032x")
        event_dict["span_id"] = format(ctx.span_id, "016x")
    return event_dict


# Container healthchecks and Prometheus scrapes hit these every few seconds; their access lines
# would drown out real requests in Loki (their traffic is still visible in the request metrics).
_PROBE_PATHS = frozenset({"/health", "/metrics"})


def _drop_probe_access_logs(record: logging.LogRecord) -> bool:
    # uvicorn.access records carry (client_addr, method, full_path, http_version, status_code).
    args = record.args
    if isinstance(args, tuple) and len(args) >= 3 and isinstance(args[2], str):
        return args[2].split("?", 1)[0] not in _PROBE_PATHS
    return True


def _route_uvicorn_loggers() -> None:
    # uvicorn applies its own dictConfig before importing the app, giving these loggers plain-text
    # handlers with propagate=False; hand them over to the root logger's structured handlers.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uvicorn_logger = logging.getLogger(name)
        uvicorn_logger.handlers.clear()
        uvicorn_logger.propagate = True
    logging.getLogger("uvicorn.access").addFilter(_drop_probe_access_logs)


def configure_logging(export: bool = True) -> None:
    """Routes stdlib and structlog logging to JSON lines on stdout and, when `export` is set, to
    the OTLP endpoint too. `export=False` is for short-lived CLI processes (alembic), which would
    otherwise stall on exit retrying the export when no collector is reachable."""
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        _add_trace_context,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        # Run in the structlog chain (not just the stdout formatter) so the OTLP handler, which
        # exports the event dict as-is, also gets interpolated messages and rendered tracebacks.
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.format_exc_info,
    ]

    structlog.configure(
        processors=shared_processors + [structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            foreign_pre_chain=shared_processors,
            processors=[
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                structlog.processors.JSONRenderer(),
            ],
        )
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(stdout_handler)

    if export:
        settings = get_settings()
        resource = trace.get_tracer_provider().resource
        logger_provider = LoggerProvider(resource=resource)
        log_exporter = OTLPLogExporter(
            endpoint=settings.otel_exporter_otlp_endpoint, insecure=True
        )
        logger_provider.add_log_record_processor(BatchLogRecordProcessor(log_exporter))
        set_logger_provider(logger_provider)
        root_logger.addHandler(LoggingHandler(logger_provider=logger_provider))

    _route_uvicorn_loggers()


def get_logger(name: str):
    return structlog.get_logger(name)
