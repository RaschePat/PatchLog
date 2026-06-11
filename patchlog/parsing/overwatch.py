from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup


@dataclass(frozen=True)
class ParsedPatch:
    markdown: str
    metadata: dict[str, Any]


def parse_overwatch_patch_html(html: str, *, source_url: str) -> ParsedPatch:
    soup = BeautifulSoup(html, "html.parser")
    patch_node = soup.select_one(".PatchNotes-patch") or soup
    title = _clean_text(_text(patch_node.select_one(".PatchNotes-patchTitle"))) or "오버워치 패치 노트"
    patch_date = _extract_patch_date(patch_node)
    if patch_date is None:
        raise ValueError("Could not extract Overwatch patch date")

    markdown = _patch_to_markdown(patch_node, title)
    metadata = {
        "game": "overwatch",
        "patch_version": patch_date,
        "patch_date": patch_date,
        "source_url": source_url,
        "title": title,
        "lang": "ko",
    }
    return ParsedPatch(markdown=markdown, metadata=metadata)


def write_processed_patch(parsed: ParsedPatch, processed_dir: Path) -> None:
    processed_dir.mkdir(parents=True, exist_ok=True)
    patch_version = parsed.metadata["patch_version"]
    md_path = processed_dir / f"{patch_version}.md"
    meta_path = processed_dir / f"{patch_version}.meta.json"
    md_path.write_text(parsed.markdown, encoding="utf-8")
    meta_path.write_text(
        json.dumps(parsed.metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _patch_to_markdown(patch_node, title: str) -> str:
    lines = [f"# {title}", ""]
    date_text = _clean_text(_text(patch_node.select_one(".PatchNotes-date")))
    if date_text:
        lines.extend([date_text, ""])

    for section in patch_node.select(".PatchNotes-section"):
        section_title = _clean_text(_text(section.select_one(".PatchNotes-sectionTitle")))
        if not section_title:
            continue
        lines.extend([f"## {section_title}", ""])
        section_description = _description_lines(section.select_one(".PatchNotes-sectionDescription"))
        has_structured_updates = bool(
            section.select_one(".PatchNotesHeroUpdate")
            or section.select_one(".PatchNotesGeneralUpdate")
        )
        if section_description and not has_structured_updates:
            lines.extend([f"### {section_title}", ""])
        lines.extend(section_description)

        for hero in section.select(".PatchNotesHeroUpdate"):
            hero_name = _clean_text(_text(hero.select_one(".PatchNotesHeroUpdate-name")))
            if not hero_name:
                continue
            icon = _hero_icon(hero)
            heading = f"### [{hero_name}]({icon})" if icon else f"### {hero_name}"
            lines.extend([heading, ""])
            lines.extend(_description_lines(hero.select_one(".PatchNotes-dev")))
            lines.extend(_description_lines(hero.select_one(".PatchNotesHeroUpdate-generalUpdates")))
            for ability in hero.select(".PatchNotesAbilityUpdate"):
                ability_name = _clean_text(_text(ability.select_one(".PatchNotesAbilityUpdate-name")))
                if ability_name:
                    lines.extend([f"#### {ability_name}", ""])
                lines.extend(_description_lines(ability.select_one(".PatchNotesAbilityUpdate-detailList")))

        for general in section.select(".PatchNotesGeneralUpdate"):
            target = _clean_text(_text(general.select_one(".PatchNotesGeneralUpdate-title")))
            if target:
                lines.extend([f"### {target}", ""])
            lines.extend(_description_lines(general.select_one(".PatchNotesGeneralUpdate-description")))

    compact: list[str] = []
    previous_blank = False
    for line in lines:
        blank = not line.strip()
        if blank and previous_blank:
            continue
        compact.append(line.rstrip())
        previous_blank = blank
    return "\n".join(compact).strip() + "\n"


def _description_lines(node) -> list[str]:
    if node is None:
        return []
    lines: list[str] = []
    for child in node.children:
        name = getattr(child, "name", None)
        if name == "p":
            text = _clean_text(child.get_text(" ", strip=True))
            if text:
                lines.extend([text, ""])
        elif name in {"ul", "ol"}:
            lines.extend(_list_lines(child))
            if lines and lines[-1] != "":
                lines.append("")
    return lines


def _list_lines(list_node, *, indent: int = 0) -> list[str]:
    lines: list[str] = []
    for item in list_node.find_all("li", recursive=False):
        nested_lists = item.find_all(["ul", "ol"], recursive=False)
        for nested in nested_lists:
            nested.extract()
        text = _clean_text(item.get_text(" ", strip=True))
        if text:
            lines.append(f"{'  ' * indent}- {text}")
        for nested in nested_lists:
            lines.extend(_list_lines(nested, indent=indent + 1))
    return lines


def _extract_patch_date(patch_node) -> str | None:
    title = _text(patch_node.select_one(".PatchNotes-patchTitle"))
    date = _date_from_korean_text(title)
    if date:
        return date
    date_label = _text(patch_node.select_one(".PatchNotes-date"))
    return _date_from_korean_text(date_label)


def _date_from_korean_text(text: str) -> str | None:
    match = re.search(r"(20\d{2})년\s*(\d{1,2})월\s*(\d{1,2})일", text)
    if not match:
        return None
    year, month, day = match.groups()
    return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"


def _hero_icon(hero_node) -> str | None:
    image = hero_node.select_one(".PatchNotesHeroUpdate-icon")
    if image and image.get("src"):
        return str(image["src"])
    return None


def _text(node) -> str:
    return node.get_text(" ", strip=True) if node is not None else ""


def _clean_text(text: str) -> str:
    return " ".join(text.split())
