from __future__ import annotations

from patchlog.models import PatchChunk


SAMPLE_CHUNKS: list[PatchChunk] = [
    PatchChunk(
        chunk_id="lol-14.23-ashe-0",
        game="lol",
        patch_version="14.23",
        patch_date="2025-11-20",
        target="애쉬",
        change_type="nerf",
        source_url="https://example.com/lol/14-23",
        content="애쉬의 W 스킬 재사용 대기시간이 증가했고 초반 견제력이 낮아졌습니다.",
    ),
    PatchChunk(
        chunk_id="lol-14.20-ashe-0",
        game="lol",
        patch_version="14.20",
        patch_date="2025-10-09",
        target="애쉬",
        change_type="buff",
        source_url="https://example.com/lol/14-20",
        content="애쉬의 기본 공격 속도 성장치가 증가했습니다.",
    ),
    PatchChunk(
        chunk_id="overwatch-2025-05-ash-0",
        game="overwatch",
        patch_version="2025.05.21",
        patch_date="2025-05-21",
        target="애쉬",
        change_type="adjust",
        source_url="https://example.com/overwatch/2025-05-21",
        content="애쉬의 다이너마이트 폭발 피해가 조정되고 밥의 지속 시간이 변경되었습니다.",
    ),
    PatchChunk(
        chunk_id="overwatch-2025-02-genji-0",
        game="overwatch",
        patch_version="2025.02.14",
        patch_date="2025-02-14",
        target="겐지",
        change_type="buff",
        source_url="https://example.com/overwatch/2025-02-14",
        content="겐지의 질풍참 재사용 대기시간 반환 조건이 완화되었습니다.",
    ),
    PatchChunk(
        chunk_id="valorant-10-02-jett-0",
        game="valorant",
        patch_version="10.02",
        patch_date="2025-02-05",
        target="제트",
        change_type="nerf",
        source_url="https://example.com/valorant/10-02",
        content="제트의 순풍 사용 가능 시간이 감소했습니다.",
    ),
]

