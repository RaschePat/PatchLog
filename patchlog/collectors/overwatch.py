from __future__ import annotations

import time
from pathlib import Path
from urllib.parse import urljoin
from urllib.robotparser import RobotFileParser

import httpx
from bs4 import BeautifulSoup

from patchlog.collectors.base import BaseCollector, CollectedPatch, PatchArticle
from patchlog.config import settings
from patchlog.parsing.overwatch import parse_overwatch_patch_html, write_processed_patch


OVERWATCH_PATCH_NOTES_URL = "https://overwatch.blizzard.com/ko-kr/news/patch-notes/"
OVERWATCH_BASE_URL = "https://overwatch.blizzard.com"
USER_AGENT = "PATCHLOG-RAG/0.1 (+local learning project)"


class OverwatchCollector(BaseCollector):
    game = "overwatch"

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
        self._patch_html_by_url: dict[str, str] = {}

    def list_patches(
        self,
        *,
        limit: int,
        since: str | None = None,
    ) -> list[PatchArticle]:
        articles: list[PatchArticle] = []
        seen_urls: set[str] = set()
        next_url: str | None = OVERWATCH_PATCH_NOTES_URL

        while next_url and len(articles) < limit:
            self._ensure_allowed(next_url)
            response = self.client.get(next_url)
            response.raise_for_status()
            page_articles, patch_html_by_url, previous_url = parse_patch_list_html(
                response.text,
                page_url=next_url,
            )
            self._patch_html_by_url.update(patch_html_by_url)
            for article in page_articles:
                if article.url in seen_urls:
                    continue
                if since and article.patch_date and article.patch_date < since:
                    continue
                articles.append(article)
                seen_urls.add(article.url)
                if len(articles) >= limit:
                    break
            next_url = previous_url
            if next_url and len(articles) < limit:
                time.sleep(self.crawl_delay_sec)

        return articles[:limit]

    def fetch_patch(self, article: PatchArticle) -> CollectedPatch:
        html = self._patch_html_by_url.get(article.url)
        if html:
            return CollectedPatch(article=article, html=html)

        page_url = article.url.split("#", maxsplit=1)[0]
        self._ensure_allowed(page_url)
        response = self.client.get(page_url)
        response.raise_for_status()
        _, patch_html_by_url, _ = parse_patch_list_html(response.text, page_url=page_url)
        self._patch_html_by_url.update(patch_html_by_url)
        html = self._patch_html_by_url.get(article.url)
        if not html:
            raise ValueError(f"Could not find Overwatch patch section for {article.url}")
        return CollectedPatch(article=article, html=html)

    def collect(
        self,
        *,
        output_root: Path,
        limit: int,
        since: str | None = None,
        force: bool = False,
    ) -> list[Path]:
        written: list[Path] = []
        articles = self.list_patches(limit=limit, since=since)
        raw_dir = output_root / "data" / "raw" / self.game
        processed_dir = output_root / "data" / "processed" / self.game
        raw_dir.mkdir(parents=True, exist_ok=True)
        processed_dir.mkdir(parents=True, exist_ok=True)

        for article in articles:
            raw_path = raw_dir / f"{article.patch_version}.html"
            meta_path = processed_dir / f"{article.patch_version}.meta.json"
            md_path = processed_dir / f"{article.patch_version}.md"
            if not force and raw_path.exists() and meta_path.exists() and md_path.exists():
                print(f"skip {article.patch_version}: already collected")
                continue

            collected = self.fetch_patch(article)
            raw_path.write_text(collected.html, encoding="utf-8")
            parsed = parse_overwatch_patch_html(collected.html, source_url=article.url)
            write_processed_patch(parsed, processed_dir)
            written.extend([raw_path, md_path, meta_path])
            print(f"collected {parsed.metadata['patch_version']}: {article.url}")

        return written

    def _ensure_allowed(self, url: str) -> None:
        robots_url = urljoin(OVERWATCH_BASE_URL, "/robots.txt")
        parser = RobotFileParser()
        parser.set_url(robots_url)
        try:
            parser.read()
        except Exception as exc:
            raise RuntimeError(f"Failed to read robots.txt: {robots_url}") from exc
        if not parser.can_fetch(USER_AGENT, url):
            raise RuntimeError(f"robots.txt disallows fetching {url}")


def parse_patch_list_html(
    html: str,
    *,
    page_url: str = OVERWATCH_PATCH_NOTES_URL,
) -> tuple[list[PatchArticle], dict[str, str], str | None]:
    soup = BeautifulSoup(html, "html.parser")
    articles: list[PatchArticle] = []
    patch_html_by_url: dict[str, str] = {}

    for patch in soup.select(".PatchNotes-patch"):
        anchor = patch.select_one(".anchor[id]")
        anchor_id = str(anchor["id"]) if anchor and anchor.get("id") else None
        title = _clean_text(_text(patch.select_one(".PatchNotes-patchTitle")))
        patch_date = _extract_patch_date(patch)
        if not title or not patch_date:
            continue
        page_base_url = _localized_url(page_url.split("#", maxsplit=1)[0])
        url = f"{page_base_url}#{anchor_id}" if anchor_id else page_base_url
        article = PatchArticle(
            game="overwatch",
            title=title,
            url=url,
            patch_version=patch_date,
            patch_date=patch_date,
        )
        articles.append(article)
        patch_html_by_url[url] = str(patch)

    previous_url = _previous_month_url(soup, page_url)
    return articles, patch_html_by_url, previous_url


def _previous_month_url(soup: BeautifulSoup, page_url: str) -> str | None:
    link = soup.select_one(".PatchNotesPaginationLink--prev[href]")
    if not link:
        return None
    return _localized_url(urljoin(page_url, str(link["href"])))


def _extract_patch_date(patch_node) -> str | None:
    from patchlog.parsing.overwatch import _date_from_korean_text

    title = _text(patch_node.select_one(".PatchNotes-patchTitle"))
    date = _date_from_korean_text(title)
    if date:
        return date
    label = _text(patch_node.select_one(".PatchNotes-date"))
    return _date_from_korean_text(label)


def _text(node) -> str:
    return node.get_text(" ", strip=True) if node is not None else ""


def _clean_text(text: str) -> str:
    return " ".join(text.split())


def _localized_url(url: str) -> str:
    return url.replace("https://overwatch.blizzard.com/news/", "https://overwatch.blizzard.com/ko-kr/news/")
