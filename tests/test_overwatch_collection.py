from __future__ import annotations

import json

from patchlog.chunking.overwatch import chunk_overwatch_markdown
from patchlog.collectors.overwatch import parse_patch_list_html
from patchlog.parsing.overwatch import parse_overwatch_patch_html, write_processed_patch


PATCH_HTML = """
<div class="PatchNotes-patch PatchNotes-live">
  <div class="anchor" id="patch-2026-05-21"></div>
  <div class="PatchNotes-labels"><div class="PatchNotes-date">2026년 5월 21일</div></div>
  <h3 class="PatchNotes-patchTitle">오버워치 패치 노트 - 2026년 5월 22일</h3>
  <div class="PatchNotes-section PatchNotes-section-hero_update">
    <h4 class="PatchNotes-sectionTitle">스타디움 업데이트</h4>
    <div class="PatchNotesHeroUpdate">
      <div class="PatchNotesHeroUpdate-header">
        <img class="PatchNotesHeroUpdate-icon" src="https://example.com/jetpack-cat.png" alt="제트팩 캣" />
        <h5 class="PatchNotesHeroUpdate-name">제트팩 캣</h5>
      </div>
      <div class="PatchNotesHeroUpdate-body">
        <div class="PatchNotesHeroUpdate-generalUpdates">
          <p>통통 튀는 꾹꾹이</p>
          <ul><li>튕기기 치유량이 25%에서 35%로 증가했습니다.</li></ul>
        </div>
      </div>
    </div>
  </div>
  <div class="PatchNotes-section PatchNotes-section-generic_update">
    <h4 class="PatchNotes-sectionTitle">버그 수정</h4>
    <div class="PatchNotesGeneralUpdate">
      <div class="PatchNotesGeneralUpdate-title">일반</div>
      <div class="PatchNotesGeneralUpdate-description">
        <ul><li>상점에서 화폐 옵션을 선택할 수 없던 문제를 수정했습니다.</li></ul>
      </div>
    </div>
  </div>
</div>
"""

PAGE_HTML = f"""
<html>
  <body>
    <div class="PatchNotes-list">{PATCH_HTML}</div>
    <a class="PatchNotesPaginationLink--prev" href="/ko-kr/news/patch-notes/live/2026/04">4월 패치 노트</a>
  </body>
</html>
"""

PATCH_METADATA = {
    "game": "overwatch",
    "patch_version": "2026-05-22",
    "patch_date": "2026-05-22",
    "source_url": "https://overwatch.blizzard.com/ko-kr/news/patch-notes/#patch-2026-05-21",
    "title": "오버워치 패치 노트 - 2026년 5월 22일",
    "lang": "ko",
}


def test_parse_overwatch_patch_list_html_extracts_patch_sections() -> None:
    articles, html_by_url, previous_url = parse_patch_list_html(
        PAGE_HTML,
        page_url="https://overwatch.blizzard.com/ko-kr/news/patch-notes/",
    )

    assert [article.patch_version for article in articles] == ["2026-05-22"]
    assert articles[0].patch_date == "2026-05-22"
    assert articles[0].url.endswith("#patch-2026-05-21")
    assert articles[0].url in html_by_url
    assert previous_url == "https://overwatch.blizzard.com/ko-kr/news/patch-notes/live/2026/04"


def test_parse_overwatch_patch_html_outputs_markdown_and_metadata() -> None:
    parsed = parse_overwatch_patch_html(PATCH_HTML, source_url=PATCH_METADATA["source_url"])

    assert parsed.metadata == PATCH_METADATA
    assert "### [제트팩 캣](https://example.com/jetpack-cat.png)" in parsed.markdown
    assert "## 버그 수정" in parsed.markdown


def test_write_overwatch_processed_patch_preserves_utf8_json(tmp_path) -> None:
    parsed = parse_overwatch_patch_html(PATCH_HTML, source_url=PATCH_METADATA["source_url"])
    write_processed_patch(parsed, tmp_path)

    meta = json.loads((tmp_path / "2026-05-22.meta.json").read_text(encoding="utf-8"))
    markdown = (tmp_path / "2026-05-22.md").read_text(encoding="utf-8")
    assert meta["game"] == "overwatch"
    assert "제트팩 캣" in markdown


def test_chunk_overwatch_markdown_splits_heroes_and_system_cards() -> None:
    parsed = parse_overwatch_patch_html(PATCH_HTML, source_url=PATCH_METADATA["source_url"])
    chunks = chunk_overwatch_markdown(parsed.markdown, parsed.metadata)

    assert [chunk.metadata["target"] for chunk in chunks] == ["제트팩 캣", "일반"]
    assert [chunk.metadata["section"] for chunk in chunks] == ["hero", "system"]
    assert chunks[0].metadata["image_url"] == "https://example.com/jetpack-cat.png"
    assert chunks[0].metadata["image_url_kind"] == "direct"


def test_overwatch_section_description_without_children_becomes_system_card() -> None:
    html = """
<div class="PatchNotes-patch">
  <div class="PatchNotes-date">2026년 3월 12일</div>
  <h3 class="PatchNotes-patchTitle">오버워치 패치 노트 - 2026년 3월 12일</h3>
  <div class="PatchNotes-section PatchNotes-section-generic_update">
    <h4 class="PatchNotes-sectionTitle">버그 수정 업데이트</h4>
    <div class="PatchNotes-sectionDescription">
      <p>버그 수정 패치입니다.</p>
    </div>
  </div>
</div>
"""
    parsed = parse_overwatch_patch_html(html, source_url="https://example.com/ow#patch")
    chunks = chunk_overwatch_markdown(parsed.markdown, parsed.metadata)

    assert "### 버그 수정 업데이트" in parsed.markdown
    assert [chunk.metadata["target"] for chunk in chunks] == ["버그 수정 업데이트"]
    assert chunks[0].metadata["section"] == "system"
