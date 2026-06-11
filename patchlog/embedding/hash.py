from __future__ import annotations

import hashlib
import math
from collections.abc import Iterable


class HashEmbeddingFunction:
    """Small deterministic embedding function for local Chroma development.

    This keeps M2 runnable without downloading a large model. The interface is
    intentionally compatible with Chroma's embedding_function hook so BGE-M3 can
    replace it later without changing indexing/search orchestration.
    """

    def __init__(self, dimensions: int = 384) -> None:
        self.dimensions = dimensions

    @staticmethod
    def name() -> str:
        return "patchlog_hash"

    @staticmethod
    def is_legacy() -> bool:
        return False

    def get_config(self) -> dict[str, int]:
        return {"dimensions": self.dimensions}

    def __call__(self, input: list[str]) -> list[list[float]]:  # Chroma protocol.
        return [self.embed(text) for text in input]

    def embed_documents(self, input: Iterable[str]) -> list[list[float]]:
        return [self.embed(text) for text in input]

    def embed_query(self, input: list[str]) -> list[list[float]]:
        return [self.embed(text) for text in input]

    @staticmethod
    def supported_spaces() -> list[str]:
        return ["cosine"]

    @staticmethod
    def default_space() -> str:
        return "cosine"

    @classmethod
    def build_from_config(cls, config: dict[str, int]) -> "HashEmbeddingFunction":
        return cls(dimensions=config.get("dimensions", 384))

    def validate_config_update(
        self,
        old_config: dict[str, int],
        new_config: dict[str, int],
    ) -> None:
        if old_config.get("dimensions") != new_config.get("dimensions"):
            raise ValueError("Hash embedding dimensions cannot be changed in-place")

    def embed_texts(self, texts: Iterable[str]) -> list[list[float]]:
        return [self.embed(text) for text in texts]

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        for token in _tokens(text):
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "little") % self.dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign

        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [value / norm for value in vector]


def _tokens(text: str) -> list[str]:
    normalized = text.lower()
    words = [word.strip(".,!?()[]{}:;\"'`*_") for word in normalized.split()]
    char_grams: list[str] = []
    compact = "".join(ch for ch in normalized if not ch.isspace())
    for size in (2, 3):
        char_grams.extend(compact[index : index + size] for index in range(len(compact) - size + 1))
    return [word for word in words if word] + char_grams
