"""Pure chunk_text tests — no DB, no TestClient."""

from app.chunking import chunk_text


def test_empty_content_returns_no_chunks():
    assert chunk_text("", chunk_size=550, overlap=120) == []
    assert chunk_text("   \n\n  ", chunk_size=550, overlap=120) == []


def test_short_content_returns_single_chunk():
    chunks = chunk_text("Hello world", chunk_size=550, overlap=120)
    assert chunks == ["Hello world"]


def test_chunk_boundaries_respect_chunk_size():
    content = "\n\n".join(["A" * 10, "B" * 10, "C" * 10])
    chunks = chunk_text(content, chunk_size=25, overlap=0)
    assert chunks == ["A" * 10 + "\n\n" + "B" * 10, "C" * 10]
    assert all(len(chunk) <= 25 for chunk in chunks)


def test_overlap_carries_trailing_chars_into_next_chunk():
    content = "\n\n".join(["A" * 10, "B" * 10, "C" * 10])
    chunks = chunk_text(content, chunk_size=30, overlap=5)
    assert chunks == [
        "A" * 10 + "\n\n" + "B" * 10,
        "B" * 5 + "\n\n" + "C" * 10,
    ]


def test_oversized_paragraph_falls_back_to_sentence_split():
    sentences = [
        "This is sentence one.",
        "This is sentence two.",
        "This is sentence three.",
    ]
    content = " ".join(sentences)
    chunks = chunk_text(content, chunk_size=30, overlap=0)

    assert len(chunks) > 1
    assert all(len(chunk) <= 30 for chunk in chunks)
    joined = "\n\n".join(chunks)
    for sentence in sentences:
        assert sentence in joined
