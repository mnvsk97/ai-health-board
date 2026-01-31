"""Embedding generation using OpenAI-compatible API (TrueFoundry gateway)."""

from __future__ import annotations

from typing import Iterable

from openai import OpenAI

from .config import load_settings

DEFAULT_EMBEDDING_DIMENSIONS = 3072  # text-embedding-3-large


def _get_embedding_config() -> dict[str, object]:
    """Get embedding configuration from settings."""
    settings = load_settings()
    return {
        "api_key": settings.get("openai_api_key"),
        "base_url": settings.get("openai_base_url"),
        "model": str(settings.get("openai_embedding_model") or "text-embedding-3-large"),
        "dimensions": int(settings.get("embedding_dimensions") or DEFAULT_EMBEDDING_DIMENSIONS),
    }


def generate_embedding(text: str) -> list[float]:
    """Generate embedding for a single text string."""
    return generate_embeddings([text])[0]


def generate_embeddings(texts: Iterable[str]) -> list[list[float]]:
    """Generate embeddings for multiple texts."""
    texts_list = [t for t in texts if t]
    if not texts_list:
        return []

    cfg = _get_embedding_config()

    client = OpenAI(
        api_key=str(cfg["api_key"]),
        base_url=str(cfg["base_url"]) if cfg["base_url"] else None,
    )

    response = client.embeddings.create(
        input=texts_list,
        model=str(cfg["model"]),
        dimensions=int(cfg["dimensions"]),
    )

    # Sort by index to maintain order
    sorted_data = sorted(response.data, key=lambda x: x.index)
    return [item.embedding for item in sorted_data]
