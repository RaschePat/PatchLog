from __future__ import annotations


DDRAGON_VERSION = "16.11.1"


def item_icon(item_id: int) -> str:
    return f"https://ddragon.leagueoflegends.com/cdn/{DDRAGON_VERSION}/img/item/{item_id}.png"


ITEM_IMAGE_URLS = {
    "강철심장": item_icon(3084),
    "강철의 솔라리 펜던트": item_icon(3190),
    "기사의 맹세": item_icon(3109),
    "꿈 생성기": item_icon(3870),
    "리치베인": item_icon(3100),
    "벼락폭풍검": item_icon(6699),
    "스태틱의 단검": item_icon(3087),
    "실험적 마공학판": item_icon(3073),
    "오만": item_icon(6697),
    "월석 재생기": item_icon(6617),
    "원칙의 원형낫": item_icon(6696),
    "제국의 명령": item_icon(4005),
    "지크의 융합": item_icon(3050),
    "태양불꽃 방패": item_icon(3068),
    "헬리아의 메아리": item_icon(6620),
    "화공 펑크 사슬검": item_icon(6609),
    "흐르는 물의 지팡이": item_icon(6616),
    "끝없는 갈망": "https://cmsassets.rgpub.io/sanity/images/dsfx7636/news_live/46965cb79b66b7fd974b053bed2e0efe4ba636db-512x512.png",
    "도란의 투구": "https://cmsassets.rgpub.io/sanity/images/dsfx7636/news_live/bc9f19b522a55901203db94e9c6bf708b3e24a91-512x512.jpg",
    "도란의 활": "https://cmsassets.rgpub.io/sanity/images/dsfx7636/news_live/f4dd1e2c39c1e953c0483e15c18a7ed22d0e9945-512x512.jpg",
    "무장 진격": "https://cmsassets.rgpub.io/sanity/images/dsfx7636/news_live/18bb2d092845859af6a234f6df369d2b965ed025-512x512.png",
    "사슬끈 분쇄자": "https://cmsassets.rgpub.io/sanity/images/dsfx7636/news_live/baec396740d4bc550d0069638d7fc35a01bd598e-512x512.png",
    "원형질 안전벨트": "https://cmsassets.rgpub.io/sanity/images/dsfx7636/news_live/49e21ed423d5290d2a7c0e6db3450d64e63000e9-512x512.png",
    "탐욕의 군화 / 불멸의 길": "https://cmsassets.rgpub.io/sanity/images/dsfx7636/news_live/9b1ba3fbc73a4aadea8c057f78f00fa82d3820ba-512x512.png",
}

RUNE_IMAGE_URLS = {
    "난입": "https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Sorcery/PhaseRush/PhaseRush.png",
    "삼중 물약": "https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Inspiration/TripleTonic/TripleTonic.png",
    "수호자": "https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Resolve/Guardian/Guardian.png",
    "신비로운 유성": "https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Sorcery/ArcaneComet/ArcaneComet.png",
    "여진": "https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Resolve/VeteranAftershock/VeteranAftershock.png",
    "죽음불꽃 손길": "https://cmsassets.rgpub.io/sanity/images/dsfx7636/news_live/19235c247a219ac4e7ccec749b88155ce19ad7d6-512x512.png",
    "칼날비": "https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Domination/HailOfBlades/HailOfBlades.png",
    "콩콩이 소환": "https://ddragon.leagueoflegends.com/cdn/img/perk-images/Styles/Sorcery/SummonAery/SummonAery.png",
    "폭풍전사의 포효": "https://cmsassets.rgpub.io/sanity/images/dsfx7636/news_live/5ae14cecdba29981b15f30e5970c4a8c646140a3-512x512.png",
    "환급": "https://cmsassets.rgpub.io/sanity/images/dsfx7636/news_live/5028a1fda4fa005a7255fd18440616255dd08447-512x512.png",
}

SYSTEM_IMAGE_URLS = {
    "순간이동": f"https://ddragon.leagueoflegends.com/cdn/{DDRAGON_VERSION}/img/spell/SummonerTeleport.png",
    "황혼과 새벽": "https://cmsassets.rgpub.io/sanity/images/dsfx7636/news_live/1c0b545b1455a9cf6bb429747d38039b3541020c-512x512.png",
}


def lol_entity_image(target: str, section: str) -> str | None:
    table = {
        "item": ITEM_IMAGE_URLS,
        "rune": RUNE_IMAGE_URLS,
        "system": SYSTEM_IMAGE_URLS,
    }.get(section)
    if not table:
        return None
    return table.get(target)


def lol_entity_catalog(target: str) -> tuple[str, str] | None:
    for section, table in (
        ("item", ITEM_IMAGE_URLS),
        ("rune", RUNE_IMAGE_URLS),
        ("system", SYSTEM_IMAGE_URLS),
    ):
        url = table.get(target)
        if url:
            return section, url
    return None
