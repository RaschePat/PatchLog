from __future__ import annotations

from dataclasses import dataclass


VALID_GAMES = ("lol", "valorant", "overwatch")
GAME_LABELS = {
    "lol": "LoL",
    "valorant": "발로란트",
    "overwatch": "오버워치",
}


@dataclass(frozen=True)
class Settings:
    retrieval_top_k: int = 8
    crawl_delay_sec: float = 2.0


settings = Settings()
