"""Pure _title_similarity scoring tests — no DB."""

from app.todo_tools import _title_similarity


def test_exact_match_scores_highest():
    assert _title_similarity("errand", "errand") == 1.0


def test_containment_either_direction_scores_high():
    assert _title_similarity("洗牙", "牙醫回診：洗牙") == 0.9
    assert _title_similarity("dentist checkup - teeth cleaning", "dentist checkup") == 0.9


def test_unrelated_titles_score_low():
    assert _title_similarity("洗牙", "買牛奶") < 0.6


def test_similar_but_distinct_titles_score_closely():
    a = _title_similarity("dentist checkup", "dentist checkup - teeth cleaning")
    b = _title_similarity("dentist checkup", "dentist checkup - annual physical")
    assert abs(a - b) < 0.15
