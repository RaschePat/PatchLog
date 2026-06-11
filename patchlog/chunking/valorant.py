from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from patchlog.assets.valorant import (
    valorant_agent_icon,
    valorant_agent_names,
    valorant_agent_names_in_text,
)
from patchlog.tagging.rules import infer_change_type


HEADING_RE = re.compile(r"^(#{2,4})\s+(.+?)\s*$")
AGENT_NAMES = set(valorant_agent_names())
WEAPON_KEYWORDS = ("무기", "산탄총", "소총", "권총", "스펙터", "팬텀", "밴달", "오딘", "아레스")
MAP_KEYWORDS = ("맵", "지도", "로터스", "바인드", "어센트", "스플릿", "헤이븐", "브리즈", "아이스박스")
GENERIC_TARGETS = {
    "일반 업데이트",
    "요원 업데이트",
    "맵 업데이트",
    "버그 수정",
    "알려진 문제",
    "무기 업데이트",
    "프리미어 업데이트",
}
SKIP_TARGETS = {"관련 글"}


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    document: str
    metadata: dict[str, Any]


@dataclass(frozen=True)
class EntityBlock:
    target: str
    section: str
    body: str


def chunk_valorant_processed_file(markdown_path: Path, meta_path: Path) -> list[Chunk]:
    markdown = markdown_path.read_text(encoding="utf-8")
    metadata = json.loads(meta_path.read_text(encoding="utf-8"))
    return chunk_valorant_markdown(markdown, metadata)


def chunk_valorant_markdown(markdown: str, patch_metadata: dict[str, Any]) -> list[Chunk]:
    blocks = _split_blocks(markdown)
    chunks: list[Chunk] = []
    counters: dict[str, int] = {}

    for block in blocks:
        target = _normalize_target(block.target)
        related_agents = _related_agents(target=target, body=block.body, section=block.section)
        counters[target] = counters.get(target, 0) + 1
        seq = counters[target] - 1
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
            "section": block.section,
            "target": target,
            "change_type": infer_change_type(block.body),
            "source_url": patch_metadata["source_url"],
            "title": patch_metadata["title"],
            "lang": patch_metadata.get("lang", "ko"),
        }
        if patch_metadata.get("thumbnail_url"):
            chunk_metadata["thumbnail_url"] = patch_metadata["thumbnail_url"]
        if related_agents:
            image_urls = [url for name in related_agents if (url := valorant_agent_icon(name))]
            chunk_metadata["agent_names"] = json.dumps(related_agents, ensure_ascii=False)
            chunk_metadata["agent_image_urls"] = json.dumps(image_urls, ensure_ascii=False)
            if len(related_agents) == 1 and image_urls:
                chunk_metadata["image_url"] = image_urls[0]
                chunk_metadata["image_url_kind"] = "catalog"
        document = (
            f"[{chunk_metadata['game']}] 패치 {chunk_metadata['patch_version']} - "
            f"{chunk_metadata['target']}\n\n{block.body.strip()}\n"
        )
        chunks.append(Chunk(chunk_id=chunk_id, document=document, metadata=chunk_metadata))

    return chunks


def _split_blocks(markdown: str) -> list[EntityBlock]:
    lines = markdown.splitlines()
    blocks: list[EntityBlock] = []
    current_section_title = "시스템"
    current_section = "system"
    current_block_section = "system"
    current_target: str | None = None
    current_lines: list[str] = []
    in_section = False

    def flush_current() -> None:
        nonlocal current_lines
        if not in_section or not current_lines:
            current_lines = []
            return
        target = current_target or current_section_title
        section = current_block_section if current_target else current_section
        body = "\n".join(current_lines).strip()
        if body:
            blocks.append(EntityBlock(target, section, body))
        current_lines = []

    for line in lines:
        heading = HEADING_RE.match(line)
        if heading:
            level = len(heading.group(1))
            title = _clean_heading(heading.group(2))
            if level == 2:
                flush_current()
                in_section = True
                current_section_title = title
                current_section = _section_from_text(title)
                current_block_section = current_section
                current_target = None
                continue
            if level >= 3:
                flush_current()
                in_section = True
                current_target = title
                inferred = _infer_entity_section(target=title, section_title=current_section_title, body="")
                current_block_section = inferred or current_section
                current_lines = [line]
                continue

        if in_section:
            current_lines.append(line)

    flush_current()

    expanded: list[EntityBlock] = []
    for block in blocks:
        if block.target in SKIP_TARGETS:
            continue
        for expanded_block in _expand_generic_block(block):
            expanded.extend(_split_agent_sentence_blocks(expanded_block))
    return expanded


def _section_from_text(text: str) -> str:
    compact = _compact(text)
    if "요원" in compact or "에이전트" in compact:
        return "agent"
    if any(keyword in compact for keyword in WEAPON_KEYWORDS):
        return "weapon"
    if any(keyword in compact for keyword in MAP_KEYWORDS):
        return "map"
    return "system"


def _infer_entity_section(*, target: str, section_title: str, body: str) -> str | None:
    if target in AGENT_NAMES:
        return "agent"
    if target.startswith("요원 "):
        return "agent"
    if target.startswith("무기 "):
        return "weapon"
    if target.startswith("맵 "):
        return "map"
    section = _section_from_text(section_title)
    if section != "system":
        return section
    if valorant_agent_names_in_text(f"{target} {body}"):
        return "agent"
    text = _compact(f"{target} {body}")
    if any(keyword in text for keyword in WEAPON_KEYWORDS):
        return "weapon"
    if any(keyword in text for keyword in MAP_KEYWORDS):
        return "map"
    return None


def _expand_generic_block(block: EntityBlock) -> list[EntityBlock]:
    if block.target not in GENERIC_TARGETS:
        label_blocks = _label_blocks(block.body)
        if not label_blocks:
            return [block]
        return _expanded_blocks(block, label_blocks)

    sub_blocks = _label_blocks(block.body) or _top_level_bullet_blocks(block.body)
    if not sub_blocks:
        return [block]

    return _expanded_blocks(block, sub_blocks)


def _expanded_blocks(block: EntityBlock, sub_blocks: list[tuple[str, str]]) -> list[EntityBlock]:
    meaningful_blocks = [
        (sub_target, sub_body)
        for sub_target, sub_body in sub_blocks
        if _looks_like_named_block(sub_target, sub_body, block.section)
    ]

    if not meaningful_blocks:
        return [block]

    expanded: list[EntityBlock] = []
    for sub_target, sub_body in meaningful_blocks:
        target = _generic_subtarget(block.target, sub_target)
        section = _infer_entity_section(
            target=target,
            section_title=block.target,
            body=sub_body,
        ) or block.section
        expanded.append(
            EntityBlock(
                target=target,
                section=section,
                body=f"### {target}\n\n{sub_body}".strip(),
            )
        )
    return expanded


def _split_agent_sentence_blocks(block: EntityBlock) -> list[EntityBlock]:
    if block.section != "agent" or block.target in AGENT_NAMES:
        return [block]

    bullet_lines = _change_bullet_lines(block.body)
    if not bullet_lines:
        agents = valorant_agent_names_in_text(f"{block.target} {block.body}")
        if agents:
            return [_agent_block(agents, block.body)]
        return [block]

    split_blocks: list[EntityBlock] = []
    for line in bullet_lines:
        agents = valorant_agent_names_in_text(line)
        if agents:
            split_blocks.append(_agent_block(agents, f"- {line}"))
        else:
            split_blocks.append(EntityBlock(block.target, "agent", f"### {block.target}\n\n- {line}"))
    return split_blocks or [block]


def _change_bullet_lines(body: str) -> list[str]:
    lines: list[str] = []
    for raw_line in body.splitlines():
        stripped = raw_line.strip()
        if not stripped.startswith("- "):
            continue
        text = _clean_markdown_inline(stripped.removeprefix("- "))
        if not text or text in {"요원", "에이전트"} or text in AGENT_NAMES:
            continue
        lines.append(text)
    return lines


def _agent_block(agents: list[str], body: str) -> EntityBlock:
    target = ", ".join(agents)
    return EntityBlock(target=target, section="agent", body=f"### {target}\n\n{body}".strip())


def _looks_like_named_block(target: str, body: str, fallback_section: str) -> bool:
    if _infer_entity_section(target=target, section_title="", body=body):
        return True
    if fallback_section in {"agent", "weapon", "map"} and len(target) <= 18:
        return True
    return "\n  -" in body or "\n    -" in body


def _top_level_bullet_blocks(body: str) -> list[tuple[str, str]]:
    lines = body.splitlines()
    blocks: list[tuple[str, list[str]]] = []
    current_target: str | None = None
    current_lines: list[str] = []

    for line in lines:
        if line.startswith("- "):
            if current_target and current_lines:
                blocks.append((current_target, current_lines))
            current_target = _clean_bullet_target(line.removeprefix("- "))
            current_lines = [line]
            continue
        if current_target:
            current_lines.append(line)

    if current_target and current_lines:
        blocks.append((current_target, current_lines))

    return [
        (target, "\n".join(lines).strip())
        for target, lines in blocks
        if target
    ]


def _label_blocks(body: str) -> list[tuple[str, str]]:
    lines = body.splitlines()
    blocks: list[tuple[str, list[str]]] = []
    current_target: str | None = None
    current_lines: list[str] = []

    for line in lines:
        stripped = line.strip()
        label_match = re.match(r"^([^:#]{1,24}):$", stripped)
        if label_match:
            if current_target and current_lines:
                blocks.append((current_target, current_lines))
            current_target = label_match.group(1).strip()
            current_lines = [line]
            continue
        if current_target:
            current_lines.append(line)

    if current_target and current_lines:
        blocks.append((current_target, current_lines))

    return [
        (target, "\n".join(lines).strip())
        for target, lines in blocks
        if target
    ]


def _clean_bullet_target(text: str) -> str:
    text = _clean_markdown_inline(text)
    text = text.split(":", maxsplit=1)[0]
    text = text.split(" - ", maxsplit=1)[0]
    return text.strip(" .:-")


def _generic_subtarget(parent: str, sub_target: str) -> str:
    if parent in {"버그 수정", "알려진 문제"} and sub_target in {"요원", "맵", "무기", "상점", "프리미어"}:
        return f"{sub_target} {parent}"
    return sub_target


def _chunk_id(*, game: str, patch_version: str, target: str, seq: int) -> str:
    safe_target = re.sub(r"[^0-9A-Za-z가-힣]+", "-", target).strip("-").lower()
    return f"{game}-{patch_version}-{safe_target}-{seq}"


def _normalize_target(target: str) -> str:
    return re.sub(r"\s+", " ", target).strip()


def _clean_heading(text: str) -> str:
    return _clean_markdown_inline(text).strip(" #")


def _clean_markdown_inline(text: str) -> str:
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    return text.strip()


def _related_agents(*, target: str, body: str, section: str) -> list[str]:
    if section != "agent":
        return []
    agents = valorant_agent_names_in_text(f"{target} {body}")
    if agents:
        return agents
    if target in AGENT_NAMES:
        return [target]
    return []


def _compact(text: str) -> str:
    return "".join(text.split()).lower()
