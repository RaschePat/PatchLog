from __future__ import annotations

import json

from patchlog.collectors.base import PatchArticle
from patchlog.collectors.lol import LoLCollector, extract_patch_version, parse_patch_list_html
from patchlog.parsing.assets import extract_lol_entity_assets
from patchlog.parsing.lol import parse_lol_patch_html, write_processed_patch


LIST_HTML = """
<html>
  <body>
    <a href="/ko-kr/news/game-updates/league-of-legends-patch-26-12-notes/">
      게임 업데이트 2026-06-09T18:00:00.000Z 리그 오브 레전드 26.12 패치 노트
    </a>
    <a href="/ko-kr/news/game-updates/patch-26-5-notes/">
      게임 업데이트 2026-03-03T19:00:00.000Z 26.5 패치 노트
    </a>
    <a href="/ko-kr/news/community/not-a-patch-note/">다른 글</a>
  </body>
</html>
"""


DETAIL_HTML = """
<html>
  <head>
    <meta property="article:published_time" content="2026-06-09T18:00:00.000Z" />
  </head>
  <body>
    <article>
      <h1>리그 오브 레전드 26.12 패치 노트</h1>
      <p>시즌 2 액트 2가 화끈하게 시작합니다.</p>
      <h2>챔피언</h2>
      <h3>아트록스</h3>
      <p>Q - 다르킨의 검</p>
      <ul><li>검 끝 추가 피해량: 70 ⇒ 75</li></ul>
    </article>
  </body>
</html>
"""

ASSET_HTML = """
<html>
  <body>
    <div class="patch-change-block">
      <p><a class="reference-link"><img src="https://ddragon.leagueoflegends.com/cdn/16.11.1/img/champion/Gwen.png"></a></p>
      <h3 class="change-title"><a href="/ko-kr/champions/gwen/">그웬</a></h3>
      <h4 class="change-detail-title ability-title"><img src="https://ddragon.leagueoflegends.com/cdn/16.11.1/img/spell/GwenQ.png">Q - 싹둑싹둑!</h4>
      <ul><li>가위질 1회당 기본 피해량: 10 ⇒ 14</li></ul>
    </div>
  </body>
</html>
"""


def test_parse_patch_list_html_extracts_recent_patch_links() -> None:
    articles = parse_patch_list_html(LIST_HTML)

    assert [article.patch_version for article in articles] == ["26.12", "26.5"]
    assert articles[0].url == (
        "https://www.leagueoflegends.com/ko-kr/news/game-updates/"
        "league-of-legends-patch-26-12-notes/"
    )
    assert articles[0].patch_date == "2026-06-09"


def test_extract_patch_version_handles_korean_titles() -> None:
    assert extract_patch_version("리그 오브 레전드 26.12 패치 노트") == "26.12"
    assert extract_patch_version("26.5 패치 노트") == "26.5"


def test_parse_lol_patch_html_outputs_metadata_and_markdown() -> None:
    parsed = parse_lol_patch_html(
        DETAIL_HTML,
        source_url="https://www.leagueoflegends.com/ko-kr/news/game-updates/league-of-legends-patch-26-12-notes/",
    )

    assert parsed.metadata == {
        "game": "lol",
        "patch_version": "26.12",
        "patch_date": "2026-06-09",
        "source_url": "https://www.leagueoflegends.com/ko-kr/news/game-updates/league-of-legends-patch-26-12-notes/",
        "title": "리그 오브 레전드 26.12 패치 노트",
        "lang": "ko",
    }
    assert "## 챔피언" in parsed.markdown
    assert "검 끝 추가 피해량" in parsed.markdown


def test_write_processed_patch_preserves_utf8_json(tmp_path) -> None:
    parsed = parse_lol_patch_html(DETAIL_HTML, source_url="https://example.com/26-12")
    write_processed_patch(parsed, tmp_path)

    meta = json.loads((tmp_path / "26.12.meta.json").read_text(encoding="utf-8"))
    markdown = (tmp_path / "26.12.md").read_text(encoding="utf-8")
    assert meta["title"] == "리그 오브 레전드 26.12 패치 노트"
    assert "아트록스" in markdown


def test_extract_lol_entity_assets_reads_champion_and_ability_icons() -> None:
    assets = extract_lol_entity_assets(ASSET_HTML)

    assert assets["그웬"].image_url == (
        "https://ddragon.leagueoflegends.com/cdn/16.11.1/img/champion/Gwen.png"
    )
    assert assets["그웬"].ability_icons == {
        "Q - 싹둑싹둑!": "https://ddragon.leagueoflegends.com/cdn/16.11.1/img/spell/GwenQ.png"
    }


class FakeLoLCollector(LoLCollector):
    def __init__(self) -> None:
        super().__init__(crawl_delay_sec=0)
        self.fetch_count = 0

    def list_patches(self, *, limit: int, since: str | None = None):
        return [
            PatchArticle(
                game="lol",
                title="리그 오브 레전드 26.12 패치 노트",
                url="https://example.com/26-12",
                patch_version="26.12",
                patch_date="2026-06-09",
            )
        ][:limit]

    def fetch_patch(self, article: PatchArticle):
        from patchlog.collectors.base import CollectedPatch

        self.fetch_count += 1
        return CollectedPatch(article=article, html=DETAIL_HTML)


def test_collect_skips_existing_patch_without_force(tmp_path) -> None:
    collector = FakeLoLCollector()
    first_written = collector.collect(output_root=tmp_path, limit=1)
    second_written = collector.collect(output_root=tmp_path, limit=1)

    assert len(first_written) == 3
    assert second_written == []
    assert collector.fetch_count == 1
