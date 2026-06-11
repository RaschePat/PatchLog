from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal


Game = Literal["lol", "valorant", "overwatch"]


@dataclass(frozen=True)
class ChatMessage:
    role: Literal["user", "assistant"]
    content: str


@dataclass(frozen=True)
class PatchChunk:
    chunk_id: str
    game: Game
    patch_version: str
    patch_date: str
    target: str
    change_type: str
    source_url: str
    content: str
    section: str = "champion"

    def source_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data.pop("content")
        return data


@dataclass(frozen=True)
class QueryAnalysis:
    query: str
    filter: dict[str, Any]


@dataclass(frozen=True)
class ChatResult:
    answer: str
    sources: list[dict[str, Any]]
    navigation_target: dict[str, Any] | None
    debug_trace: dict[str, Any] | None = None
