from __future__ import annotations

import os
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
    embedding_backend: str = os.getenv("PATCHLOG_EMBEDDING_BACKEND", "bge-m3")
    llm_backend: str = os.getenv("PATCHLOG_LLM_BACKEND", "openai")
    llm_model: str = os.getenv("PATCHLOG_LLM_MODEL", "gpt-5.5")


settings = Settings()
