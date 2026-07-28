"""Pure vector_store.py ranking tests — no DB, no Qdrant, no TestClient."""

from datetime import date
from unittest.mock import MagicMock, patch

from qdrant_client import models

from app.vector_store import _hybrid_score, _recency_bonus, search


def test_recency_bonus_is_one_for_todays_entry():
    today = date(2026, 7, 28)
    assert _recency_bonus(today, today, half_life_days=180) == 1.0


def test_recency_bonus_is_half_at_half_life():
    today = date(2026, 7, 28)
    entry_date = date(2026, 1, 29)  # 180 days before today
    assert abs(_recency_bonus(entry_date, today, half_life_days=180) - 0.5) < 1e-9


def test_hybrid_score_reproduces_cosine_score_when_weight_is_zero():
    today = date(2026, 7, 28)
    old_entry = date(2020, 1, 1)
    assert (
        _hybrid_score(0.42, old_entry, today, recency_weight=0.0, half_life_days=180) == 0.42
    )


def test_hybrid_score_does_not_let_recency_overpower_strong_semantic_signal():
    today = date(2026, 7, 28)
    strong_old_match = _hybrid_score(
        0.95, date(2020, 1, 1), today, recency_weight=0.15, half_life_days=180
    )
    weak_recent_match = _hybrid_score(
        0.30, today, today, recency_weight=0.15, half_life_days=180
    )
    assert strong_old_match > weak_recent_match


def test_hybrid_score_breaks_near_ties_in_favor_of_more_recent_entry():
    today = date(2026, 7, 28)
    older_entry = _hybrid_score(
        0.80, date(2025, 11, 28), today, recency_weight=0.15, half_life_days=180
    )
    newer_entry = _hybrid_score(
        0.79, date(2026, 6, 26), today, recency_weight=0.15, half_life_days=180
    )
    assert newer_entry > older_entry


def _scored_point(point_id: str, score: float, entry_date: str) -> models.ScoredPoint:
    return models.ScoredPoint(
        id=point_id,
        version=0,
        score=score,
        payload={"entry_date": entry_date},
        vector=None,
    )


def test_search_widens_candidate_pool_and_rescues_newer_chunk_from_stale_higher_scorer():
    """Reproduces the reported bug: an older chunk with a higher cosine score should no longer
    silently exclude a newer, similarly relevant chunk once the candidate pool is widened and
    rescored with recency blended in."""
    older_higher_scoring = _scored_point("old", score=0.85, entry_date="2025-11-28")
    newer_lower_scoring = _scored_point("new", score=0.80, entry_date="2026-06-26")
    filler = [
        _scored_point(f"filler-{i}", score=0.5 - i * 0.01, entry_date="2020-01-01")
        for i in range(5)
    ]

    mock_client = MagicMock()
    mock_client.collection_exists.return_value = True
    mock_client.query_points.return_value = MagicMock(
        points=[older_higher_scoring, newer_lower_scoring, *filler]
    )

    with (
        patch("app.vector_store.get_qdrant_client", return_value=mock_client),
        patch("app.vector_store.date") as mock_date,
    ):
        mock_date.today.return_value = date(2026, 7, 28)
        mock_date.fromisoformat.side_effect = date.fromisoformat

        results = search(user_id=__import__("uuid").uuid4(), query_vector=[0.1], top_k=5)

    _, kwargs = mock_client.query_points.call_args
    assert kwargs["limit"] == 20  # retrieval_candidate_pool_size default, not top_k

    result_ids = [point.id for point in results]
    assert "new" in result_ids
    assert result_ids.index("new") < result_ids.index("old")
