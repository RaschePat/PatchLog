from __future__ import annotations

from dataclasses import dataclass

from bs4 import BeautifulSoup


@dataclass(frozen=True)
class EntityAsset:
    image_url: str | None = None
    ability_icons: dict[str, str] | None = None


def extract_lol_entity_assets(html: str) -> dict[str, EntityAsset]:
    soup = BeautifulSoup(html, "html.parser")
    assets: dict[str, EntityAsset] = {}

    for title in soup.select("h3.change-title"):
        anchor = title.find("a")
        target = anchor.get_text(" ", strip=True) if anchor else title.get_text(" ", strip=True)
        if not target:
            continue

        block = title.find_parent(class_="patch-change-block") or title.parent
        image_url = _first_reference_image(block)
        ability_icons = _ability_icons(block)
        assets[target] = EntityAsset(
            image_url=image_url,
            ability_icons=ability_icons or None,
        )

    return assets


def _first_reference_image(block) -> str | None:
    if block is None:
        return None
    reference = block.select_one("a.reference-link img")
    if reference and reference.get("src"):
        return str(reference["src"])
    first_image = block.find("img")
    if first_image and first_image.get("src"):
        return str(first_image["src"])
    return None


def _ability_icons(block) -> dict[str, str]:
    if block is None:
        return {}
    icons: dict[str, str] = {}
    for heading in block.select("h4.change-detail-title"):
        image = heading.find("img")
        if not image or not image.get("src"):
            continue
        text = heading.get_text(" ", strip=True)
        if text:
            icons[text] = str(image["src"])
    return icons
