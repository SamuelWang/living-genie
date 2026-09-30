import uuid

import httpx
from opentelemetry.trace import StatusCode
from prometheus_client import start_http_server
from prometheus_client.parser import text_string_to_metric_families
from sqlalchemy import select
from sqlalchemy.orm import Session

import app.worker as worker
from app.db import SessionLocal
from app.models import EmbeddingJob
from tests.conftest import AuthedUser

_STAGE_SPANS = ("job.chunk", "job.embed_chunks", "job.qdrant_upsert")


def _job_for_entry(db_session: Session, entry_id: uuid.UUID) -> EmbeddingJob:
    return db_session.scalar(
        select(EmbeddingJob).where(
            EmbeddingJob.source_id == entry_id, EmbeddingJob.source_type == "diary_entry"
        )
    )


def _create_entry(authed_user: AuthedUser) -> uuid.UUID:
    resp = authed_user.client.post(
        "/diaries", json={"title": "Trip", "content": "Went hiking today. It was fun."}
    )
    return uuid.UUID(resp.json()["id"])


def _job_span(span_exporter):
    (job_span,) = [s for s in span_exporter.get_finished_spans() if s.name == "job.process"]
    return job_span


def _stage_spans(span_exporter) -> dict:
    return {
        span.name: span
        for span in span_exporter.get_finished_spans()
        if span.name in _STAGE_SPANS
    }


def test_worker_metrics_server_exposes_job_metrics(
    authed_user: AuthedUser, db_session: Session, fake_vector_store, fake_ollama_client
):
    _create_entry(authed_user)
    assert worker.process_next_job(db_session) is True

    # Same start_http_server call worker.main() makes, on an ephemeral port so it can't clash
    # with a locally running worker on WORKER_METRICS_PORT.
    server, thread = start_http_server(0)
    try:
        resp = httpx.get(f"http://localhost:{server.server_port}/metrics")
    finally:
        server.shutdown()
        thread.join()

    assert resp.status_code == 200
    families = {family.name: family for family in text_string_to_metric_families(resp.text)}
    assert "living_genie_worker_job_duration_seconds" in families
    assert any(
        sample.labels == {"source_type": "diary_entry", "status": "completed"}
        for sample in families["living_genie_worker_jobs"].samples
    )


def test_worker_job_emits_stage_spans_tagged_with_source(
    authed_user: AuthedUser,
    db_session: Session,
    fake_vector_store,
    fake_ollama_client,
    span_exporter,
):
    entry_id = _create_entry(authed_user)
    assert worker.process_next_job(db_session) is True

    spans = _stage_spans(span_exporter)
    assert set(spans) == set(_STAGE_SPANS)
    for span in spans.values():
        assert span.attributes["source_type"] == "diary_entry"
        assert span.attributes["source_id"] == str(entry_id)
        assert span.status.status_code != StatusCode.ERROR
    assert spans["job.embed_chunks"].attributes["chunk_count"] >= 1

    # One trace per job: every stage, and the job's own Postgres bookkeeping, hangs off the
    # job.process root span.
    job_span = _job_span(span_exporter)
    assert job_span.parent is None
    assert job_span.attributes["source_type"] == "diary_entry"
    assert job_span.attributes["source_id"] == str(entry_id)
    assert job_span.attributes["job.status"] == "completed"
    trace_id = job_span.context.trace_id
    in_trace = [s for s in span_exporter.get_finished_spans() if s.context.trace_id == trace_id]
    assert {s.name for s in in_trace} >= {"job.process", *_STAGE_SPANS}
    assert any(s.attributes.get("db.system") == "postgresql" for s in in_trace)
    for span in spans.values():
        assert span.parent.span_id == job_span.context.span_id


def test_idle_worker_poll_exports_no_spans(db_session: Session, span_exporter):
    assert worker.process_next_job(db_session) is False
    assert span_exporter.get_finished_spans() == ()


def test_failed_worker_job_records_exception_on_failing_stage_span(
    authed_user_real_commits: AuthedUser, fake_vector_store, fake_ollama_client, span_exporter
):
    # Real, non-nested session: the failure path's db.rollback() would otherwise unwind the
    # `db_session` fixture's SAVEPOINT (see test_worker.py's failure-path test).
    entry_id = _create_entry(authed_user_real_commits)
    fake_vector_store.fail_upsert = True

    db = SessionLocal()
    try:
        assert _job_for_entry(db, entry_id) is not None
        assert worker.process_next_job(db) is True
    finally:
        db.close()

    spans = _stage_spans(span_exporter)
    upsert = spans["job.qdrant_upsert"]
    assert upsert.status.status_code == StatusCode.ERROR
    exception_events = [event for event in upsert.events if event.name == "exception"]
    assert len(exception_events) == 1
    assert exception_events[0].attributes["exception.message"] == "fake upsert failure"

    assert spans["job.chunk"].status.status_code != StatusCode.ERROR
    assert spans["job.embed_chunks"].status.status_code != StatusCode.ERROR

    # The failing stage sits in the same trace as the job's root span, which is marked failed too.
    job_span = _job_span(span_exporter)
    assert upsert.context.trace_id == job_span.context.trace_id
    assert job_span.status.status_code == StatusCode.ERROR
    assert job_span.attributes["job.status"] == "pending"  # first attempt; will be retried
