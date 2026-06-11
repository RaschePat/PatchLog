from __future__ import annotations

import re
import json
from collections import defaultdict
from typing import Any

from patchlog.assets.lol import lol_entity_catalog, lol_entity_image


CARD_LIMIT_PER_PATCH = 8
GAME_THUMBNAIL_FALLBACKS = {
    "overwatch": "https://blz-contentstack-images.akamaized.net/v3/assets/blt2477dcaf4ebd440c/blt38e932b5c2f5c71a/2600_Sky_v2.jpg",
}


def build_patch_dashboard(rows: list[dict[str, Any]], *, card_limit: int = CARD_LIMIT_PER_PATCH) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        metadata = row["metadata"]
        key = (metadata["patch_version"], metadata["patch_date"])
        grouped[key].append(_change_card(row))

    patches: list[dict[str, Any]] = []
    for (patch_version, patch_date), cards in grouped.items():
        cards = sorted(cards, key=_change_sort_key)
        first = cards[0]
        patches.append(
            {
                "game": first["game"],
                "patch_version": patch_version,
                "patch_date": patch_date,
                "title": first["title"],
                "source_url": first["source_url"],
                "thumbnail_url": first.get("thumbnail_url") or GAME_THUMBNAIL_FALLBACKS.get(first["game"]),
                "change_count": len(cards),
                "changes": cards[:card_limit],
                "all_changes": cards,
                "section_counts": _section_counts(cards),
            }
        )

    return sorted(
        patches,
        key=lambda patch: (patch["patch_date"], _version_sort_key(patch["patch_version"])),
        reverse=True,
    )


def latest_patch_summary(patch: dict[str, Any]) -> str:
    return (
        f"가장 최신 패치는 {patch['title']}입니다. "
        f"총 {patch['change_count']}개의 변경 카드가 정리되어 있습니다. "
        f"[패치 {patch['patch_version']}, {patch['patch_date']}]"
    )


def _change_card(row: dict[str, Any]) -> dict[str, Any]:
    metadata = row["metadata"]
    section = metadata.get("section", "system")
    target = metadata["target"]
    catalog = lol_entity_catalog(target)
    if catalog:
        section, catalog_image_url = catalog
    else:
        catalog_image_url = lol_entity_image(target, section)
    return {
        "chunk_id": row["chunk_id"],
        "game": metadata["game"],
        "target": target,
        "section": section,
        "change_type": metadata.get("change_type", "adjust"),
        "summary": summarize_document(row["document"], target),
        "image_url": catalog_image_url or metadata.get("image_url"),
        "image_url_kind": "catalog" if catalog_image_url else metadata.get("image_url_kind"),
        "agent_names": _decode_json_list(metadata.get("agent_names")),
        "agent_image_urls": _decode_json_list(metadata.get("agent_image_urls")),
        "ability_icons": _decode_ability_icons(metadata.get("ability_icons")),
        "patch_version": metadata["patch_version"],
        "patch_date": metadata["patch_date"],
        "title": metadata.get("title", f"패치 {metadata['patch_version']}"),
        "source_url": metadata["source_url"],
        "thumbnail_url": metadata.get("thumbnail_url"),
    }


def summarize_document(document: str, target: str, *, limit: int = 220) -> str:
    focused = _focused_change_summary(document, limit=limit)
    if focused:
        return focused

    text = " ".join(document.split())
    text = re.sub(r"^\[[^\]]+\]\s+패치\s+.+?\s+-\s+", "", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = text.replace(f"### {target}", "")
    text = text.replace("####", "")
    text = text.replace("###", "")
    text = text.replace("---", " ")
    text = text.replace("**", "")
    text = text.replace("> ", "")
    text = re.sub(r"\s+", " ", text).strip(" -")
    if text.startswith(target):
        text = text[len(target) :].strip(" :-")
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."


def _focused_change_summary(document: str, *, limit: int) -> str | None:
    lines = document.splitlines()
    parts: list[str] = []
    current_heading: str | None = None
    current_heading_style = "markdown"

    for index, raw_line in enumerate(lines):
        line = raw_line.strip()
        if not line or line.startswith(">"):
            continue
        if line.startswith("#### "):
            current_heading = _clean_markdown(line.removeprefix("#### "))
            current_heading_style = "markdown"
            continue
        if _looks_like_plain_change_heading(line, lines[index + 1 : index + 4]):
            current_heading = _clean_markdown(line)
            current_heading_style = "plain"
            continue
        if line.startswith("- ") and _looks_like_change_line(line):
            change = _clean_markdown(line.removeprefix("- "))
            if current_heading and current_heading_style == "plain":
                parts.append(f"• {current_heading} - {change}")
            elif current_heading:
                parts.append(f"{current_heading} · {change}")
            else:
                parts.append(f"• {change}")
        if len(parts) >= 4:
            break

    if not parts:
        return None

    summary = "\n".join(parts)
    if len(summary) <= limit:
        return summary
    return summary[:limit].rstrip() + "..."


def _looks_like_change_line(line: str) -> bool:
    if not line.startswith("- "):
        return False
    return any(marker in line for marker in ("⇒", "→", ":", "에서", "증가", "감소", "수정", "변경"))


def _looks_like_plain_change_heading(line: str, following_lines: list[str]) -> bool:
    if line.startswith(("#", "-", "[", "*")):
        return False
    if len(line) > 36:
        return False
    return any(_looks_like_change_line(candidate.strip()) for candidate in following_lines)


def _clean_markdown(text: str) -> str:
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = text.replace("**", "")
    text = text.replace("`", "")
    text = re.sub(r"\s+", " ", text)
    return text.strip(" -")


def _change_sort_key(change: dict[str, Any]) -> tuple[int, int, str]:
    section_order = {
        "champion": 0,
        "agent": 0,
        "hero": 0,
        "item": 1,
        "weapon": 1,
        "rune": 2,
        "map": 2,
        "system": 3,
    }
    change_order = {"nerf": 0, "buff": 1, "adjust": 2, "bugfix": 3, "rework": 4, "new": 5}
    return (
        section_order.get(change["section"], 9),
        change_order.get(change["change_type"], 9),
        change["target"],
    )


def _version_sort_key(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in re.findall(r"\d+", version))


def _decode_ability_icons(raw: Any) -> dict[str, str]:
    if not raw:
        return {}
    if isinstance(raw, dict):
        return {str(key): str(value) for key, value in raw.items()}
    if isinstance(raw, str):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return {}
        if isinstance(data, dict):
            return {str(key): str(value) for key, value in data.items()}
    return {}


def _decode_json_list(raw: Any) -> list[str]:
    if not raw:
        return []
    if isinstance(raw, list):
        return [str(value) for value in raw]
    if isinstance(raw, str):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return []
        if isinstance(data, list):
            return [str(value) for value in data]
    return []


def _section_counts(cards: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for card in cards:
        section = card["section"]
        counts[section] = counts.get(section, 0) + 1
    return counts
