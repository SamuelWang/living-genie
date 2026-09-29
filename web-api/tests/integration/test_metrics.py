from fastapi.testclient import TestClient
from prometheus_client.parser import text_string_to_metric_families


def test_metrics_endpoint_serves_prometheus_format_without_auth(client: TestClient):
    assert client.get("/health").status_code == 200

    resp = client.get("/metrics")
    assert resp.status_code == 200, resp.text

    families = {family.name: family for family in text_string_to_metric_families(resp.text)}

    # prometheus-fastapi-instrumentator's per-route baseline metrics
    assert "http_request_duration_seconds" in families
    request_samples = families["http_requests"].samples
    assert any(sample.labels.get("handler") == "/health" for sample in request_samples)

    # custom chat/RAG metrics, registered on the same default registry
    assert "living_genie_tool_calls" in families
    assert "living_genie_rag_retrieval_seconds" in families
