from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from patchlog.assets.lol import ITEM_IMAGE_URLS, RUNE_IMAGE_URLS, SYSTEM_IMAGE_URLS, lol_entity_image
from patchlog.tagging.rules import infer_change_type


PATCH_ENTITY_HEADING_RE = re.compile(r"^###\s+\[([^\]]+)\]\(([^)]+)\)\s*$")
SECTION_HEADING_RE = re.compile(r"^##+\s+(.+?)\s*$")
RUNE_NAMES = {
    "콩콩이 소환",
    "여진",
    "수호자",
    "칼날비",
    "죽음불꽃 손길",
    "난입",
    "삼중 물약",
    "신비로운 유성",
    "폭풍전사의 포효",
    "환급",
}
ITEM_NAMES = {
    "꿈 생성기",
    "월석 재생기",
    "제국의 명령",
    "헬리아의 메아리",
    "강철의 솔라리 펜던트",
    "기사의 맹세",
    "지크의 융합",
    "실험적 마공학판",
    "강철심장",
    "스태틱의 단검",
    "오만",
    "무장 진격",
    "끝없는 갈망",
    "도란의 투구",
    "도란의 활",
    "리치베인",
    "벼락폭풍검",
    "사슬끈 분쇄자",
    "원칙의 원형낫",
    "원형질 안전벨트",
    "태양불꽃 방패",
    "탐욕의 군화 / 불멸의 길",
    "흐르는 물의 지팡이",
}
SYSTEM_NAMES = {
    "순간이동",
    "황혼과 새벽",
}


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    document: str
    metadata: dict[str, Any]


@dataclass(frozen=True)
class EntityBlock:
    target: str
    url: str
    body: str


def chunk_lol_processed_file(
    markdown_path: Path,
    meta_path: Path,
    asset_map: dict[str, Any] | None = None,
) -> list[Chunk]:
    markdown = markdown_path.read_text(encoding="utf-8")
    metadata = json.loads(meta_path.read_text(encoding="utf-8"))
    return chunk_lol_markdown(markdown, metadata, asset_map=asset_map)


def chunk_lol_markdown(
    markdown: str,
    patch_metadata: dict[str, Any],
    asset_map: dict[str, Any] | None = None,
) -> list[Chunk]:
    blocks = _split_champion_blocks(markdown)
    chunks: list[Chunk] = []
    counters: dict[str, int] = {}

    for entity in blocks:
        normalized_target = _normalize_target(entity.target)
        counters[normalized_target] = counters.get(normalized_target, 0) + 1
        seq = counters[normalized_target] - 1
        chunk_id = _chunk_id(
            game=patch_metadata["game"],
            patch_version=patch_metadata["patch_version"],
            target=normalized_target,
            seq=seq,
        )
        section = _infer_section(
            target=normalized_target,
            url=entity.url,
            block=entity.body,
        )
        chunk_metadata = {
            "game": patch_metadata["game"],
            "patch_version": patch_metadata["patch_version"],
            "patch_date": patch_metadata["patch_date"],
            "section": section,
            "target": normalized_target,
            "change_type": infer_change_type(entity.body),
            "source_url": patch_metadata["source_url"],
            "title": patch_metadata["title"],
            "lang": patch_metadata.get("lang", "ko"),
        }
        if patch_metadata.get("thumbnail_url"):
            chunk_metadata["thumbnail_url"] = patch_metadata["thumbnail_url"]
        asset = (asset_map or {}).get(normalized_target)
        image_url = _entity_image_url(target=normalized_target, section=section, url=entity.url, asset=asset)
        if image_url:
            chunk_metadata["image_url"] = image_url
            chunk_metadata["image_url_kind"] = _entity_image_url_kind(
                target=normalized_target,
                section=section,
                url=entity.url,
                asset=asset,
            )
        ability_icons = _entity_ability_icons(section=section, asset=asset)
        if ability_icons:
            chunk_metadata["ability_icons"] = json.dumps(ability_icons, ensure_ascii=False)
        document = (
            f"[{chunk_metadata['game']}] 패치 {chunk_metadata['patch_version']} - "
            f"{chunk_metadata['target']}\n\n{entity.body.strip()}\n"
        )
        chunks.append(Chunk(chunk_id=chunk_id, document=document, metadata=chunk_metadata))

    return chunks


def _split_champion_blocks(markdown: str) -> list[EntityBlock]:
    lines = markdown.splitlines()
    blocks: list[EntityBlock] = []
    current_target: str | None = None
    current_url: str | None = None
    current_lines: list[str] = []

    for line in lines:
        entity_match = PATCH_ENTITY_HEADING_RE.match(line)
        if entity_match:
            if current_target and current_lines:
                blocks.append(
                    EntityBlock(
                        target=current_target,
                        url=current_url or "",
                        body="\n".join(current_lines).strip(),
                    )
                )
            current_target = entity_match.group(1)
            current_url = entity_match.group(2)
            current_lines = [line]
            continue

        if current_target:
            section_match = SECTION_HEADING_RE.match(line)
            if section_match and line.startswith("## ") and not line.startswith("### "):
                blocks.append(
                    EntityBlock(
                        target=current_target,
                        url=current_url or "",
                        body="\n".join(current_lines).strip(),
                    )
                )
                current_target = None
                current_url = None
                current_lines = []
                continue
            current_lines.append(line)

    if current_target and current_lines:
        blocks.append(
            EntityBlock(
                target=current_target,
                url=current_url or "",
                body="\n".join(current_lines).strip(),
            )
        )

    return blocks


def _infer_section(*, target: str, url: str, block: str) -> str:
    normalized_url = url.lower()
    if "/champions/" in normalized_url:
        return "champion"
    if (
        target in ITEM_NAMES
        or target in ITEM_IMAGE_URLS
        or "/img/item/" in normalized_url
        or "총가격" in block
        or "조합 가격" in block
        or "골드" in block
    ):
        return "item"
    if target in RUNE_NAMES or target in RUNE_IMAGE_URLS or "핵심 룬" in block or "룬" in block:
        return "rune"
    if target in SYSTEM_NAMES or target in SYSTEM_IMAGE_URLS:
        return "system"
    return "system"


def _entity_image_url(*, target: str, section: str, url: str, asset: Any | None) -> str | None:
    catalog_url = lol_entity_image(target, section)
    if catalog_url:
        return catalog_url
    if section == "champion" and asset and getattr(asset, "image_url", None):
        return asset.image_url
    if section in {"item", "rune", "system"} and _looks_like_image_url(url):
        return url
    return None


def _entity_image_url_kind(*, target: str, section: str, url: str, asset: Any | None) -> str:
    if lol_entity_image(target, section):
        return "catalog"
    if section == "champion" and asset and getattr(asset, "image_url", None):
        return "asset"
    if section in {"item", "rune", "system"} and _looks_like_image_url(url):
        return "direct"
    return "unknown"


def _entity_ability_icons(*, section: str, asset: Any | None) -> dict[str, str]:
    if section == "champion" and asset and getattr(asset, "ability_icons", None):
        return dict(asset.ability_icons)
    return {}


def _looks_like_image_url(url: str) -> bool:
    normalized = url.lower()
    return any(ext in normalized for ext in (".png", ".jpg", ".jpeg", ".webp", ".svg"))


def _chunk_id(*, game: str, patch_version: str, target: str, seq: int) -> str:
    safe_target = re.sub(r"[^0-9A-Za-z가-힣]+", "-", target).strip("-").lower()
    return f"{game}-{patch_version}-{safe_target}-{seq}"


def _normalize_target(target: str) -> str:
    return re.sub(r"\s+", " ", target).strip()
