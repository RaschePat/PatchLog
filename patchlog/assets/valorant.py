from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ValorantAgent:
    name: str
    developer_name: str
    icon_url: str
    portrait_url: str


VALORANT_AGENTS: tuple[ValorantAgent, ...] = (
    ValorantAgent("게코", "Aggrobot", "https://media.valorant-api.com/agents/e370fa57-4757-3604-3648-499e1f642d3f/displayicon.png", "https://media.valorant-api.com/agents/e370fa57-4757-3604-3648-499e1f642d3f/fullportrait.png"),
    ValorantAgent("네온", "Sprinter", "https://media.valorant-api.com/agents/bb2a4828-46eb-8cd1-e765-15848195d751/displayicon.png", "https://media.valorant-api.com/agents/bb2a4828-46eb-8cd1-e765-15848195d751/fullportrait.png"),
    ValorantAgent("데드록", "Cable", "https://media.valorant-api.com/agents/cc8b64c8-4b25-4ff9-6e7f-37b4da43d235/displayicon.png", "https://media.valorant-api.com/agents/cc8b64c8-4b25-4ff9-6e7f-37b4da43d235/fullportrait.png"),
    ValorantAgent("레이나", "Vampire", "https://media.valorant-api.com/agents/a3bfb853-43b2-7238-a4f1-ad90e9e46bcc/displayicon.png", "https://media.valorant-api.com/agents/a3bfb853-43b2-7238-a4f1-ad90e9e46bcc/fullportrait.png"),
    ValorantAgent("레이즈", "Clay", "https://media.valorant-api.com/agents/f94c3b30-42be-e959-889c-5aa313dba261/displayicon.png", "https://media.valorant-api.com/agents/f94c3b30-42be-e959-889c-5aa313dba261/fullportrait.png"),
    ValorantAgent("믹스", "Iris", "https://media.valorant-api.com/agents/7c8a4701-4de6-9355-b254-e09bc2a34b72/displayicon.png", "https://media.valorant-api.com/agents/7c8a4701-4de6-9355-b254-e09bc2a34b72/fullportrait.png"),
    ValorantAgent("바이스", "Nox", "https://media.valorant-api.com/agents/efba5359-4016-a1e5-7626-b1ae76895940/displayicon.png", "https://media.valorant-api.com/agents/efba5359-4016-a1e5-7626-b1ae76895940/fullportrait.png"),
    ValorantAgent("바이퍼", "Pandemic", "https://media.valorant-api.com/agents/707eab51-4836-f488-046a-cda6bf494859/displayicon.png", "https://media.valorant-api.com/agents/707eab51-4836-f488-046a-cda6bf494859/fullportrait.png"),
    ValorantAgent("브리치", "Breach", "https://media.valorant-api.com/agents/5f8d3a7f-467b-97f3-062c-13acf203c006/displayicon.png", "https://media.valorant-api.com/agents/5f8d3a7f-467b-97f3-062c-13acf203c006/fullportrait.png"),
    ValorantAgent("브림스톤", "Sarge", "https://media.valorant-api.com/agents/9f0d8ba9-4140-b941-57d3-a7ad57c6b417/displayicon.png", "https://media.valorant-api.com/agents/9f0d8ba9-4140-b941-57d3-a7ad57c6b417/fullportrait.png"),
    ValorantAgent("비토", "Pine", "https://media.valorant-api.com/agents/92eeef5d-43b5-1d4a-8d03-b3927a09034b/displayicon.png", "https://media.valorant-api.com/agents/92eeef5d-43b5-1d4a-8d03-b3927a09034b/fullportrait.png"),
    ValorantAgent("사이퍼", "Gumshoe", "https://media.valorant-api.com/agents/117ed9e3-49f3-6512-3ccf-0cada7e3823b/displayicon.png", "https://media.valorant-api.com/agents/117ed9e3-49f3-6512-3ccf-0cada7e3823b/fullportrait.png"),
    ValorantAgent("세이지", "Thorne", "https://media.valorant-api.com/agents/569fdd95-4d10-43ab-ca70-79becc718b46/displayicon.png", "https://media.valorant-api.com/agents/569fdd95-4d10-43ab-ca70-79becc718b46/fullportrait.png"),
    ValorantAgent("소바", "Hunter", "https://media.valorant-api.com/agents/320b2a48-4d9b-a075-30f1-1f93a9b638fa/displayicon.png", "https://media.valorant-api.com/agents/320b2a48-4d9b-a075-30f1-1f93a9b638fa/fullportrait.png"),
    ValorantAgent("스카이", "Guide", "https://media.valorant-api.com/agents/6f2a04ca-43e0-be17-7f36-b3908627744d/displayicon.png", "https://media.valorant-api.com/agents/6f2a04ca-43e0-be17-7f36-b3908627744d/fullportrait.png"),
    ValorantAgent("아스트라", "Rift", "https://media.valorant-api.com/agents/41fb69c1-4189-7b37-f117-bcaf1e96f1bf/displayicon.png", "https://media.valorant-api.com/agents/41fb69c1-4189-7b37-f117-bcaf1e96f1bf/fullportrait.png"),
    ValorantAgent("아이소", "Sequoia", "https://media.valorant-api.com/agents/0e38b510-41a8-5780-5e8f-568b2a4f2d6c/displayicon.png", "https://media.valorant-api.com/agents/0e38b510-41a8-5780-5e8f-568b2a4f2d6c/fullportrait.png"),
    ValorantAgent("오멘", "Wraith", "https://media.valorant-api.com/agents/8e253930-4c05-31dd-1b6c-968525494517/displayicon.png", "https://media.valorant-api.com/agents/8e253930-4c05-31dd-1b6c-968525494517/fullportrait.png"),
    ValorantAgent("요루", "Stealth", "https://media.valorant-api.com/agents/7f94d92c-4234-0a36-9646-3a87eb8b5c89/displayicon.png", "https://media.valorant-api.com/agents/7f94d92c-4234-0a36-9646-3a87eb8b5c89/fullportrait.png"),
    ValorantAgent("웨이레이", "Terra", "https://media.valorant-api.com/agents/df1cb487-4902-002e-5c17-d28e83e78588/displayicon.png", "https://media.valorant-api.com/agents/df1cb487-4902-002e-5c17-d28e83e78588/fullportrait.png"),
    ValorantAgent("제트", "Wushu", "https://media.valorant-api.com/agents/add6443a-41bd-e414-f6ad-e58d267f4e95/displayicon.png", "https://media.valorant-api.com/agents/add6443a-41bd-e414-f6ad-e58d267f4e95/fullportrait.png"),
    ValorantAgent("체임버", "Deadeye", "https://media.valorant-api.com/agents/22697a3d-45bf-8dd7-4fec-84a9e28c69d7/displayicon.png", "https://media.valorant-api.com/agents/22697a3d-45bf-8dd7-4fec-84a9e28c69d7/fullportrait.png"),
    ValorantAgent("케이/오", "Grenadier", "https://media.valorant-api.com/agents/601dbbe7-43ce-be57-2a40-4abd24953621/displayicon.png", "https://media.valorant-api.com/agents/601dbbe7-43ce-be57-2a40-4abd24953621/fullportrait.png"),
    ValorantAgent("클로브", "Smonk", "https://media.valorant-api.com/agents/1dbf2edd-4729-0984-3115-daa5eed44993/displayicon.png", "https://media.valorant-api.com/agents/1dbf2edd-4729-0984-3115-daa5eed44993/fullportrait.png"),
    ValorantAgent("킬조이", "Killjoy", "https://media.valorant-api.com/agents/1e58de9c-4950-5125-93e9-a0aee9f98746/displayicon.png", "https://media.valorant-api.com/agents/1e58de9c-4950-5125-93e9-a0aee9f98746/fullportrait.png"),
    ValorantAgent("테호", "Cashew", "https://media.valorant-api.com/agents/b444168c-4e35-8076-db47-ef9bf368f384/displayicon.png", "https://media.valorant-api.com/agents/b444168c-4e35-8076-db47-ef9bf368f384/fullportrait.png"),
    ValorantAgent("페이드", "BountyHunter", "https://media.valorant-api.com/agents/dade69b4-4f5a-8528-247b-219e5a1facd6/displayicon.png", "https://media.valorant-api.com/agents/dade69b4-4f5a-8528-247b-219e5a1facd6/fullportrait.png"),
    ValorantAgent("피닉스", "Phoenix", "https://media.valorant-api.com/agents/eb93336a-449b-9c1b-0a54-a891f7921d69/displayicon.png", "https://media.valorant-api.com/agents/eb93336a-449b-9c1b-0a54-a891f7921d69/fullportrait.png"),
    ValorantAgent("하버", "Mage", "https://media.valorant-api.com/agents/95b78ed7-4637-86d9-7e41-71ba8c293152/displayicon.png", "https://media.valorant-api.com/agents/95b78ed7-4637-86d9-7e41-71ba8c293152/fullportrait.png"),
)

AGENT_ALIASES = {
    "KAY/O": "케이/오",
    "케이오": "케이/오",
}


def valorant_agent_names() -> tuple[str, ...]:
    return tuple(agent.name for agent in VALORANT_AGENTS)


def valorant_agent_icon(name: str) -> str | None:
    agent = _AGENTS_BY_NAME.get(name)
    return agent.icon_url if agent else None


def valorant_agent_names_in_text(text: str) -> list[str]:
    compact = _compact(text)
    matches: list[tuple[int, str]] = []
    for alias, canonical in AGENT_ALIASES.items():
        index = compact.find(_compact(alias))
        if index >= 0:
            matches.append((index, canonical))
    for name in sorted(_AGENTS_BY_NAME, key=len, reverse=True):
        index = compact.find(_compact(name))
        if index >= 0:
            matches.append((index, name))

    found: list[str] = []
    for _, name in sorted(matches, key=lambda item: item[0]):
        if name not in found:
            found.append(name)
    return found


_AGENTS_BY_NAME = {agent.name: agent for agent in VALORANT_AGENTS}


def _compact(text: str) -> str:
    return "".join(text.split()).lower()
