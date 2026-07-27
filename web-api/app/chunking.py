import re

_PARAGRAPH_SPLIT_RE = re.compile(r"\n\s*\n+")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?。！？])\s*")


def chunk_text(content: str, chunk_size: int, overlap: int) -> list[str]:
    paragraphs = [p.strip() for p in _PARAGRAPH_SPLIT_RE.split(content.strip()) if p.strip()]
    if not paragraphs:
        return []
    units: list[str] = []
    for paragraph in paragraphs:
        units.extend(_split_oversized(paragraph, chunk_size))
    return _pack(units, chunk_size, overlap)


def _split_oversized(text: str, chunk_size: int) -> list[str]:
    if len(text) <= chunk_size:
        return [text]
    sentences = [s.strip() for s in _SENTENCE_SPLIT_RE.split(text) if s.strip()]
    if len(sentences) <= 1:
        return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]
    units: list[str] = []
    for sentence in sentences:
        units.extend(_split_oversized(sentence, chunk_size))
    return units


def _pack(units: list[str], chunk_size: int, overlap: int) -> list[str]:
    chunks: list[str] = []
    current = ""
    for unit in units:
        candidate = f"{current}\n\n{unit}" if current else unit
        if len(candidate) <= chunk_size:
            current = candidate
            continue
        if current:
            chunks.append(current)
        carry = current[-overlap:] if overlap > 0 and current else ""
        current = f"{carry}\n\n{unit}" if carry else unit
        if len(current) > chunk_size:
            current = unit
    if current:
        chunks.append(current)
    return chunks
