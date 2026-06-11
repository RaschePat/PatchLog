from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup

from patchlog.collectors.lol import extract_patch_version

try:
    from markdownify import markdownify as html_to_markdown
except Exception:  # pragma: no cover - fallback for minimal environments.
    html_to_markdown = None


@dataclass(frozen=True)
class ParsedPatch:
    markdown: str
    metadata: dict[str, Any]


def parse_lol_patch_html(html: str, *, source_url: str) -> ParsedPatch:
    soup = BeautifulSoup(html, "html.parser")
    title = _extract_title(soup)
    patch_version = extract_patch_version(title) or extract_patch_version(source_url)
    if patch_version is None:
        raise ValueError("Could not extract LoL patch version from page")

    patch_date = _extract_patch_date(soup)
    if patch_date is None:
        raise ValueError("Could not extract LoL patch date from page")

    body = _extract_article_body(soup)
    markdown = _to_markdown(body)
    metadata = {
        "game": "lol",
        "patch_version": patch_version,
        "patch_date": patch_date,
        "source_url": source_url,
        "title": title,
        "lang": "ko",
    }
    thumbnail_url = _extract_thumbnail_url(soup)
    if thumbnail_url:
        metadata["thumbnail_url"] = thumbnail_url
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


def _extract_title(soup: BeautifulSoup) -> str:
    h1 = soup.find("h1")
    if h1:
        return _clean_text(h1.get_text(" ", strip=True))

    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content"):
        return _clean_text(str(og_title["content"]))

    title = soup.find("title")
    if title:
        return _clean_text(title.get_text(" ", strip=True))

    raise ValueError("Could not extract LoL patch title from page")


def _extract_patch_date(soup: BeautifulSoup) -> str | None:
    for tag in soup.find_all("time"):
        datetime_value = tag.get("datetime")
        if datetime_value:
            parsed = _date_from_text(str(datetime_value))
            if parsed:
                return parsed

    for attrs in (
        {"property": "article:published_time"},
        {"name": "date"},
        {"name": "publishdate"},
    ):
        tag = soup.find("meta", attrs=attrs)
        if tag and tag.get("content"):
            parsed = _date_from_text(str(tag["content"]))
            if parsed:
                return parsed

    return _date_from_text(soup.get_text(" ", strip=True))


def _extract_thumbnail_url(soup: BeautifulSoup) -> str | None:
    for attrs in (
        {"property": "og:image"},
        {"name": "twitter:image"},
        {"itemprop": "image"},
    ):
        tag = soup.find("meta", attrs=attrs)
        if tag and tag.get("content"):
            url = str(tag["content"]).strip()
            if url.startswith("http"):
                return url
    return None


def _extract_article_body(soup: BeautifulSoup):
    for selector in ("article", "main", "[data-testid='article-content']"):
        body = soup.select_one(selector)
        if body:
            return body

    h1 = soup.find("h1")
    if h1 and h1.parent:
        return h1.parent

    body = soup.find("body")
    if body:
        return body

    raise ValueError("Could not extract LoL patch article body from page")


def _to_markdown(body) -> str:
    for unwanted in body.select("script, style, nav, footer, header, picture, source"):
        unwanted.decompose()

    if html_to_markdown is not None:
        markdown = html_to_markdown(
            str(body),
            heading_style="ATX",
            bullets="-",
            strip=["img"],
        )
    else:
        markdown = body.get_text("\n", strip=True)

    lines = [line.rstrip() for line in markdown.splitlines()]
    compact: list[str] = []
    previous_blank = False
    for line in lines:
        blank = not line.strip()
        if blank and previous_blank:
            continue
        compact.append(line)
        previous_blank = blank
    return "\n".join(compact).strip() + "\n"


def _date_from_text(text: str) -> str | None:
    match = re.search(r"(20\d{2})-(\d{2})-(\d{2})", text)
    if match:
        return "-".join(match.groups())
    return None


def _clean_text(text: str) -> str:
    return " ".join(text.split())
