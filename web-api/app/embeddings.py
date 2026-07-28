from functools import lru_cache
from typing import Literal

from ollama import Client

from app.settings import get_settings

_PROMPT_PREFIXES: dict[str, str] = {
    "query": "task: search result | query: ",
    "passage": "title: none | text: ",
}


@lru_cache
def get_ollama_client() -> Client:
    return Client(host=get_settings().ollama_url)


def embed_texts(texts: list[str], kind: Literal["query", "passage"]) -> list[list[float]]:
    if not texts:
        return []
    prefixed = [_PROMPT_PREFIXES[kind] + text for text in texts]
    response = get_ollama_client().embed(model=get_settings().ollama_embedding_model, input=prefixed)
    return response.embeddings
