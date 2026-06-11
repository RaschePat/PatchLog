from __future__ import annotations

import html
import os
from typing import Any

import requests
import streamlit as st


API_BASE_URL = os.getenv("PATCHLOG_API_URL", "http://127.0.0.1:8000")
GAMES = {
    "lol": "League of Legends",
    "valorant": "Valorant",
    "overwatch": "Overwatch",
}
GAME_ACCENTS = {
    "lol": "#e7c365",
    "valorant": "#ff4655",
    "overwatch": "#f99e1a",
}
CARD_LIMIT_PER_PATCH = 8
SECTION_FILTERS = {
    "all": "전체 섹션",
    "champion": "챔피언",
    "agent": "요원",
    "hero": "영웅",
    "item": "아이템",
    "weapon": "무기",
    "rune": "룬",
    "map": "맵",
    "system": "시스템",
}
SECTION_FILTERS_BY_GAME = {
    "lol": ("all", "champion", "item", "rune", "system"),
    "valorant": ("all", "agent", "weapon", "map", "system"),
    "overwatch": ("all", "hero", "map", "system"),
}
CHANGE_FILTERS = {
    "all": "전체 변경",
    "buff": "상향",
    "nerf": "하향",
    "adjust": "조정",
    "bugfix": "수정",
    "rework": "개편",
    "new": "신규",
}
GAME_SEARCH_PLACEHOLDERS = {
    "lol": "챔피언, 아이템, 스킬명 검색",
    "valorant": "요원, 무기, 맵 이름 검색",
    "overwatch": "영웅, 전장, 스킬명 검색",
}
GAME_DOMAIN_HINTS = {
    "lol": "챔피언, 아이템, 룬",
    "valorant": "요원, 무기, 맵",
    "overwatch": "영웅, 전장, 시스템",
}
GAME_CHAT_INTROS = {
    "lol": "최신 패치, 특정 챔피언 상향/하향, 패치별 변경점을 물어보세요.",
    "valorant": "최신 패치, 특정 요원/무기 변경, 맵 업데이트를 물어보세요.",
    "overwatch": "최신 패치, 특정 영웅 변경, 전장 업데이트를 물어보세요.",
}


def main() -> None:
    st.set_page_config(page_title="PATCHLOG", layout="wide")
    _init_state()
    _inject_css()

    left_col, main_col, chat_col = st.columns([0.18, 0.64, 0.18], gap="large")
    active_game = st.session_state.active_game_tab

    with left_col:
        _render_left_nav(active_game)
    active_game = st.session_state.active_game_tab
    patches = _call_patches_api(active_game)

    with main_col:
        _render_patch_central(active_game, patches)
    with chat_col:
        _render_ai_panel(active_game)


def _init_state() -> None:
    st.session_state.setdefault("active_game_tab", "lol")
    st.session_state.setdefault("selected_chunk_id_by_game", {})
    st.session_state.setdefault("referenced_chunk_ids_by_game", {})
    st.session_state.setdefault("last_sources_by_game", {})
    st.session_state.setdefault("last_debug_by_game", {})
    for game in GAMES:
        st.session_state.setdefault(_history_key(game), [])


def _hero_style(thumbnail_url: Any) -> str:
    if not thumbnail_url:
        return ""
    safe_url = str(thumbnail_url).strip().replace("\\", "/").replace("'", "%27").replace(")", "%29")
    if not safe_url.startswith("http"):
        return ""
    return (
        "background-image: "
        "linear-gradient(90deg, rgba(15,13,19,.92) 0%, rgba(15,13,19,.64) 46%, rgba(15,13,19,.82) 100%), "
        "linear-gradient(180deg, rgba(15,13,19,.18) 0%, rgba(15,13,19,.88) 100%), "
        f"url('{safe_url}');"
    )


def _inject_css() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
        .stApp {
            background: #050505;
            color: #e6e0e9;
            font-family: Inter, sans-serif;
        }
        [data-testid="stHeader"] { background: transparent; }
        [data-testid="stSidebar"] { display: none; }
        .block-container {
            max-width: 1440px;
            padding: 1.25rem 1.5rem 2rem;
        }
        div[data-testid="stVerticalBlock"] { gap: 0.8rem; }
        div[data-testid="column"]:has(.side-panel),
        div[data-testid="column"]:has(.ai-panel) {
            height: 500px;
            max-height: 500px;
            overflow-y: auto;
            z-index: 4;
            scrollbar-width: thin;
            scrollbar-color: #494551 transparent;
            background: #0b0910;
            border: 1px solid #2b292f;
            border-radius: 8px;
            padding: 28px 18px 18px;
            box-shadow: 0 18px 44px rgba(0,0,0,.28);
        }
        .st-emotion-cache-13o7eu2 {
            position: sticky;
            top: 200px;
        }
        div[data-testid="column"]:has(.side-panel) {
            background: #050505;
        }
        div[data-testid="column"]:has(.side-panel)::-webkit-scrollbar,
        div[data-testid="column"]:has(.ai-panel)::-webkit-scrollbar {
            width: 6px;
        }
        div[data-testid="column"]:has(.side-panel)::-webkit-scrollbar-thumb,
        div[data-testid="column"]:has(.ai-panel)::-webkit-scrollbar-thumb {
            background: #494551;
            border-radius: 999px;
        }
        .side-panel {
            display: none;
        }
        .lobby-shell {
            min-height: 100%;
            display: flex;
            flex-direction: column;
        }
        .lobby-title {
            color: #ff4655;
            font-size: 28px;
            font-weight: 800;
            line-height: 1;
            margin-bottom: 4px;
        }
        .muted { color: #cbc4d2; }
        div[role="radiogroup"] label {
            background: #1d1b20;
            border: 1px solid #2b292f;
            border-left: 4px solid transparent;
            border-radius: 4px;
            padding: 10px 12px;
            margin: 14px 0;
            min-height: 46px;
        }
        div[role="radiogroup"] input[type="radio"] {
            accent-color: var(--accent);
        }
        div[role="radiogroup"] label:has(input:checked) {
            border-left-color: var(--accent);
            background: #2b292f;
            color: var(--accent);
        }
        .lobby-footnote {
            color: #f4eef7;
            font-size: 14px;
            line-height: 1.75;
            margin-top: auto;
            padding-top: 48px;
        }
        .topbar {
            display: flex;
            align-items: center;
            gap: 28px;
            margin-bottom: 28px;
        }
        .brand {
            color: #ff4655;
            font-size: 25px;
            font-weight: 800;
            letter-spacing: 0;
        }
        .hero {
            border: 1px solid #2b292f;
            border-radius: 8px;
            padding: 40px 34px 36px;
            margin-bottom: 28px;
            background:
              linear-gradient(90deg, rgba(15,13,19,.92) 0%, rgba(15,13,19,.64) 46%, rgba(15,13,19,.82) 100%),
              radial-gradient(circle at 82% 12%, rgba(231,195,101,.22), transparent 34%),
              #141218;
            background-size: cover;
            background-position: center;
            overflow: hidden;
            box-shadow: inset 0 0 90px rgba(0,0,0,.36);
        }
        .hero-label {
            display: inline-block;
            border: 0;
            color: var(--accent);
            font-size: 11px;
            font-weight: 800;
            letter-spacing: .06em;
            margin-bottom: 10px;
        }
        .hero h1 {
            font-size: 46px;
            line-height: 1.08;
            margin: 0 0 10px;
            color: #f4eef7;
        }
        .filter-panel {
            border: 1px solid #2b292f;
            border-radius: 8px;
            padding: 14px 16px 10px;
            margin: -8px 0 22px;
            background: rgba(20,18,24,.92);
        }
        .filter-title {
            color: var(--accent);
            font-size: 12px;
            font-weight: 800;
            letter-spacing: .08em;
            text-transform: uppercase;
            margin-bottom: 8px;
        }
        .filter-result {
            color: #cbc4d2;
            font-size: 12px;
            font-weight: 700;
            margin-top: 4px;
        }
        .filter-summary {
            display: flex;
            flex-wrap: wrap;
            gap: 7px;
            margin: 8px 0 2px;
        }
        .filter-chip {
            border: 1px solid #494551;
            border-radius: 4px;
            color: #e6e0e9;
            background: #211f24;
            padding: 5px 8px;
            font-size: 12px;
            font-weight: 800;
        }
        .filter-chip.active {
            border-color: var(--accent);
            color: var(--accent);
            background: rgba(231,195,101,.08);
        }
        .patch-card {
            background: rgba(15, 18, 20, .92);
            border: 1px solid #2b292f;
            border-radius: 8px;
            padding: 22px 24px;
            margin-bottom: 10px;
        }
        .patch-card.highlight {
            border-color: var(--accent);
            box-shadow: 0 0 0 1px rgba(231,195,101,.45);
        }
        .patch-head {
            display: flex;
            align-items: center;
            gap: 16px;
            border-bottom: 1px solid #494551;
            padding-bottom: 16px;
            margin-bottom: 18px;
        }
        .version {
            border: 1px solid var(--accent);
            color: var(--accent);
            background: rgba(231,195,101,.08);
            padding: 10px 8px;
            font-weight: 800;
            border-radius: 4px;
        }
        .patch-title {
            color: #e6e0e9;
            font-weight: 800;
            font-size: 20px;
        }
        .patch-meta {
            color: #cbc4d2;
            font-size: 12px;
            font-weight: 700;
            letter-spacing: .08em;
            text-transform: uppercase;
        }
        .section-row {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin: -6px 0 16px;
        }
        .section-chip {
            border: 1px solid #494551;
            border-radius: 4px;
            color: #cbc4d2;
            padding: 4px 7px;
            font-size: 11px;
            font-weight: 800;
            text-transform: uppercase;
        }
        .section-heading {
            color: var(--accent);
            font-size: 12px;
            font-weight: 800;
            letter-spacing: .08em;
            text-transform: uppercase;
            margin: 16px 0 8px;
        }
        .patch-actions {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 10px;
            margin: -2px 0 24px;
            color: #cbc4d2;
            font-size: 12px;
            font-weight: 700;
        }
        .change-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 12px;
            align-items: stretch;
        }
        .change-card {
            background: linear-gradient(180deg, #2d2a31, #262329);
            border-left: 4px solid #494551;
            border-radius: 4px;
            padding: 13px 15px;
            min-height: 118px;
            display: flex;
            flex-direction: column;
            gap: 8px;
            scroll-margin-top: 24px;
        }
        .change-card.referenced {
            border-color: rgba(231,195,101,.6);
            background: linear-gradient(180deg, rgba(231,195,101,.13), #262329 44%);
        }
        .change-card.selected {
            border-color: var(--accent);
            box-shadow: 0 0 0 1px rgba(231,195,101,.35);
            background: linear-gradient(180deg, rgba(231,195,101,.2), #262329 50%);
        }
        .change-card.buff { border-left-color: #7ddc8a; }
        .change-card.nerf { border-left-color: #ff7b7b; }
        .change-card.adjust { border-left-color: #e7c365; }
        .change-card.bugfix { border-left-color: #8ab4ff; }
        .change-card.rework,
        .change-card.new { border-left-color: #c49cff; }
        .change-title {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 10px;
            color: #f4eef7;
            font-size: 16px;
            font-weight: 800;
            min-height: 38px;
        }
        .identity {
            display: flex;
            align-items: center;
            gap: 10px;
            min-width: 0;
        }
        .identity span {
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        .entity-icons {
            display: inline-flex;
            align-items: center;
            flex: 0 0 auto;
        }
        .entity-icons .entity-icon {
            margin-left: -8px;
            border: 2px solid #211f24;
            box-shadow: 0 0 0 1px rgba(255,255,255,.08);
        }
        .entity-icons .entity-icon:first-child {
            margin-left: 0;
        }
        .entity-icon {
            width: 36px;
            height: 36px;
            border-radius: 6px;
            object-fit: cover;
            border: 1px solid #494551;
            background: #141218;
            flex: 0 0 auto;
        }
        .entity-fallback {
            width: 36px;
            height: 36px;
            border-radius: 6px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            border: 1px solid #494551;
            background: rgba(231,195,101,.1);
            color: var(--accent);
            font-size: 12px;
            font-weight: 800;
            flex: 0 0 auto;
        }
        .entity-fallback.item { color: #ffdf93; }
        .entity-fallback.agent { color: #ff8a80; }
        .entity-fallback.hero { color: #f99e1a; }
        .entity-fallback.weapon { color: #8ab4ff; }
        .entity-fallback.rune { color: #c49cff; }
        .entity-fallback.map { color: #7ddc8a; }
        .entity-fallback.system { color: #8ab4ff; }
        .tag {
            color: #141218;
            background: var(--accent);
            border-radius: 3px;
            padding: 3px 6px;
            font-size: 10px;
            font-weight: 800;
            height: fit-content;
            flex: 0 0 auto;
        }
        .tag.buff { background: #7ddc8a; }
        .tag.nerf { background: #ff7b7b; }
        .tag.adjust { background: #e7c365; }
        .tag.bugfix { background: #8ab4ff; }
        .tag.rework,
        .tag.new { background: #c49cff; }
        .tag.system { background: #cbc4d2; }
        .tag.unknown { background: #cbc4d2; }
        .tag-text {
            display: inline-block;
            color: #141218;
        }
        .summary {
            color: #d4ced9;
            font-size: 14px;
            line-height: 1.5;
        }
        .summary-line {
            display: flex;
            gap: 8px;
            align-items: flex-start;
            padding-top: 7px;
            border-top: 1px solid rgba(203,196,210,.12);
        }
        .summary-line:first-child {
            padding-top: 0;
            border-top: 0;
        }
        .summary-text {
            min-width: 0;
            overflow-wrap: anywhere;
            word-break: keep-all;
        }
        .summary-ability {
            color: #f4eef7;
            font-weight: 800;
            margin-right: 4px;
        }
        .ability-icon {
            width: 22px;
            height: 22px;
            border-radius: 4px;
            object-fit: cover;
            border: 1px solid #494551;
            background: #141218;
            flex: 0 0 auto;
            margin-top: 1px;
        }
        .ai-panel {
            background: transparent;
            border: 0;
            border-radius: 8px;
            padding: 0;
        }
        .ai-title {
            color: #f4eef7;
            font-size: 22px;
            font-weight: 800;
            letter-spacing: .08em;
        }
        .chat-log {
            background: #0b0910;
            border: 1px solid #2b292f;
            border-radius: 4px;
            min-height: 220px;
            max-height: 220px;
            overflow-y: auto;
            padding: 16px;
            margin: 16px 0;
        }
        .bubble {
            background: #211f24;
            color: #e6e0e9;
            border-radius: 6px;
            padding: 12px 14px;
            margin: 0 0 12px;
            font-size: 14px;
            line-height: 1.45;
            width: fit-content;
            max-width: 92%;
        }
        .bubble.user {
            background: rgba(231,195,101,.18);
            border: 1px solid rgba(231,195,101,.4);
            color: #ffdf93;
            margin-left: auto;
        }
        .source-chip {
            display: inline-block;
            border: 1px solid #494551;
            border-radius: 4px;
            color: #cbc4d2;
            padding: 4px 7px;
            margin: 4px 4px 0 0;
            font-size: 11px;
            font-weight: 700;
            text-decoration: none;
            cursor: pointer;
        }
        .source-chip:hover {
            border-color: var(--accent);
            color: var(--accent);
        }
        .selected-evidence {
            border: 1px solid rgba(231,195,101,.55);
            border-radius: 8px;
            padding: 16px;
            margin: -8px 0 22px;
            background: linear-gradient(180deg, rgba(231,195,101,.12), rgba(15,18,20,.96));
        }
        .selected-evidence-label {
            color: var(--accent);
            font-size: 11px;
            font-weight: 800;
            letter-spacing: .08em;
            text-transform: uppercase;
            margin-bottom: 10px;
        }
        .empty {
            border: 1px dashed #494551;
            border-radius: 8px;
            padding: 32px;
            color: #cbc4d2;
            background: #141218;
        }
        .stButton > button {
            border-radius: 4px;
            border: 1px solid var(--accent);
            background: transparent;
            color: var(--accent);
            font-weight: 800;
        }
        .stTextInput input {
            border-radius: 4px;
            border: 1px solid #494551;
            background: #211f24;
            color: #e6e0e9;
        }
        div[data-testid="stForm"] {
            border: 1px solid #211f24;
            border-radius: 8px;
            padding: 14px;
            background: #050505;
        }
        @media (max-width: 1000px) {
            div[data-testid="column"]:has(.side-panel),
            div[data-testid="column"]:has(.ai-panel) {
                position: static !important;
                height: auto;
                max-height: none;
                overflow: visible;
            }
            .change-grid { grid-template-columns: 1fr; }
            .hero h1 { font-size: 30px; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_left_nav(active_game: str) -> None:
    st.markdown('<div class="side-panel"></div>', unsafe_allow_html=True)
    st.markdown('<div class="lobby-shell">', unsafe_allow_html=True)
    st.markdown('<div class="lobby-title">Patch Reader</div>', unsafe_allow_html=True)
    st.markdown('<div class="muted">Global Patch Hub</div>', unsafe_allow_html=True)
    st.write("")
    st.markdown(
        f'<div style="--accent:{GAME_ACCENTS[active_game]}">',
        unsafe_allow_html=True,
    )
    st.radio(
        "게임 선택",
        options=list(GAMES.keys()),
        key="active_game_tab",
        format_func=lambda game: GAMES[game],
        label_visibility="collapsed",
    )
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="lobby-footnote">Patch data updates locally<br>from official patch notes.</div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


def _render_patch_central(game: str, patches: list[dict[str, Any]]) -> None:
    accent = GAME_ACCENTS[game]
    st.markdown(f'<div style="--accent:{accent}">', unsafe_allow_html=True)
    st.markdown(
        """
        <div class="topbar">
          <div class="brand">PATCH CENTRAL</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not patches:
        st.markdown(
            f'<div class="empty">아직 표시할 {html.escape(GAMES[game])} 패치 데이터가 없습니다. 먼저 수집과 인덱싱을 실행하세요.</div>',
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)
        return

    latest = patches[0]
    hero_style = _hero_style(latest.get("thumbnail_url"))
    st.markdown(
        f"""
        <div class="hero" style="{hero_style}">
          <div class="hero-label">LATEST PATCH</div>
          <h1>{html.escape(latest["title"])}</h1>
          <div class="muted">Released {html.escape(latest["patch_date"])} · {latest["change_count"]} indexed changes</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    selected_chunk_id = st.session_state.selected_chunk_id_by_game.get(game)
    referenced_chunk_ids = set(st.session_state.referenced_chunk_ids_by_game.get(game, []))
    selected_change = _find_change_in_patches(patches, selected_chunk_id)
    if selected_change:
        st.markdown(_selected_evidence_html(selected_change), unsafe_allow_html=True)

    filter_state = _render_patch_filters(game, patches)
    filtered_patches = filter_state["patches"]
    if not filtered_patches:
        st.markdown(
            _empty_filter_html(filter_state),
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)
        return

    for patch in filtered_patches:
        expanded_key = f"expanded_patch_{game}_{patch['patch_version']}"
        st.session_state.setdefault(expanded_key, False)
        display_changes = patch["all_changes"] if st.session_state[expanded_key] else patch["changes"]
        selected_change = _find_selected_change(patch, selected_chunk_id)
        referenced_changes = _find_referenced_changes(patch, referenced_chunk_ids)
        display_changes = _ensure_visible_changes(display_changes, [selected_change, *referenced_changes])
        patch_selected = selected_change is not None
        st.markdown(
            _patch_card_html(patch, display_changes, selected_chunk_id, referenced_chunk_ids, patch_selected),
            unsafe_allow_html=True,
        )
        is_expanded = st.session_state[expanded_key]
        hidden_count = 0 if is_expanded else max(patch["change_count"] - len(patch["changes"]), 0)
        st.markdown(
            f'<div class="patch-actions"><span>{_patch_action_hint(patch, hidden_count)}</span></div>',
            unsafe_allow_html=True,
        )
        action_col, link_col = st.columns([0.48, 0.52], gap="small")
        if patch["change_count"] > len(patch["changes"]):
            label = "요약만 보기" if is_expanded else f"전체 {patch['change_count']}개 보기"
            with action_col:
                if st.button(label, key=f"toggle-{game}-{patch['patch_version']}", use_container_width=True):
                    st.session_state[expanded_key] = not st.session_state[expanded_key]
                    st.rerun()
        else:
            with action_col:
                st.button("전체 표시 중", key=f"toggle-disabled-{game}-{patch['patch_version']}", disabled=True, use_container_width=True)
        with link_col:
            st.link_button(f"{patch['patch_version']} 원문 열기", patch["source_url"], use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)


def _patch_action_hint(patch: dict[str, Any], hidden_count: int) -> str:
    if hidden_count > 0:
        return html.escape(f"요약 {len(patch['changes'])}개 표시 · 숨겨진 변경 {hidden_count}개")
    return html.escape(f"{patch['change_count']}개 변경 모두 표시")


def _render_patch_filters(game: str, patches: list[dict[str, Any]]) -> dict[str, Any]:
    versions = ["all", *[patch["patch_version"] for patch in patches]]
    section_options = list(SECTION_FILTERS_BY_GAME.get(game, tuple(SECTION_FILTERS)))
    section_key = f"filter_section_{game}"
    if st.session_state.get(section_key) not in section_options:
        st.session_state[section_key] = "all"
    st.markdown(
        '<div class="filter-panel"><div class="filter-title">PATCH FILTERS</div></div>',
        unsafe_allow_html=True,
    )
    version_col, section_col, change_col, reset_col = st.columns([0.25, 0.28, 0.28, 0.19], gap="small")
    with version_col:
        version = st.selectbox(
            "패치",
            options=versions,
            key=f"filter_version_{game}",
            format_func=lambda value: "전체 패치" if value == "all" else value,
        )
    with section_col:
        section = st.selectbox(
            "섹션",
            options=section_options,
            key=section_key,
            format_func=lambda value: SECTION_FILTERS[value],
        )
    with change_col:
        change_type = st.selectbox(
            "변경",
            options=list(CHANGE_FILTERS.keys()),
            key=f"filter_change_{game}",
            format_func=lambda value: CHANGE_FILTERS[value],
        )
    with reset_col:
        st.write("")
        if st.button("필터 초기화", key=f"filter_reset_{game}", use_container_width=True):
            _reset_patch_filters(game, patches)
            st.rerun()
    query = st.text_input(
        "검색",
        key=f"filter_query_{game}",
        placeholder=GAME_SEARCH_PLACEHOLDERS.get(game, "패치 항목 검색"),
    )
    filtered = _filter_patches(
        patches,
        version=version,
        section=section,
        change_type=change_type,
        query=query,
    )
    total_changes = sum(patch["change_count"] for patch in filtered)
    st.markdown(
        _filter_summary_html(
            version=version,
            section=section,
            change_type=change_type,
            query=query,
            patch_count=len(filtered),
            change_count=total_changes,
        ),
        unsafe_allow_html=True,
    )
    return {
        "patches": filtered,
        "version": version,
        "section": section,
        "change_type": change_type,
        "query": query,
        "game": game,
        "patch_count": len(filtered),
        "change_count": total_changes,
    }


def _reset_patch_filters(game: str, patches: list[dict[str, Any]]) -> None:
    st.session_state[f"filter_version_{game}"] = "all"
    st.session_state[f"filter_section_{game}"] = "all"
    st.session_state[f"filter_change_{game}"] = "all"
    st.session_state[f"filter_query_{game}"] = ""
    for patch in patches:
        st.session_state[f"expanded_patch_{game}_{patch['patch_version']}"] = False


def _empty_filter_html(filter_state: dict[str, Any]) -> str:
    active = _active_filter_descriptions(
        version=filter_state["version"],
        section=filter_state["section"],
        change_type=filter_state["change_type"],
        query=filter_state["query"],
    )
    active_text = " · ".join(active) if active else "전체 조건"
    hints = _empty_filter_hints(filter_state)
    hint_items = "".join(f"<li>{html.escape(hint)}</li>" for hint in hints)
    return (
        '<div class="empty">'
        '<div style="font-weight:800;color:#f4eef7;margin-bottom:8px;">필터 조건에 맞는 변경 카드가 없습니다.</div>'
        f'<div class="muted">현재 조건: {html.escape(active_text)}</div>'
        f'<ul style="margin:14px 0 0;padding-left:18px;color:#cbc4d2;">{hint_items}</ul>'
        '</div>'
    )


def _empty_filter_hints(filter_state: dict[str, Any]) -> list[str]:
    hints: list[str] = []
    game = filter_state.get("game", "lol")
    if filter_state["query"].strip():
        hints.append("검색어의 띄어쓰기나 철자를 줄여서 다시 검색해 보세요.")
    if filter_state["change_type"] != "all":
        hints.append("변경 타입을 전체 변경으로 바꾸면 더 넓게 볼 수 있습니다.")
    if filter_state["section"] != "all":
        hints.append(f"섹션을 전체 섹션으로 바꾸면 {GAME_DOMAIN_HINTS.get(game, '변경 항목')}을 함께 볼 수 있습니다.")
    if filter_state["version"] != "all":
        hints.append("패치를 전체 패치로 바꾸면 이전 패치까지 검색합니다.")
    if not hints:
        hints.append("수집/인덱싱된 데이터에 해당 항목이 없을 수 있습니다.")
    return hints[:3]


def _active_filter_descriptions(*, version: str, section: str, change_type: str, query: str) -> list[str]:
    descriptions: list[str] = []
    if version != "all":
        descriptions.append(f"패치 {version}")
    if section != "all":
        descriptions.append(SECTION_FILTERS[section])
    if change_type != "all":
        descriptions.append(CHANGE_FILTERS[change_type])
    if query.strip():
        descriptions.append(f"검색 {query.strip()}")
    return descriptions


def _filter_summary_html(
    *,
    version: str,
    section: str,
    change_type: str,
    query: str,
    patch_count: int,
    change_count: int,
) -> str:
    chips = [
        _filter_chip("패치", "전체" if version == "all" else version, version != "all"),
        _filter_chip("섹션", SECTION_FILTERS[section], section != "all"),
        _filter_chip("변경", CHANGE_FILTERS[change_type], change_type != "all"),
    ]
    if query.strip():
        chips.append(_filter_chip("검색", query.strip(), True))
    chips_html = "".join(chips)
    return (
        f'<div class="filter-summary">{chips_html}</div>'
        f'<div class="filter-result">{patch_count}개 패치 · {change_count}개 변경 표시</div>'
    )


def _filter_chip(label: str, value: str, active: bool) -> str:
    class_name = "filter-chip active" if active else "filter-chip"
    return f'<span class="{class_name}">{html.escape(label)} · {html.escape(value)}</span>'


def _filter_patches(
    patches: list[dict[str, Any]],
    *,
    version: str,
    section: str,
    change_type: str,
    query: str,
) -> list[dict[str, Any]]:
    query = _compact_text(query)
    filtered_patches: list[dict[str, Any]] = []
    for patch in patches:
        if version != "all" and patch["patch_version"] != version:
            continue
        changes = [
            change
            for change in patch.get("all_changes", [])
            if _matches_change_filter(change, section=section, change_type=change_type, query=query)
        ]
        if not changes:
            continue
        filtered_patches.append(
            {
                **patch,
                "change_count": len(changes),
                "changes": changes[:CARD_LIMIT_PER_PATCH],
                "all_changes": changes,
                "section_counts": _section_counts(changes),
            }
        )
    return filtered_patches


def _matches_change_filter(
    change: dict[str, Any],
    *,
    section: str,
    change_type: str,
    query: str,
) -> bool:
    if section != "all" and change.get("section") != section:
        return False
    if change_type != "all" and change.get("change_type") != change_type:
        return False
    if not query:
        return True
    haystack = _compact_text(
        " ".join(
            [
                str(change.get("target", "")),
                str(change.get("summary", "")),
                str(change.get("patch_version", "")),
                _section_label(str(change.get("section", ""))),
                _change_type_label(str(change.get("change_type", ""))),
            ]
        )
    )
    return query in haystack


def _section_counts(changes: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for change in changes:
        section = change.get("section", "system")
        counts[section] = counts.get(section, 0) + 1
    return counts


def _compact_text(text: str) -> str:
    return "".join(str(text).split()).lower()


def _selected_evidence_html(change: dict[str, Any]) -> str:
    return (
        '<div class="selected-evidence">'
        '<div class="selected-evidence-label">AI 선택 근거</div>'
        f'{_change_card_html(change, selected=True, referenced=True)}'
        '</div>'
    )


def _patch_card_html(
    patch: dict[str, Any],
    changes_to_render: list[dict[str, Any]],
    selected_chunk_id: str | None,
    referenced_chunk_ids: set[str],
    patch_selected: bool,
) -> str:
    patch_class = "patch-card highlight" if patch_selected else "patch-card"
    changes = _sectioned_changes_html(changes_to_render, selected_chunk_id, referenced_chunk_ids)
    section_chips = "".join(
        f'<span class="section-chip">{_section_label(section)} {count}</span>'
        for section, count in patch.get("section_counts", {}).items()
    )
    return (
        f'<div class="{patch_class}" id="{html.escape(patch["patch_version"])}">'
        '<div class="patch-head">'
        f'<div class="version">{html.escape(patch["patch_version"])}</div>'
        '<div>'
        f'<div class="patch-title">{html.escape(patch["title"])}</div>'
        f'<div class="patch-meta">Released · {html.escape(patch["patch_date"])} · {patch["change_count"]} changes</div>'
        '</div>'
        '</div>'
        f'<div class="section-row">{section_chips}</div>'
        f'{changes}'
        '</div>'
    )


def _sectioned_changes_html(
    changes: list[dict[str, Any]],
    selected_chunk_id: str | None,
    referenced_chunk_ids: set[str],
) -> str:
    groups: dict[str, list[dict[str, Any]]] = {}
    for change in changes:
        groups.setdefault(change["section"], []).append(change)

    sections: list[str] = []
    for section in ("champion", "agent", "hero", "item", "weapon", "rune", "map", "system"):
        section_changes = groups.get(section)
        if not section_changes:
            continue
        cards = "".join(
            _change_card_html(
                change,
                selected=change["chunk_id"] == selected_chunk_id,
                referenced=change["chunk_id"] in referenced_chunk_ids,
            )
            for change in section_changes
        )
        sections.append(
            f'<div class="section-heading">{_section_label(section)}</div>'
            f'<div class="change-grid">{cards}</div>'
        )
    return "".join(sections)


def _section_label(section: str) -> str:
    return {
        "champion": "챔피언",
        "agent": "요원",
        "hero": "영웅",
        "item": "아이템",
        "weapon": "무기",
        "rune": "룬",
        "map": "맵",
        "system": "시스템",
    }.get(section, section)


def _find_selected_change(patch: dict[str, Any], selected_chunk_id: str | None) -> dict[str, Any] | None:
    if not selected_chunk_id:
        return None
    for change in patch.get("all_changes", []):
        if change["chunk_id"] == selected_chunk_id:
            return change
    return None


def _find_change_in_patches(patches: list[dict[str, Any]], selected_chunk_id: str | None) -> dict[str, Any] | None:
    if not selected_chunk_id:
        return None
    for patch in patches:
        found = _find_selected_change(patch, selected_chunk_id)
        if found:
            return found
    return None


def _find_referenced_changes(patch: dict[str, Any], referenced_chunk_ids: set[str]) -> list[dict[str, Any]]:
    if not referenced_chunk_ids:
        return []
    return [change for change in patch.get("all_changes", []) if change["chunk_id"] in referenced_chunk_ids]


def _ensure_visible_changes(
    display_changes: list[dict[str, Any]],
    required_changes: list[dict[str, Any] | None],
) -> list[dict[str, Any]]:
    visible_ids = {change["chunk_id"] for change in display_changes}
    extra_changes: list[dict[str, Any]] = []
    for change in required_changes:
        if not change:
            continue
        chunk_id = change["chunk_id"]
        if chunk_id in visible_ids:
            continue
        extra_changes.append(change)
        visible_ids.add(chunk_id)
    return [*extra_changes, *display_changes]


def _change_card_html(change: dict[str, Any], *, selected: bool, referenced: bool) -> str:
    selected_class = " selected" if selected else ""
    referenced_class = " referenced" if referenced and not selected else ""
    change_type = html.escape(change["change_type"])
    change_label = html.escape(_change_type_label(change["change_type"]))
    section = str(change.get("section", "system"))
    icon_html = _entity_icon_html(change)
    return (
        f'<div id="{html.escape(change["chunk_id"])}" class="change-card {change_type}{selected_class}{referenced_class}">'
        '<div class="change-title">'
        f'<div class="identity">{icon_html}<span>{html.escape(change["target"])}</span></div>'
        f'<span class="tag {change_type}"><span class="tag-text">{change_label}</span></span>'
        '</div>'
        f'<div class="summary">{_summary_with_icons(change)}</div>'
        '</div>'
    )


def _entity_icon_html(change: dict[str, Any]) -> str:
    section = str(change.get("section", "system"))
    image_kind = str(change.get("image_url_kind", "asset"))
    agent_image_urls = [str(url) for url in change.get("agent_image_urls", []) if url]
    if section == "agent" and len(agent_image_urls) > 1:
        images = "".join(
            f'<img class="entity-icon" src="{html.escape(url)}" alt="">'
            for url in agent_image_urls[:4]
        )
        return f'<span class="entity-icons">{images}</span>'
    if change.get("image_url") and (section in {"champion", "hero"} or image_kind in {"direct", "catalog"}):
        return f'<img class="entity-icon" src="{html.escape(change["image_url"])}" alt="">'
    return (
        f'<span class="entity-fallback {html.escape(section)}">'
        f'{html.escape(_section_badge(section))}'
        '</span>'
    )


def _section_badge(section: str) -> str:
    return {
        "champion": "CH",
        "agent": "AG",
        "hero": "HE",
        "item": "IT",
        "weapon": "WP",
        "rune": "RU",
        "map": "MAP",
        "system": "SYS",
    }.get(section, "ETC")


def _change_type_label(change_type: str) -> str:
    return {
        "buff": "상향",
        "nerf": "하향",
        "adjust": "조정",
        "bugfix": "수정",
        "rework": "개편",
        "new": "신규",
        "system": "시스템",
    }.get(change_type, change_type.upper())


def _render_ai_panel(game: str) -> None:
    accent = GAME_ACCENTS[game]
    st.markdown(f'<div class="ai-panel" style="--accent:{accent}">', unsafe_allow_html=True)
    st.markdown('<div class="ai-title">AI ANALYST</div>', unsafe_allow_html=True)
    st.markdown('<div class="muted">ASK ABOUT CHANGES</div>', unsafe_allow_html=True)

    history_key = _history_key(game)
    history = st.session_state[history_key]
    log_html = ['<div class="chat-log">']
    if not history:
        log_html.append(
            f'<div class="bubble">{html.escape(GAME_CHAT_INTROS.get(game, "패치 변경점을 물어보세요."))}</div>'
        )
    for message in history[-8:]:
        role_class = "user" if message["role"] == "user" else "assistant"
        log_html.append(f'<div class="bubble {role_class}">{_markdownish_to_html(message["content"])}</div>')
    log_html.append("</div>")
    st.markdown("\n".join(log_html), unsafe_allow_html=True)

    with st.form(key=f"chat-form-{game}", clear_on_submit=True):
        prompt = st.text_input("질문", placeholder="가장 최신의 패치노트를 보여줘")
        submitted = st.form_submit_button("ASK", use_container_width=True)

    if submitted and prompt.strip():
        _submit_chat(game, prompt.strip())

    sources = st.session_state.last_sources_by_game.get(game, [])
    if sources:
        st.markdown('<div class="muted">REFERENCED CARDS</div>', unsafe_allow_html=True)
        for index, source in enumerate(sources[:3]):
            label = f'{source.get("target", "근거")} · {source.get("patch_version", "")} 보기'
            if st.button(label, key=f"source-{game}-{index}-{source.get('chunk_id')}", use_container_width=True):
                _select_source(game, source)

    st.markdown("</div>", unsafe_allow_html=True)


def _select_source(game: str, source: dict[str, Any]) -> None:
    chunk_id = source.get("chunk_id")
    if not chunk_id:
        return
    st.session_state.selected_chunk_id_by_game[game] = chunk_id
    st.session_state.referenced_chunk_ids_by_game[game] = [
        chunk_id,
        *[
            existing
            for existing in st.session_state.referenced_chunk_ids_by_game.get(game, [])
            if existing != chunk_id
        ],
    ]
    st.rerun()


def _submit_chat(game: str, prompt: str) -> None:
    history_key = _history_key(game)
    history = st.session_state[history_key]
    response = _call_chat_api(
        game=game,
        message=prompt,
        chat_history=history,
        top_k=3,
        debug=False,
    )
    answer = response["answer"]
    history.extend(
        [
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": answer},
        ]
    )
    st.session_state.last_sources_by_game[game] = response.get("sources", [])
    st.session_state.last_debug_by_game[game] = response.get("debug_trace")
    st.session_state.referenced_chunk_ids_by_game[game] = [
        source["chunk_id"]
        for source in response.get("sources", [])
        if source.get("chunk_id")
    ]

    target = response.get("navigation_target")
    if target and target.get("game") == game:
        st.session_state.selected_chunk_id_by_game[game] = target["chunk_id"]
    st.rerun()


def _call_chat_api(
    *,
    game: str,
    message: str,
    chat_history: list[dict[str, str]],
    top_k: int,
    debug: bool,
) -> dict[str, Any]:
    response = requests.post(
        f"{API_BASE_URL}/chat",
        json={
            "game": game,
            "message": message,
            "chat_history": chat_history,
            "top_k": top_k,
            "debug": debug,
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def _call_patches_api(game: str) -> list[dict[str, Any]]:
    try:
        response = requests.get(f"{API_BASE_URL}/patches", params={"game": game}, timeout=20)
        response.raise_for_status()
        return response.json().get("patches", [])
    except requests.RequestException:
        return []


def _history_key(game: str) -> str:
    return f"chat_history_{game}"


def _markdownish_to_html(text: str) -> str:
    escaped = html.escape(text)
    escaped = escaped.replace("\n", "<br>")
    return escaped


def _escape_with_breaks(text: str) -> str:
    return html.escape(text).replace("\n", "<br>")


def _summary_with_icons(change: dict[str, Any]) -> str:
    ability_icons = change.get("ability_icons") or {}
    lines = str(change["summary"]).splitlines() or [str(change["summary"])]
    rendered: list[str] = []
    for line in lines:
        heading = line.split("·", 1)[0].strip()
        icon_url = ability_icons.get(heading)
        icon_html = ""
        if icon_url:
            icon_html = f'<img class="ability-icon" src="{html.escape(icon_url)}" alt="">'
        line_html = _summary_line_html(line)
        rendered.append(
            f'<div class="summary-line">{icon_html}<span class="summary-text">{line_html}</span></div>'
        )
    return "".join(rendered)


def _summary_line_html(line: str) -> str:
    if "·" not in line:
        return html.escape(line)
    heading, detail = line.split("·", 1)
    return (
        f'<span class="summary-ability">{html.escape(heading.strip())}</span>'
        f'<span>{html.escape(detail.strip())}</span>'
    )


if __name__ == "__main__":
    main()
