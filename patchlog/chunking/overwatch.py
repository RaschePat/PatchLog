from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from patchlog.tagging.rules import infer_change_type


ENTITY_HEADING_RE = re.compile(r"^###\s+(?:\[([^\]]+)\]\(([^)]+)\)|(.+?))\s*$")
SECTION_HEADING_RE = re.compile(r"^##\s+(.+?)\s*$")


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    document: str
    metadata: dict[str, Any]


@dataclass(frozen=True)
class EntityBlock:
    target: str
    section_title: str
    url: str
    body: str


def chunk_overwatch_processed_file(markdown_path: Path, meta_path: Path) -> list[Chunk]:
    markdown = markdown_path.read_text(encoding="utf-8")
    metadata = json.loads(meta_path.read_text(encoding="utf-8"))
    return chunk_overwatch_markdown(markdown, metadata)


def chunk_overwatch_markdown(markdown: str, patch_metadata: dict[str, Any]) -> list[Chunk]:
    blocks = _split_blocks(markdown)
    chunks: list[Chunk] = []
    counters: dict[str, int] = {}

    for block in blocks:
        target = _normalize_target(block.target)
        counters[target] = counters.get(target, 0) + 1
        seq = counters[target] - 1
        section = _infer_section(block)
        chunk_id = _chunk_id(
            game=patch_metadata["game"],
            patch_version=patch_metadata["patch_version"],
            target=target,
            seq=seq,
        )
        chunk_metadata = {
            "game": patch_metadata["game"],
            "patch_version": patch_metadata["patch_version"],
            "patch_date": patch_metadata["patch_date"],
            "section": section,
            "target": target,
            "change_type": infer_change_type(block.body),
            "source_url": patch_metadata["source_url"],
            "title": patch_metadata["title"],
            "lang": patch_metadata.get("lang", "ko"),
        }
        if patch_metadata.get("thumbnail_url"):
            chunk_metadata["thumbnail_url"] = patch_metadata["thumbnail_url"]
        if section == "hero" and _looks_like_image_url(block.url):
            chunk_metadata["image_url"] = block.url
            chunk_metadata["image_url_kind"] = "direct"

        document = (
            f"[{chunk_metadata['game']}] 패치 {chunk_metadata['patch_version']} - "
            f"{chunk_metadata['target']}\n\n{block.body.strip()}\n"
        )
        chunks.append(Chunk(chunk_id=chunk_id, document=document, metadata=chunk_metadata))

    return chunks


def _split_blocks(markdown: str) -> list[EntityBlock]:
    blocks: list[EntityBlock] = []
    current_section_title = "시스템"
    current_target: str | None = None
    current_url = ""
    current_lines: list[str] = []

    def flush_current() -> None:
        nonlocal current_lines
        if current_target and current_lines:
            blocks.append(
                EntityBlock(
                    target=current_target,
                    section_title=current_section_title,
                    url=current_url,
                    body="\n".join(current_lines).strip(),
                )
            )
        current_lines = []

    for line in markdown.splitlines():
        section_match = SECTION_HEADING_RE.match(line)
        if section_match:
            flush_current()
            current_target = None
            current_url = ""
            current_section_title = _clean_markdown(section_match.group(1))
            continue

        entity_match = ENTITY_HEADING_RE.match(line)
        if entity_match:
            flush_current()
            current_target = entity_match.group(1) or entity_match.group(3)
            current_url = entity_match.group(2) or ""
            current_lines = [line]
            continue

        if current_target:
            current_lines.append(line)

    flush_current()
    return [block for block in blocks if block.body.strip()]


def _infer_section(block: EntityBlock) -> str:
    if _looks_like_image_url(block.url):
        return "hero"
    compact = _compact(f"{block.section_title} {block.target}")
    if "전장" in compact or "맵" in compact:
        return "map"
    return "system"


def _chunk_id(*, game: str, patch_version: str, target: str, seq: int) -> str:
    safe_version = re.sub(r"[^0-9A-Za-z가-힣]+", "-", patch_version).strip("-").lower()
    safe_target = re.sub(r"[^0-9A-Za-z가-힣]+", "-", target).strip("-").lower()
    return f"{game}-{safe_version}-{safe_target}-{seq}"


def _normalize_target(target: str) -> str:
    return re.sub(r"\s+", " ", target).strip()


def _clean_markdown(text: str) -> str:
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    return text.replace("**", "").strip()


def _looks_like_image_url(url: str) -> bool:
    normalized = url.lower()
    return normalized.startswith("http") and any(
        ext in normalized for ext in (".png", ".jpg", ".jpeg", ".webp", ".svg")
    )


def _compact(text: str) -> str:
    return "".join(text.split()).lower()
