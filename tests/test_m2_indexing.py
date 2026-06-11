from __future__ import annotations

from types import SimpleNamespace

import pytest

from patchlog.chunking.lol import chunk_lol_markdown
from patchlog.embedding.hash import HashEmbeddingFunction


PATCH_METADATA = {
    "game": "lol",
    "patch_version": "26.12",
    "patch_date": "2026-06-09",
    "source_url": "https://example.com/26-12",
    "title": "리그 오브 레전드 26.12 패치 노트",
    "lang": "ko",
}


MARKDOWN = """
# 리그 오브 레전드 26.12 패치 노트

### [기사의 맹세](https://www.leagueoflegends.com/ko-kr/how-to-play/)

> 기사의 맹세는 고유 효과를 강화합니다.

- **대신 입는 피해량**: 12% ⇒ **14%**

### [아트록스](https://www.leagueoflegends.com/ko-kr/champions/aatrox/)

> 아트록스는 상향이 필요합니다.

#### Q - 다르킨의 검

- **검 끝 추가 피해량**: 70 ⇒ **75**

### [리 신](https://www.leagueoflegends.com/ko-kr/champions/leesin/)

> 리 신은 너무 강력한 모습을 보입니다. 피해량을 하향합니다.

#### Q1 - 음파

- **피해량**: 65 ⇒ **60**

## 아이템

### 다른 섹션
"""


def test_chunk_lol_markdown_splits_champion_blocks_and_metadata() -> None:
    chunks = chunk_lol_markdown(MARKDOWN, PATCH_METADATA)

    assert [chunk.metadata["target"] for chunk in chunks] == ["기사의 맹세", "아트록스", "리 신"]
    assert chunks[0].chunk_id == "lol-26.12-기사의-맹세-0"
    assert chunks[0].metadata["section"] == "item"
    assert chunks[1].metadata["change_type"] == "buff"
    assert chunks[2].metadata["change_type"] == "nerf"
    assert chunks[1].metadata["game"] == "lol"
    assert chunks[1].metadata["section"] == "champion"
    assert "[lol] 패치 26.12 - 아트록스" in chunks[1].document


def test_non_champion_direct_image_urls_are_marked_as_trusted() -> None:
    markdown = """
# 리그 오브 레전드 26.12 패치 노트

### [테스트 아이템](https://ddragon.leagueoflegends.com/cdn/16.11.1/img/item/1234.png)

- **공격력**: 10 ⇒ **12**
"""
    chunks = chunk_lol_markdown(markdown, PATCH_METADATA)

    assert chunks[0].metadata["section"] == "item"
    assert chunks[0].metadata["image_url"] == "https://ddragon.leagueoflegends.com/cdn/16.11.1/img/item/1234.png"
    assert chunks[0].metadata["image_url_kind"] == "direct"


def test_hash_embedding_is_deterministic_and_normalized() -> None:
    embedder = HashEmbeddingFunction(dimensions=32)

    first = embedder.embed("아트록스 상향")
    second = embedder.embed("아트록스 상향")

    assert first == second
    assert len(first) == 32
    assert sum(value * value for value in first) == pytest.approx(1.0)


def test_chroma_store_indexes_and_filters_chunks(tmp_path) -> None:
    pytest.importorskip("chromadb")
    from patchlog.store.chroma import ChromaPatchStore

    chunks = chunk_lol_markdown(MARKDOWN, PATCH_METADATA)
    store = ChromaPatchStore(persist_path=tmp_path / "chroma")
    store.upsert_chunks(chunks)

    rows = store.search(
        query="리 신 피해량 하향",
        where={"game": "lol", "target": "리 신"},
        top_k=3,
    )

    assert rows
    assert rows[0]["metadata"]["target"] == "리 신"
    assert rows[0]["metadata"]["game"] == "lol"


def test_chroma_backed_chat_returns_citations_and_navigation(tmp_path) -> None:
    pytest.importorskip("chromadb")
    from patchlog.retrieval.orchestrator import ChatOrchestrator
    from patchlog.store.chroma import ChromaPatchStore

    chunks = chunk_lol_markdown(MARKDOWN, PATCH_METADATA)
    store = ChromaPatchStore(persist_path=tmp_path / "chroma")
    store.upsert_chunks(chunks)

    result = ChatOrchestrator(store=store).chat(
        game="lol",
        message="리 신 피해량 하향 알려줘",
        top_k=3,
        debug=True,
    )

    assert result.sources
    assert result.sources[0]["game"] == "lol"
    assert result.sources[0]["target"] == "리 신"
    assert result.navigation_target is not None
    assert result.navigation_target["chunk_id"] == result.sources[0]["chunk_id"]
    assert "[패치 26.12, 2026-06-09]" in result.answer
    assert result.answer.startswith("리 신은 26.12 패치에서 하향 내용이 확인됩니다.")
    assert "핵심 변경:" in result.answer
    assert "- 리 신:" not in result.answer
    assert result.debug_trace is not None
    assert result.debug_trace["final_filter"] == {
        "game": "lol",
        "target": "리 신",
        "change_type": "nerf",
    }


def test_chat_matches_known_targets_without_spaces(tmp_path) -> None:
    pytest.importorskip("chromadb")
    from patchlog.retrieval.orchestrator import ChatOrchestrator
    from patchlog.store.chroma import ChromaPatchStore

    chunks = chunk_lol_markdown(MARKDOWN, PATCH_METADATA)
    store = ChromaPatchStore(persist_path=tmp_path / "chroma")
    store.upsert_chunks(chunks)

    result = ChatOrchestrator(store=store).chat(
        game="lol",
        message="리신 하향 알려줘",
        top_k=3,
        debug=True,
    )

    assert result.sources
    assert {source["target"] for source in result.sources} == {"리 신"}
    assert "아트록스" not in result.answer
    assert "기사의 맹세" not in result.answer
    assert result.answer.startswith("리 신은 26.12 패치에서 하향 내용이 확인됩니다.")
    assert result.debug_trace is not None
    assert result.debug_trace["final_filter"] == {
        "game": "lol",
        "target": "리 신",
        "change_type": "nerf",
    }


def test_unknown_explicit_target_does_not_fall_back_to_semantic_search(tmp_path) -> None:
    pytest.importorskip("chromadb")
    from patchlog.retrieval.orchestrator import ChatOrchestrator
    from patchlog.store.chroma import ChromaPatchStore

    store = ChromaPatchStore(persist_path=tmp_path / "chroma")
    store.upsert_chunks(
        [
            SimpleNamespace(
                chunk_id="valorant-12.10-gameplay-0",
                document="[valorant] 패치 12.10 - 게임플레이\n\n구매 단계 버그를 수정했습니다.",
                metadata={
                    "game": "valorant",
                    "patch_version": "12.10",
                    "patch_date": "2026-05-27",
                    "section": "system",
                    "target": "게임플레이",
                    "change_type": "bugfix",
                    "source_url": "https://example.com/valorant/12-10",
                    "title": "발로란트 12.10 패치 노트",
                    "lang": "ko",
                },
            ),
            SimpleNamespace(
                chunk_id="valorant-12.11-clove-0",
                document="[valorant] 패치 12.11 - 클로브\n\n아직 안 죽었어 음향 효과 버그를 수정했습니다.",
                metadata={
                    "game": "valorant",
                    "patch_version": "12.11",
                    "patch_date": "2026-06-09",
                    "section": "agent",
                    "target": "클로브",
                    "change_type": "bugfix",
                    "source_url": "https://example.com/valorant/12-11",
                    "title": "발로란트 12.11 패치 노트",
                    "lang": "ko",
                },
            ),
        ]
    )

    result = ChatOrchestrator(store=store).chat(
        game="valorant",
        message="녹턴 패치 알려줘",
        top_k=3,
        debug=True,
    )

    assert result.sources == []
    assert result.navigation_target is None
    assert "해당 대상을 찾지 못했습니다" in result.answer
    assert result.debug_trace is not None
    assert result.debug_trace["final_filter"] == {"game": "valorant"}


def test_new_unknown_target_does_not_reuse_previous_history_target(tmp_path) -> None:
    pytest.importorskip("chromadb")
    from patchlog.models import ChatMessage
    from patchlog.retrieval.orchestrator import ChatOrchestrator
    from patchlog.store.chroma import ChromaPatchStore

    store = ChromaPatchStore(persist_path=tmp_path / "chroma")
    store.upsert_chunks(
        [
            SimpleNamespace(
                chunk_id="lol-26.12-nocturne-0",
                document="[lol] 패치 26.12 - 녹턴\n\nQ 피해량이 하향되었습니다.",
                metadata={
                    "game": "lol",
                    "patch_version": "26.12",
                    "patch_date": "2026-06-09",
                    "section": "champion",
                    "target": "녹턴",
                    "change_type": "nerf",
                    "source_url": "https://example.com/lol/26-12",
                    "title": "리그 오브 레전드 26.12 패치 노트",
                    "lang": "ko",
                },
            )
        ]
    )

    result = ChatOrchestrator(store=store).chat(
        game="lol",
        message="클로브 패치 알려줘",
        chat_history=[
            ChatMessage(role="user", content="녹턴 패치 알려줘"),
            ChatMessage(role="assistant", content="녹턴 답변"),
        ],
        top_k=3,
        debug=True,
    )

    assert result.sources == []
    assert result.navigation_target is None
    assert "녹턴" not in result.answer
    assert result.debug_trace is not None
    assert result.debug_trace["final_filter"] == {"game": "lol"}


def test_target_chat_prefers_latest_patch_over_similarity_order(tmp_path) -> None:
    pytest.importorskip("chromadb")
    from patchlog.retrieval.orchestrator import ChatOrchestrator
    from patchlog.store.chroma import ChromaPatchStore

    store = ChromaPatchStore(persist_path=tmp_path / "chroma")
    store.upsert_chunks(
        [
            SimpleNamespace(
                chunk_id="overwatch-2026-04-15-jetpack-cat-0",
                document="[overwatch] 패치 2026-04-15 - 제트팩 캣\n\n정신 없는 비행\n\n- 가속도가 11% 감소했습니다.",
                metadata={
                    "game": "overwatch",
                    "patch_version": "2026-04-15",
                    "patch_date": "2026-04-15",
                    "section": "hero",
                    "target": "제트팩 캣",
                    "change_type": "nerf",
                    "source_url": "https://example.com/ow/2026-04-15",
                    "title": "오버워치 패치 노트 - 2026년 4월 15일",
                    "lang": "ko",
                },
            ),
            SimpleNamespace(
                chunk_id="overwatch-2026-05-22-jetpack-cat-0",
                document="[overwatch] 패치 2026-05-22 - 제트팩 캣\n\n통통 튀는 꾹꾹이\n\n- 튕기기 치유량이 25%에서 35%로 증가했습니다.",
                metadata={
                    "game": "overwatch",
                    "patch_version": "2026-05-22",
                    "patch_date": "2026-05-22",
                    "section": "hero",
                    "target": "제트팩 캣",
                    "change_type": "buff",
                    "source_url": "https://example.com/ow/2026-05-22",
                    "title": "오버워치 패치 노트 - 2026년 5월 22일",
                    "lang": "ko",
                },
            ),
        ]
    )

    result = ChatOrchestrator(store=store).chat(
        game="overwatch",
        message="제트팩 캣 패치내역 알려줘",
        top_k=2,
        debug=True,
    )

    assert result.sources
    assert result.sources[0]["patch_version"] == "2026-05-22"
    assert result.navigation_target is not None
    assert result.navigation_target["patch_version"] == "2026-05-22"
    assert result.answer.startswith("제트팩 캣은 2026-05-22 패치")


def test_chat_understands_section_and_patch_version_filters(tmp_path) -> None:
    pytest.importorskip("chromadb")
    from patchlog.retrieval.orchestrator import ChatOrchestrator
    from patchlog.store.chroma import ChromaPatchStore

    chunks = chunk_lol_markdown(MARKDOWN, PATCH_METADATA)
    store = ChromaPatchStore(persist_path=tmp_path / "chroma")
    store.upsert_chunks(chunks)
    orchestrator = ChatOrchestrator(store=store)

    item_result = orchestrator.chat(
        game="lol",
        message="아이템 변경 알려줘",
        top_k=3,
        debug=True,
    )
    assert item_result.sources
    assert {source["section"] for source in item_result.sources} == {"item"}
    assert item_result.debug_trace is not None
    assert item_result.debug_trace["final_filter"] == {"game": "lol", "section": "item"}
    assert item_result.answer.startswith("아이템에서 확인된 변경 항목은 다음과 같습니다.")

    patch_result = orchestrator.chat(
        game="lol",
        message="26.12 패치 요약해줘",
        top_k=3,
        debug=True,
    )
    assert patch_result.sources
    assert {source["patch_version"] for source in patch_result.sources} == {"26.12"}
    assert patch_result.debug_trace is not None
    assert patch_result.debug_trace["final_filter"] == {"game": "lol", "patch_version": "26.12"}
    assert patch_result.answer.startswith("26.12 패치에서 확인된 변경 항목은 다음과 같습니다.")


def test_dashboard_patches_are_date_sorted_and_latest_chat_uses_latest_patch(tmp_path) -> None:
    pytest.importorskip("chromadb")
    from fastapi.testclient import TestClient

    import patchlog.api.main as api_main
    from patchlog.retrieval.orchestrator import ChatOrchestrator
    from patchlog.store.chroma import ChromaPatchStore

    older_metadata = {**PATCH_METADATA, "patch_version": "26.11", "patch_date": "2026-05-27"}
    store = ChromaPatchStore(persist_path=tmp_path / "chroma")
    store.upsert_chunks(chunk_lol_markdown(MARKDOWN, older_metadata))
    store.upsert_chunks(chunk_lol_markdown(MARKDOWN, PATCH_METADATA))
    api_main.orchestrator = ChatOrchestrator(store=store)

    client = TestClient(api_main.app)
    patches = client.get("/patches", params={"game": "lol"}).json()["patches"]
    assert patches[0]["patch_version"] == "26.12"
    assert patches[0]["changes"][0]["chunk_id"]
    assert patches[0]["changes"][0]["summary"]

    response = client.post(
        "/chat",
        json={
            "game": "lol",
            "message": "가장 최신의 패치노트를 보여줘.",
            "chat_history": [],
            "top_k": 8,
            "debug": True,
        },
    ).json()
    assert "26.12" in response["answer"]
    assert len(response["sources"]) == 1
    assert response["navigation_target"]["patch_version"] == "26.12"
    assert response["debug_trace"]["generation"] == "latest_patch_dashboard_summary"


def test_dashboard_exposes_all_changes_section_counts_and_focused_summaries() -> None:
    from patchlog.dashboard import build_patch_dashboard

    chunks = chunk_lol_markdown(MARKDOWN, PATCH_METADATA)
    rows = [
        {
            "chunk_id": chunk.chunk_id,
            "document": chunk.document,
            "metadata": chunk.metadata,
        }
        for chunk in chunks
    ]

    patches = build_patch_dashboard(rows, card_limit=2)

    assert patches[0]["change_count"] == 3
    assert len(patches[0]["changes"]) == 2
    assert len(patches[0]["all_changes"]) == 3
    assert patches[0]["section_counts"] == {"champion": 2, "item": 1}
    aatrox = next(change for change in patches[0]["all_changes"] if change["target"] == "아트록스")
    assert aatrox["summary"] == "Q - 다르킨의 검 · 검 끝 추가 피해량: 70 ⇒ 75"


def test_dashboard_formats_overwatch_plain_ability_headings_as_bullets() -> None:
    from patchlog.dashboard import summarize_document

    document = """
[overwatch] 패치 2026-05-22 - 제트팩 캣

### [제트팩 캣](https://example.com/jetpack-cat.png)

통통 튀는 꾹꾹이

- 튕기기 치유량이 25%에서 35%로 증가했습니다.

양발냥이

- 추가 사격 피해가 25%에서 30%로 증가했습니다.

방울 폭탄

- 폭발 피해가 100에서 120으로 증가했습니다.

젤리 견인

- 연료 1%당 기술 피해가 10에서 7.5로 감소했습니다.
"""

    assert summarize_document(document, "제트팩 캣", limit=500) == (
        "• 통통 튀는 꾹꾹이 - 튕기기 치유량이 25%에서 35%로 증가했습니다.\n"
        "• 양발냥이 - 추가 사격 피해가 25%에서 30%로 증가했습니다.\n"
        "• 방울 폭탄 - 폭발 피해가 100에서 120으로 증가했습니다.\n"
        "• 젤리 견인 - 연료 1%당 기술 피해가 10에서 7.5로 감소했습니다."
    )


def test_dashboard_summary_removes_internal_prefix_with_date_versions() -> None:
    from patchlog.dashboard import summarize_document

    document = (
        "[overwatch] 패치 2026-05-27 - 버그 수정 패치\n\n"
        "### 버그 수정 패치\n\n"
        "버그 수정 패치입니다."
    )

    assert summarize_document(document, "버그 수정 패치") == "버그 수정 패치입니다."


def test_streamlit_section_filters_are_game_specific() -> None:
    from app.streamlit_app import SECTION_FILTERS_BY_GAME

    assert SECTION_FILTERS_BY_GAME["lol"] == ("all", "champion", "item", "rune", "system")
    assert SECTION_FILTERS_BY_GAME["valorant"] == ("all", "agent", "weapon", "map", "system")
    assert SECTION_FILTERS_BY_GAME["overwatch"] == ("all", "hero", "map", "system")


def test_dashboard_overrides_item_images_from_catalog() -> None:
    from patchlog.dashboard import build_patch_dashboard

    rows = [
        {
            "chunk_id": "lol-26.12-기사의-맹세-0",
            "document": "[lol] 패치 26.12 - 기사의 맹세\n\n### 기사의 맹세\n\n- 체력: 1 ⇒ 2",
            "metadata": {
                **PATCH_METADATA,
                "section": "item",
                "target": "기사의 맹세",
                "change_type": "buff",
                "image_url": "https://example.com/wrong.png",
                "image_url_kind": "asset",
            },
        }
    ]

    patches = build_patch_dashboard(rows)
    change = patches[0]["all_changes"][0]

    assert change["image_url"].endswith("/img/item/3109.png")
    assert change["image_url_kind"] == "catalog"


def test_dashboard_catalog_can_correct_legacy_sections() -> None:
    from patchlog.dashboard import build_patch_dashboard

    rows = [
        {
            "chunk_id": "lol-26.12-lich-bane-0",
            "document": "[lol] 패치 26.12 - 리치베인\n\n### 리치베인\n\n- 피해량: 1 ⇒ 2",
            "metadata": {
                **PATCH_METADATA,
                "section": "system",
                "target": "리치베인",
                "change_type": "buff",
            },
        },
        {
            "chunk_id": "lol-26.12-phase-rush-0",
            "document": "[lol] 패치 26.12 - 난입\n\n### 난입\n\n- 이동 속도: 1 ⇒ 2",
            "metadata": {
                **PATCH_METADATA,
                "section": "system",
                "target": "난입",
                "change_type": "buff",
            },
        },
    ]

    changes = build_patch_dashboard(rows)[0]["all_changes"]
    by_target = {change["target"]: change for change in changes}

    assert by_target["리치베인"]["section"] == "item"
    assert by_target["리치베인"]["image_url"].endswith("/img/item/3100.png")
    assert by_target["난입"]["section"] == "rune"
    assert "PhaseRush.png" in by_target["난입"]["image_url"]


def test_streamlit_only_uses_trusted_non_champion_image_urls() -> None:
    from app.streamlit_app import _entity_icon_html

    unsafe_item_icon = _entity_icon_html(
        {
            "section": "item",
            "image_url": "https://example.com/wrong-champion.png",
            "image_url_kind": "asset",
        }
    )
    direct_item_icon = _entity_icon_html(
        {
            "section": "item",
            "image_url": "https://example.com/item.png",
            "image_url_kind": "direct",
        }
    )
    catalog_item_icon = _entity_icon_html(
        {
            "section": "item",
            "image_url": "https://example.com/catalog-item.png",
            "image_url_kind": "catalog",
        }
    )
    champion_icon = _entity_icon_html(
        {
            "section": "champion",
            "image_url": "https://example.com/champion.png",
        }
    )
    multi_agent_icon = _entity_icon_html(
        {
            "section": "agent",
            "agent_image_urls": [
                "https://example.com/skye.png",
                "https://example.com/neon.png",
                "https://example.com/fade.png",
            ],
        }
    )

    assert "entity-fallback item" in unsafe_item_icon
    assert "wrong-champion.png" not in unsafe_item_icon
    assert "entity-icon" in direct_item_icon
    assert "item.png" in direct_item_icon
    assert "entity-icon" in catalog_item_icon
    assert "catalog-item.png" in catalog_item_icon
    assert "entity-icon" in champion_icon
    assert "entity-icons" in multi_agent_icon
    assert multi_agent_icon.count("<img") == 3
    assert "skye.png" in multi_agent_icon


def test_streamlit_empty_filter_state_explains_active_filters() -> None:
    from app.streamlit_app import _empty_filter_html

    html = _empty_filter_html(
        {
            "version": "26.12",
            "section": "champion",
            "change_type": "buff",
            "query": "없는대상",
            "patches": [],
            "patch_count": 0,
            "change_count": 0,
        }
    )

    assert "현재 조건: 패치 26.12 · 챔피언 · 상향 · 검색 없는대상" in html
    assert "검색어의 띄어쓰기" in html
    assert "전체 변경" in html
