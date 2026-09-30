import time

from opentelemetry import trace
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.utils import suppress_instrumentation
from opentelemetry.trace import Span, Status, StatusCode
from prometheus_client import Counter, Histogram, start_http_server
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.chunking import chunk_text
from app.db import SessionLocal, engine
from app.embeddings import embed_texts
from app.models import DiaryEntry, EmbeddingJob, Todo
from app.observability import configure_logging, configure_tracing, get_logger
from app.settings import get_settings
from app.vector_store import ensure_collection, upsert_chunks

logger = get_logger(__name__)
tracer = trace.get_tracer(__name__)

JOB_COUNTER = Counter(
    "living_genie_worker_jobs_total",
    "Embedding jobs processed by the worker, broken down by source type and final status.",
    ["source_type", "status"],
)
JOB_DURATION = Histogram(
    "living_genie_worker_job_duration_seconds",
    "Duration of the chunk/embed/upsert stage of embedding job processing, by source type.",
    ["source_type"],
)


def reset_stuck_jobs(db: Session) -> int:
    result = db.execute(
        update(EmbeddingJob).where(EmbeddingJob.status == "processing").values(status="pending")
    )
    db.commit()
    return result.rowcount


def process_next_job(db: Session) -> bool:
    stmt = (
        select(EmbeddingJob)
        .where(EmbeddingJob.status == "pending")
        .order_by(EmbeddingJob.created_at)
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    # Polling is untraced: otherwise every idle poll exports its own single-span SELECT trace,
    # burying the real job traces in Tempo.
    with suppress_instrumentation():
        job = db.scalars(stmt).first()
        if job is None:
            db.rollback()
            return False

    # One root span per job, so the status bookkeeping queries and every stage span (with their
    # Postgres/Ollama/Qdrant children) land in a single trace.
    with tracer.start_as_current_span(
        "job.process",
        attributes={
            "job.id": str(job.id),
            "source_type": job.source_type,
            "source_id": str(job.source_id),
        },
    ) as job_span:
        _process_job(db, job, job_span)
    return True


def _process_job(db: Session, job: EmbeddingJob, job_span: Span) -> None:
    job.status = "processing"
    db.commit()

    if job.source_type == "diary_entry":
        source = db.get(DiaryEntry, job.source_id)
    else:
        source = db.get(Todo, job.source_id)
    if source is None:
        logger.info("%s %s gone; skipping job %s", job.source_type, job.source_id, job.id)
        job_span.set_attribute("job.status", "skipped")
        return

    settings = get_settings()
    span_attrs = {"source_type": job.source_type, "source_id": str(job.source_id)}
    start = time.perf_counter()
    try:
        # Each stage span records the exception and sets ERROR status as it propagates out, before
        # the except block's failure bookkeeping runs, so a failed job's trace shows its stage.
        with _stage_span("job.chunk", span_attrs):
            if job.source_type == "diary_entry":
                composed = (
                    f"{source.title}\n\n{source.content}" if source.content else source.title
                )
                chunks = chunk_text(
                    composed, settings.embedding_chunk_size, settings.embedding_chunk_overlap
                )
                source_date = source.entry_date
            else:
                status_text = "done" if source.completed else "pending"
                composed = f"{source.title}\n{source.description or ''}\nStatus: {status_text}"
                chunks = chunk_text(
                    composed, settings.embedding_chunk_size, settings.embedding_chunk_overlap
                )
                source_date = source.due_date or source.created_at.date()
        with _stage_span("job.embed_chunks", span_attrs) as span:
            span.set_attribute("chunk_count", len(chunks))
            vectors = embed_texts(chunks, kind="passage") if chunks else []
        with _stage_span("job.qdrant_upsert", span_attrs):
            upsert_chunks(
                job.source_type, job.source_id, source.user_id, source_date, chunks, vectors
            )
        job.status = "completed"
        db.commit()
    except Exception as exc:
        db.rollback()
        job_span.set_status(Status(StatusCode.ERROR, str(exc)))
        _fail_job(db, job.id, exc)
    finally:
        JOB_DURATION.labels(source_type=job.source_type).observe(time.perf_counter() - start)
        JOB_COUNTER.labels(source_type=job.source_type, status=job.status).inc()
        job_span.set_attribute("job.status", job.status)


def _stage_span(name: str, attributes: dict[str, str]):
    return tracer.start_as_current_span(
        name, attributes=attributes, record_exception=True, set_status_on_exception=True
    )


def _fail_job(db: Session, job_id, exc: Exception) -> None:
    job = db.get(EmbeddingJob, job_id)
    if job is None:
        return
    job.attempts += 1
    if job.attempts < get_settings().embedding_job_max_attempts:
        job.status = "pending"
    else:
        job.status = "failed"
        job.error_message = str(exc)
    db.commit()


def startup() -> None:
    db = SessionLocal()
    try:
        reset_count = reset_stuck_jobs(db)
    finally:
        db.close()
    if reset_count:
        logger.info("Reset %d stuck job(s) from processing to pending", reset_count)
    ensure_collection()


def run_forever() -> None:
    poll_interval = get_settings().embedding_job_poll_interval_seconds
    while True:
        db = SessionLocal()
        try:
            processed = process_next_job(db)
        finally:
            db.close()
        if not processed:
            time.sleep(poll_interval)


def main() -> None:
    configure_tracing("worker")
    configure_logging()
    SQLAlchemyInstrumentor().instrument(engine=engine)
    HTTPXClientInstrumentor().instrument()
    start_http_server(get_settings().worker_metrics_port)
    startup()
    run_forever()


if __name__ == "__main__":
    main()
