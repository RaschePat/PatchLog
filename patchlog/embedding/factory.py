from __future__ import annotations

from typing import Literal

from patchlog.config import settings
from patchlog.embedding.bge_m3 import BGEM3EmbeddingFunction
from patchlog.embedding.hash import HashEmbeddingFunction


EmbeddingBackend = Literal["bge-m3", "hash"]

COLLECTION_NAMES = {
    "bge-m3": "patch_notes_bge_m3",
    "hash": "patch_notes_hash",
}


def normalize_embedding_backend(backend: str | None = None) -> EmbeddingBackend:
    value = (backend or settings.embedding_backend).strip().lower()
    if value in {"bge", "bge_m3", "bgem3"}:
        value = "bge-m3"
    if value not in COLLECTION_NAMES:
        raise ValueError("Unsupported embedding backend. Use 'bge-m3' or 'hash'.")
    return value  # type: ignore[return-value]


def collection_name_for_backend(backend: str | None = None) -> str:
    return COLLECTION_NAMES[normalize_embedding_backend(backend)]


def create_embedding_function(backend: str | None = None):
    normalized = normalize_embedding_backend(backend)
    if normalized == "hash":
        return HashEmbeddingFunction()
    return BGEM3EmbeddingFunction()
