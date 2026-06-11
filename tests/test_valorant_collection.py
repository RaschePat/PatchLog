from __future__ import annotations

import json

from patchlog.assets.valorant import valorant_agent_icon, valorant_agent_names
from patchlog.chunking.valorant import chunk_valorant_markdown
from patchlog.collectors.valorant import extract_patch_version, parse_patch_list_html
from patchlog.parsing.valorant import parse_valorant_patch_html, write_processed_patch


LIST_HTML = """
<html>
  <body>
    <a href="/ko-kr/news/game-updates/valorant-patch-notes-12-11/">
      게임 업데이트 2026-06-09T13:00:00.000Z 발로란트 12.11 패치 노트
    </a>
    <a href="/ko-kr/news/game-updates/valorant-patch-notes-12-10/">
      게임 업데이트 2026-05-27T13:00:00.000Z 발로란트 12.10 패치 노트
    </a>
    <a href="/ko-kr/news/community/not-a-patch-note/">다른 글</a>
  </body>
</html>
"""


DETAIL_HTML = """
<html>
  <head>
    <meta property="article:published_time" content="2026-06-09T13:00:00.000Z" />
  </head>
  <body>
    <article>
      <h1>발로란트 12.11 패치 노트</h1>
      <p>액트 3을 마무리하는 가벼운 패치입니다.</p>
      <h2>요원 업데이트</h2>
      <h3>네온</h3>
      <ul><li>슬라이드 정확도가 감소했습니다.</li></ul>
      <h2>무기 업데이트</h2>
      <h3>산탄총</h3>
      <ul><li>피해량이 하향되었습니다.</li></ul>
      <h2>맵 업데이트</h2>
      <h3>로터스</h3>
      <ul><li>C 지점 구조가 조정되었습니다.</li></ul>
    </article>
  </body>
</html>
"""

PATCH_METADATA = {
    "game": "valorant",
    "patch_version": "12.11",
    "patch_date": "2026-06-09",
    "source_url": "https://playvalorant.com/ko-kr/news/game-updates/valorant-patch-notes-12-11/",
    "title": "발로란트 12.11 패치 노트",
    "lang": "ko",
}


def test_parse_valorant_patch_list_html_extracts_recent_patch_links() -> None:
    articles = parse_patch_list_html(LIST_HTML)

    assert [article.patch_version for article in articles] == ["12.11", "12.10"]
    assert articles[0].game == "valorant"
    assert articles[0].patch_date == "2026-06-09"
    assert articles[0].url == (
        "https://playvalorant.com/ko-kr/news/game-updates/"
        "valorant-patch-notes-12-11/"
    )


def test_extract_valorant_patch_version_normalizes_minor_version() -> None:
    assert extract_patch_version("발로란트 12.11 패치 노트") == "12.11"
    assert extract_patch_version("VALORANT patch notes 12.3") == "12.03"


def test_parse_valorant_patch_html_outputs_metadata_and_markdown() -> None:
    parsed = parse_valorant_patch_html(
        DETAIL_HTML,
        source_url="https://playvalorant.com/ko-kr/news/game-updates/valorant-patch-notes-12-11/",
    )

    assert parsed.metadata == PATCH_METADATA
    assert "## 요원 업데이트" in parsed.markdown
    assert "네온" in parsed.markdown


def test_write_valorant_processed_patch_preserves_utf8_json(tmp_path) -> None:
    parsed = parse_valorant_patch_html(DETAIL_HTML, source_url=PATCH_METADATA["source_url"])
    write_processed_patch(parsed, tmp_path)

    meta = json.loads((tmp_path / "12.11.meta.json").read_text(encoding="utf-8"))
    markdown = (tmp_path / "12.11.md").read_text(encoding="utf-8")
    assert meta["game"] == "valorant"
    assert meta["title"] == "발로란트 12.11 패치 노트"
    assert "산탄총" in markdown


def test_chunk_valorant_markdown_splits_sections_and_metadata() -> None:
    parsed = parse_valorant_patch_html(DETAIL_HTML, source_url=PATCH_METADATA["source_url"])
    chunks = chunk_valorant_markdown(parsed.markdown, parsed.metadata)

    assert [chunk.metadata["target"] for chunk in chunks] == ["네온", "산탄총", "로터스"]
    assert [chunk.metadata["section"] for chunk in chunks] == ["agent", "weapon", "map"]
    assert chunks[0].chunk_id == "valorant-12.11-네온-0"
    assert chunks[1].metadata["change_type"] == "nerf"


def test_chunk_valorant_markdown_expands_generic_update_bullets() -> None:
    markdown = """
# 발로란트 12.11 패치 노트

## 콘솔 한정

### 무기 업데이트

- 저지
  - 최소 탄퍼짐 증가 2.25 >>> 2.5

### 버그 수정

- 요원
  - 사이퍼의 카메라 모델이 보이지 않던 버그를 수정했습니다.
- 맵
  - 브리즈에서 일부 스킬이 잘못 조준되던 버그를 수정했습니다.
"""

    chunks = chunk_valorant_markdown(markdown, PATCH_METADATA)

    assert [chunk.metadata["target"] for chunk in chunks] == ["저지", "사이퍼", "맵 버그 수정"]
    assert [chunk.metadata["section"] for chunk in chunks] == ["weapon", "agent", "map"]
    assert json.loads(chunks[1].metadata["agent_names"]) == ["사이퍼"]


def test_chunk_valorant_heading_sections_do_not_leak_between_siblings() -> None:
    markdown = """
# 발로란트 12.11 패치 노트

## 콘솔 한정

### 무기 업데이트

- 저지
  - 최소 탄퍼짐 증가 2.25 >>> 2.5

### 버그 수정

- 상점
  - 구매 버튼 안내 문구가 겹치던 버그를 수정했습니다.
"""

    chunks = chunk_valorant_markdown(markdown, PATCH_METADATA)

    assert [chunk.metadata["target"] for chunk in chunks] == ["저지", "상점 버그 수정"]
    assert [chunk.metadata["section"] for chunk in chunks] == ["weapon", "system"]


def test_chunk_valorant_markdown_splits_section_bullet_entities() -> None:
    markdown = """
# 발로란트 12.02 패치 노트

## 요원 업데이트

- **하버**
  - 해만
    - 재사용 대기시간 감소 40초 >>> 30초
- **레이나**
  - 여제
    - 궁극기 포인트 증가 6 >>> 7
"""

    chunks = chunk_valorant_markdown(markdown, PATCH_METADATA)

    assert [chunk.metadata["target"] for chunk in chunks] == ["하버", "레이나"]
    assert [chunk.metadata["section"] for chunk in chunks] == ["agent", "agent"]


def test_chunk_valorant_markdown_splits_colon_labeled_weapon_blocks() -> None:
    markdown = """
# 발로란트 12.09 패치 노트

## 무기 업데이트

모든 산탄총:

- 모든 산탄총의 이동 중 사격 정확도가 감소했습니다.

버키:

- 버키 탄환 피해량이 0~8m 거리에서 감소했습니다.

저지:

- 최소 탄퍼짐 증가 2.25 >>> 2.5

쇼티:

- 연사 속도 감소 3.33 >>> 3.0
"""

    chunks = chunk_valorant_markdown(markdown, PATCH_METADATA)

    assert [chunk.metadata["target"] for chunk in chunks] == ["모든 산탄총", "버키", "저지", "쇼티"]
    assert [chunk.metadata["section"] for chunk in chunks] == ["weapon", "weapon", "weapon", "weapon"]


def test_chunk_valorant_markdown_skips_related_articles_section() -> None:
    markdown = """
# 발로란트 12.11 패치 노트

## 일반 업데이트

- 내 발로란트 카드가 지금 공개되었습니다!

## 관련 글

- [다른 글](https://playvalorant.com/ko-kr/news/example/)
"""

    chunks = chunk_valorant_markdown(markdown, PATCH_METADATA)

    assert [chunk.metadata["target"] for chunk in chunks] == ["일반 업데이트"]


def test_valorant_agent_catalog_contains_profile_icons() -> None:
    names = set(valorant_agent_names())

    assert len(names) == 29
    assert {"믹스", "스카이", "네온", "페이드"}.issubset(names)
    assert valorant_agent_icon("믹스").endswith("/displayicon.png")


def test_chunk_valorant_agent_bugfix_lines_are_classified_by_mentioned_agents() -> None:
    markdown = """
# 발로란트 12.11 패치 노트

## 전체 플랫폼

### 버그 수정

- 요원
  - 프랙처에서 집라인에 스파이크가 떨어졌을 때 스파이크 획득 대사가 반복되던 버그를 수정했습니다.
  - 왼손잡이 모드에서 스카이, 네온, 페이드의 HUD 시각 효과가 화면 중앙으로 밀려나던 버그를 수정했습니다.
  - M-파동으로 피해를 입지 않은 아군을 치유하면 믹스가 어시스트를 달성하던 버그를 수정했습니다.
"""

    chunks = chunk_valorant_markdown(markdown, PATCH_METADATA)
    by_target = {chunk.metadata["target"]: chunk for chunk in chunks}

    assert list(by_target) == ["요원 버그 수정", "스카이, 네온, 페이드", "믹스"]
    assert by_target["요원 버그 수정"].metadata.get("agent_image_urls") is None
    assert json.loads(by_target["믹스"].metadata["agent_names"]) == ["믹스"]
    assert by_target["믹스"].metadata["image_url"].endswith("/displayicon.png")
    assert json.loads(by_target["스카이, 네온, 페이드"].metadata["agent_names"]) == ["스카이", "네온", "페이드"]
    assert len(json.loads(by_target["스카이, 네온, 페이드"].metadata["agent_image_urls"])) == 3
