from __future__ import annotations

from typing import Literal

from fastapi import FastAPI
from fastapi import Query
from pydantic import BaseModel, Field

from patchlog.config import settings
from patchlog.models import ChatMessage
from patchlog.retrieval.orchestrator import create_api_orchestrator


GameName = Literal["lol", "valorant", "overwatch"]


class ChatHistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    game: GameName
    message: str = Field(min_length=1)
    chat_history: list[ChatHistoryMessage] = Field(default_factory=list)
    top_k: int = settings.retrieval_top_k
    debug: bool = False


class SearchRequest(BaseModel):
    game: GameName
    query: str = Field(min_length=1)
    target: str | None = None
    change_type: Literal["buff", "nerf", "rework", "adjust", "bugfix", "new"] | None = None
    section: Literal["champion", "agent", "hero", "item", "weapon", "rune", "map", "system"] | None = None
    patch_version: str | None = None
    top_k: int = settings.retrieval_top_k


app = FastAPI(title="PATCHLOG API")
orchestrator = create_api_orchestrator()


@app.get("/")
def root() -> dict[str, object]:
    return {
        "name": "PATCHLOG API",
        "health": "/health",
        "chat": "/chat",
        "search": "/search",
        "patches": "/patches?game=lol",
        "docs": "/docs",
    }


@app.post("/chat")
def chat(request: ChatRequest) -> dict:
    history = [
        ChatMessage(role=message.role, content=message.content)
        for message in request.chat_history
    ]
    result = orchestrator.chat(
        game=request.game,
        message=request.message,
        chat_history=history,
        top_k=request.top_k,
        debug=request.debug,
    )
    return {
        "answer": result.answer,
        "sources": result.sources,
        "navigation_target": result.navigation_target,
        "debug_trace": result.debug_trace,
    }


@app.post("/search")
def search(request: SearchRequest) -> dict:
    sources = orchestrator.search(
        game=request.game,
        query=request.query,
        target=request.target,
        change_type=request.change_type,
        section=request.section,
        patch_version=request.patch_version,
        top_k=request.top_k,
    )
    return {"sources": sources}


@app.get("/patches")
def patches(game: GameName = Query(default="lol")) -> dict:
    return {"patches": orchestrator.patches(game=game)}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
