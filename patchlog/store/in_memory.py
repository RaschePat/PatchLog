from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from patchlog.models import PatchChunk
from patchlog.sample_corpus import SAMPLE_CHUNKS


class InMemoryPatchStore:
    def __init__(self, chunks: Iterable[PatchChunk] | None = None) -> None:
        self._chunks = list(chunks or SAMPLE_CHUNKS)

    def search(self, query: str, filter_data: dict[str, Any], top_k: int) -> list[PatchChunk]:
        candidates = [chunk for chunk in self._chunks if _matches_filter(chunk, filter_data)]
        scored = sorted(
            ((self._score(chunk, query, filter_data), chunk) for chunk in candidates),
            key=lambda item: (item[0], item[1].patch_date),
            reverse=True,
        )
        return [chunk for score, chunk in scored if score > 0][:top_k]

    @staticmethod
    def _score(chunk: PatchChunk, query: str, filter_data: dict[str, Any]) -> int:
        score = 0
        if filter_data.get("target") == chunk.target:
            score += 8
        if filter_data.get("change_type") == chunk.change_type:
            score += 4
        if filter_data.get("section") == chunk.section:
            score += 3
        if filter_data.get("patch_version") == chunk.patch_version:
            score += 3
        for token in _tokens(query):
            if (
                token in chunk.content
                or token in chunk.target
                or token in chunk.change_type
                or token in chunk.patch_version
                or token in chunk.section
            ):
                score += 1
        return score


def _matches_filter(chunk: PatchChunk, filter_data: dict[str, Any]) -> bool:
    for key, expected in filter_data.items():
        if getattr(chunk, key) != expected:
            return False
    return True


def _tokens(query: str) -> list[str]:
    return [token.strip(" ?!.,") for token in query.split() if token.strip(" ?!.,")]
