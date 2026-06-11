from __future__ import annotations

from patchlog.models import ChatMessage, Game, QueryAnalysis
import re


TARGETS_BY_GAME: dict[Game, tuple[str, ...]] = {
    "lol": ("애쉬",),
    "valorant": ("제트",),
    "overwatch": ("애쉬", "겐지"),
}

CHANGE_KEYWORDS = {
    "nerf": ("너프", "약화", "하향"),
    "buff": ("버프", "강화", "상향"),
    "adjust": ("조정",),
}

SECTION_KEYWORDS = {
    "champion": ("챔피언", "캐릭터"),
    "agent": ("요원", "에이전트"),
    "hero": ("영웅", "히어로"),
    "item": ("아이템", "장비"),
    "weapon": ("무기", "총기", "총", "산탄총"),
    "rune": ("룬", "핵심룬", "핵심 룬"),
    "map": ("맵", "지도", "전장"),
    "system": ("시스템", "모드", "게임플레이"),
}

PATCH_FOLLOWUP_KEYWORDS = (
    "그럼",
    "최근",
    "이번",
    "패치",
    "변경",
    "변경사항",
    "너프",
    "버프",
    "하향",
    "상향",
    "약화",
    "강화",
    "조정",
    "스킬",
    "아이템",
    "룬",
    "챔피언",
    "영웅",
    "요원",
    "에이전트",
    "무기",
    "맵",
)
CONTEXTUAL_FOLLOWUP_KEYWORDS = (
    "그럼",
    "그건",
    "그거",
    "걔",
    "해당",
    "최근 너프만",
    "최근 버프만",
    "최근 하향만",
    "최근 상향만",
    "이전 변경",
    "관련 이전",
)
REQUEST_KEYWORDS = (
    "패치",
    "변경",
    "변경사항",
    "너프",
    "버프",
    "하향",
    "상향",
    "약화",
    "강화",
    "조정",
    "수정",
)
GENERIC_TARGET_WORDS = {
    "최신",
    "가장",
    "이번",
    "최근",
    "패치",
    "패치노트",
    "변경",
    "변경사항",
    "너프",
    "버프",
    "하향",
    "상향",
    "약화",
    "강화",
    "조정",
    "수정",
    "챔피언",
    "영웅",
    "요원",
    "아이템",
    "무기",
    "룬",
    "맵",
    "시스템",
}


def analyze_query(
    message: str,
    game: Game,
    chat_history: list[ChatMessage] | None = None,
    known_targets: list[str] | None = None,
) -> QueryAnalysis:
    """Extract search text and metadata except game.

    The game is intentionally not inferred from the message. It is supplied by
    the active UI tab and enforced by the retrieval orchestrator.
    """

    filter_data: dict[str, str] = {}
    target = _extract_target(message, game, known_targets=known_targets)
    has_unknown_target = _has_unknown_explicit_target(message, game, known_targets=known_targets)
    if target is None and chat_history and is_contextual_followup(message) and not has_unknown_target:
        target = _last_target_from_history(chat_history, game, known_targets=known_targets)
    if target:
        filter_data["target"] = target

    change_type = _extract_change_type(message)
    if change_type:
        filter_data["change_type"] = change_type

    section = _extract_section(message)
    if section:
        filter_data["section"] = section

    patch_version = _extract_patch_version(message)
    if patch_version:
        filter_data["patch_version"] = patch_version

    return QueryAnalysis(query=message, filter=filter_data)


def _extract_target(
    text: str,
    game: Game,
    *,
    known_targets: list[str] | None = None,
) -> str | None:
    targets = known_targets or list(TARGETS_BY_GAME[game])
    compact_text = _compact(text)
    for target in sorted(targets, key=len, reverse=True):
        if target in text or _compact(target) in compact_text:
            return target
    return None


def _last_target_from_history(
    chat_history: list[ChatMessage],
    game: Game,
    *,
    known_targets: list[str] | None = None,
) -> str | None:
    for message in reversed(chat_history):
        target = _extract_target(message.content, game, known_targets=known_targets)
        if target:
            return target
    return None


def _extract_change_type(text: str) -> str | None:
    for change_type, keywords in CHANGE_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            return change_type
    return None


def _extract_section(text: str) -> str | None:
    compact_text = _compact(text)
    for section, keywords in SECTION_KEYWORDS.items():
        if any(_compact(keyword) in compact_text for keyword in keywords):
            return section
    return None


def _extract_patch_version(text: str) -> str | None:
    match = re.search(r"(?<!\d)(\d{2}\.\d{1,2})(?!\d)", text)
    if not match:
        return None
    major, minor = match.group(1).split(".", maxsplit=1)
    return f"{int(major)}.{int(minor)}"


def is_patch_followup(text: str) -> bool:
    compact_text = _compact(text)
    return any(_compact(keyword) in compact_text for keyword in PATCH_FOLLOWUP_KEYWORDS)


def is_contextual_followup(text: str) -> bool:
    compact_text = _compact(text)
    return any(_compact(keyword) in compact_text for keyword in CONTEXTUAL_FOLLOWUP_KEYWORDS)


def has_unknown_explicit_target(
    text: str,
    game: Game,
    *,
    known_targets: list[str] | None = None,
) -> bool:
    return _has_unknown_explicit_target(text, game, known_targets=known_targets)


def _has_unknown_explicit_target(
    text: str,
    game: Game,
    *,
    known_targets: list[str] | None = None,
) -> bool:
    if _extract_target(text, game, known_targets=known_targets):
        return False
    if _extract_patch_version(text):
        return False
    compact_text = _compact(text)
    if not any(_compact(keyword) in compact_text for keyword in REQUEST_KEYWORDS):
        return False
    candidate = _explicit_target_candidate(text)
    if not candidate:
        return False
    return _compact(candidate) not in {_compact(word) for word in GENERIC_TARGET_WORDS}


def _explicit_target_candidate(text: str) -> str | None:
    cleaned = re.sub(r"[?!.,。！？]", " ", text).strip()
    patterns = (
        r"^(.+?)\s*(?:패치|변경사항|변경|너프|버프|하향|상향|약화|강화|조정|수정)",
        r"(?:패치|변경사항|변경|너프|버프|하향|상향|약화|강화|조정|수정)\s+(.+?)\s*(?:알려|보여|궁금|있어|해줘|좀|$)",
    )
    for pattern in patterns:
        match = re.search(pattern, cleaned)
        if not match:
            continue
        candidate = match.group(1)
        candidate = re.sub(r"\b(최근|이번|가장|최신|그럼|그거|그건|해당)\b", " ", candidate)
        candidate = re.sub(r"\s+", " ", candidate).strip()
        candidate = candidate.strip(" 은는이가을를의에대해서")
        if candidate:
            return candidate
    return None


def _compact(text: str) -> str:
    return "".join(text.split()).lower()
