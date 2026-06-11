from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PatchArticle:
    game: str
    title: str
    url: str
    patch_version: str
    patch_date: str | None = None


@dataclass(frozen=True)
class CollectedPatch:
    article: PatchArticle
    html: str


class BaseCollector:
    game: str

    def list_patches(
        self,
        *,
        limit: int,
        since: str | None = None,
    ) -> list[PatchArticle]:
        raise NotImplementedError

    def fetch_patch(self, article: PatchArticle) -> CollectedPatch:
        raise NotImplementedError

    def collect(
        self,
        *,
        output_root: Path,
        limit: int,
        since: str | None = None,
        force: bool = False,
    ) -> list[Path]:
        raise NotImplementedError

