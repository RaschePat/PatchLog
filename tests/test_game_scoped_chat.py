from __future__ import annotations

from patchlog.models import ChatMessage
from patchlog.retrieval.orchestrator import ChatOrchestrator


def test_same_name_ashe_is_scoped_to_lol() -> None:
    result = ChatOrchestrator().chat(
        game="lol",
        message="애쉬 최근 변경사항 알려줘",
        debug=True,
    )

    assert result.sources
    assert {source["game"] for source in result.sources} == {"lol"}
    assert result.navigation_target is not None
    assert result.navigation_target["game"] == "lol"
    assert result.debug_trace is not None
    assert result.debug_trace["final_filter"]["game"] == "lol"


def test_same_name_ashe_is_scoped_to_overwatch() -> None:
    result = ChatOrchestrator().chat(
        game="overwatch",
        message="애쉬 최근 변경사항 알려줘",
        debug=True,
    )

    assert result.sources
    assert {source["game"] for source in result.sources} == {"overwatch"}
    assert result.navigation_target is not None
    assert result.navigation_target["game"] == "overwatch"
    assert result.debug_trace is not None
    assert result.debug_trace["final_filter"]["game"] == "overwatch"


def test_ashe_in_valorant_returns_not_found() -> None:
    result = ChatOrchestrator().chat(
        game="valorant",
        message="애쉬 최근 변경사항 알려줘",
    )

    assert result.sources == []
    assert result.navigation_target is None
    assert "발로란트" in result.answer
    assert "찾지 못했습니다" in result.answer


def test_follow_up_uses_only_current_game_history() -> None:
    orchestrator = ChatOrchestrator()
    lol_history = [
        ChatMessage(role="user", content="애쉬 최근 변경사항 알려줘"),
        ChatMessage(role="assistant", content="애쉬 답변"),
    ]
    result = orchestrator.chat(
        game="lol",
        message="그럼 최근 너프만?",
        chat_history=lol_history,
        debug=True,
    )

    assert result.sources
    assert {source["game"] for source in result.sources} == {"lol"}
    assert {source["target"] for source in result.sources} == {"애쉬"}
    assert result.debug_trace is not None
    assert result.debug_trace["final_filter"]["target"] == "애쉬"
    assert result.debug_trace["final_filter"]["change_type"] == "nerf"


def test_off_topic_question_does_not_reuse_previous_target() -> None:
    orchestrator = ChatOrchestrator()
    lol_history = [
        ChatMessage(role="user", content="애쉬 최근 변경사항 알려줘"),
        ChatMessage(role="assistant", content="애쉬 답변"),
    ]
    result = orchestrator.chat(
        game="lol",
        message="김치찌개 레시피 알려줘",
        chat_history=lol_history,
        debug=True,
    )

    assert result.sources == []
    assert result.navigation_target is None
    assert "패치노트와 관련된 질문만" in result.answer
    assert result.debug_trace is not None
    assert result.debug_trace["final_filter"] == {"game": "lol"}


def test_valorant_off_topic_prompt_uses_valorant_terms() -> None:
    result = ChatOrchestrator().chat(
        game="valorant",
        message="김치찌개 레시피 알려줘",
    )

    assert result.sources == []
    assert "요원, 무기, 맵" in result.answer
    assert "챔피언, 아이템, 룬" not in result.answer


def test_overwatch_does_not_receive_lol_history() -> None:
    result = ChatOrchestrator().chat(
        game="overwatch",
        message="그럼 최근 너프만?",
        chat_history=[],
        debug=True,
    )

    assert result.debug_trace is not None
    assert result.debug_trace["final_filter"] == {
        "game": "overwatch",
        "change_type": "nerf",
    }
