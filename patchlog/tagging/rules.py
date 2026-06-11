from __future__ import annotations


NERF_KEYWORDS = (
    "하향",
    "약화",
    "감소",
    "낮아",
    "줄",
    "재사용 대기시간 증가",
    "소모량 증가",
)
BUFF_KEYWORDS = (
    "상향",
    "강화",
    "증가",
    "높",
    "완화",
    "개선",
)
ADJUST_KEYWORDS = ("조정", "변경", "업데이트")


def infer_change_type(text: str) -> str:
    nerf_score = _count_keywords(text, NERF_KEYWORDS)
    buff_score = _count_keywords(text, BUFF_KEYWORDS)
    adjust_score = _count_keywords(text, ADJUST_KEYWORDS)

    if nerf_score > buff_score and nerf_score >= adjust_score:
        return "nerf"
    if buff_score > nerf_score and buff_score >= adjust_score:
        return "buff"
    if adjust_score:
        return "adjust"
    return "adjust"


def _count_keywords(text: str, keywords: tuple[str, ...]) -> int:
    return sum(text.count(keyword) for keyword in keywords)
