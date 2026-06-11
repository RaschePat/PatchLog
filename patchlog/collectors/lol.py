from __future__ import annotations

import time
from pathlib import Path
from urllib.parse import urljoin
from urllib.robotparser import RobotFileParser

import httpx
from bs4 import BeautifulSoup

from patchlog.collectors.base import BaseCollector, CollectedPatch, PatchArticle
from patchlog.config import settings


LOL_PATCH_NOTES_URL = "https://www.leagueoflegends.com/ko-kr/news/tags/patch-notes/"
LOL_BASE_URL = "https://www.leagueoflegends.com"
USER_AGENT = "PATCHLOG-RAG/0.1 (+local learning project)"


class LoLCollector(BaseCollector):
    game = "lol"

    def __init__(
        self,
        *,
        client: httpx.Client | None = None,
        crawl_delay_sec: float | None = None,
    ) -> None:
        self.client = client or httpx.Client(
            headers={"User-Agent": USER_AGENT},
            follow_redirects=True,
            timeout=30,
        )
        self.crawl_delay_sec = (
            settings.crawl_delay_sec if crawl_delay_sec is None else crawl_delay_sec
        )

    def list_patches(
        self,
        *,
        limit: int,
        since: str | None = None,
    ) -> list[PatchArticle]:
        self._ensure_allowed(LOL_PATCH_NOTES_URL)
        response = self.client.get(LOL_PATCH_NOTES_URL)
        response.raise_for_status()
        articles = parse_patch_list_html(response.text, base_url=LOL_BASE_URL)
        if since:
            articles = [
                article
                for article in articles
                if article.patch_date is None or article.patch_date >= since
            ]
        return articles[:limit]

    def fetch_patch(self, article: PatchArticle) -> CollectedPatch:
        self._ensure_allowed(article.url)
        response = self.client.get(article.url)
        response.raise_for_status()
        return CollectedPatch(article=article, html=response.text)

    def collect(
        self,
        *,
        output_root: Path,
        limit: int,
        since: str | None = None,
        force: bool = False,
    ) -> list[Path]:
        from patchlog.parsing.lol import parse_lol_patch_html, write_processed_patch

        written: list[Path] = []
        articles = self.list_patches(limit=limit, since=since)
        raw_dir = output_root / "data" / "raw" / self.game
        processed_dir = output_root / "data" / "processed" / self.game
        raw_dir.mkdir(parents=True, exist_ok=True)
        processed_dir.mkdir(parents=True, exist_ok=True)

        for index, article in enumerate(articles):
            raw_path = raw_dir / f"{article.patch_version}.html"
            meta_path = processed_dir / f"{article.patch_version}.meta.json"
            md_path = processed_dir / f"{article.patch_version}.md"
            if not force and raw_path.exists() and meta_path.exists() and md_path.exists():
                print(f"skip {article.patch_version}: already collected")
                continue

            if index > 0:
                time.sleep(self.crawl_delay_sec)
            collected = self.fetch_patch(article)
            raw_path.write_text(collected.html, encoding="utf-8")
            parsed = parse_lol_patch_html(collected.html, source_url=article.url)
            write_processed_patch(parsed, processed_dir)
            written.extend([raw_path, md_path, meta_path])
            print(f"collected {parsed.metadata['patch_version']}: {article.url}")

        return written

    def _ensure_allowed(self, url: str) -> None:
        robots_url = urljoin(LOL_BASE_URL, "/robots.txt")
        parser = RobotFileParser()
        parser.set_url(robots_url)
        try:
            parser.read()
        except Exception as exc:
            raise RuntimeError(f"Failed to read robots.txt: {robots_url}") from exc
        if not parser.can_fetch(USER_AGENT, url):
            raise RuntimeError(f"robots.txt disallows fetching {url}")


def parse_patch_list_html(html: str, *, base_url: str = LOL_BASE_URL) -> list[PatchArticle]:
    soup = BeautifulSoup(html, "html.parser")
    articles: list[PatchArticle] = []
    seen_urls: set[str] = set()

    for anchor in soup.find_all("a", href=True):
        href = str(anchor["href"])
        url = urljoin(base_url, href)
        if not _looks_like_patch_note_url(url):
            continue

        title = _clean_text(anchor.get_text(" ", strip=True))
        if "패치" not in title and "patch" not in title.lower():
            title = _title_from_url(url)

        patch_version = extract_patch_version(title) or extract_patch_version(url)
        if patch_version is None or url in seen_urls:
            continue

        patch_date = _extract_nearby_iso_date(anchor)
        articles.append(
            PatchArticle(
                game="lol",
                title=title,
                url=url,
                patch_version=patch_version,
                patch_date=patch_date,
            )
        )
        seen_urls.add(url)

    return articles


def extract_patch_version(text: str) -> str | None:
    import re

    match = re.search(r"(?<!\d)(\d{2}\.\d{1,2})(?!\d)", text)
    if match:
        return match.group(1)
    return None


def _looks_like_patch_note_url(url: str) -> bool:
    normalized = url.lower()
    return (
        "leagueoflegends.com/ko-kr/news/game-updates/" in normalized
        and "patch" in normalized
        and "notes" in normalized
    )


def _extract_nearby_iso_date(anchor) -> str | None:
    import re

    node = anchor
    for _ in range(4):
        text = node.get_text(" ", strip=True) if node is not None else ""
        match = re.search(r"(20\d{2}-\d{2}-\d{2})T", text)
        if match:
            return match.group(1)
        node = node.parent
    return None


def _title_from_url(url: str) -> str:
    slug = url.rstrip("/").split("/")[-1]
    return slug.replace("-", " ")


def _clean_text(text: str) -> str:
    return " ".join(text.split())

