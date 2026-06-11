from __future__ import annotations

import os
from typing import Any

from patchlog.config import GAME_LABELS


class LLMConfigurationError(RuntimeError):
    pass


class OpenAIAnswerGenerator:
    def __init__(
        self,
        *,
        model: str,
        client: Any | None = None,
        api_key: str | None = None,
    ) -> None:
        self.model = model
        self.client = client
        self.api_key = api_key

    def generate(
        self,
        *,
        game: str,
        message: str,
        chunks: list[Any],
        final_filter: dict[str, Any],
    ) -> str:
        client = self._client()
        response = client.responses.create(
            model=self.model,
            input=[
                {"role": "system", "content": _system_prompt()},
                {
                    "role": "user",
                    "content": _user_prompt(
                        game=game,
                        message=message,
                        chunks=chunks,
                        final_filter=final_filter,
                    ),
                },
            ],
        )
        return _response_text(response)

    def _client(self):
        if self.client is not None:
            return self.client
        api_key = self.api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise LLMConfigurationError(
                "OPENAI_API_KEY is required when PATCHLOG_LLM_BACKEND=openai."
            )
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - environment dependent.
            raise RuntimeError(
                "openai is required for LLM generation. "
                "Run `python -m pip install -r requirements.txt`."
            ) from exc
        self.client = OpenAI(api_key=api_key)
        return self.client


def _system_prompt() -> str:
    return (
        "You are PatchLog analyst. Answer in Korean. "
        "Use only the retrieved patch-note context. Do not speculate. "
        "Keep the answer concise. Every factual bullet must include a citation "
        "like [패치 26.12, 2026-06-09]. If the context is insufficient, say that "
        "the collected patch notes do not contain enough evidence."
    )


def _user_prompt(
    *,
    game: str,
    message: str,
    chunks: list[Any],
    final_filter: dict[str, Any],
) -> str:
    context = "\n\n".join(_chunk_context(index, chunk) for index, chunk in enumerate(chunks, start=1))
    return (
        f"Game: {GAME_LABELS.get(game, game)}\n"
        f"Forced metadata filter: {final_filter}\n"
        f"User question: {message}\n\n"
        "Retrieved context:\n"
        f"{context}\n\n"
        "Answer format:\n"
        "- 1-4 short Korean bullets or paragraphs.\n"
        "- Cite each bullet with the patch version/date.\n"
        "- Do not mention unrelated games or targets."
    )


def _chunk_context(index: int, chunk: Any) -> str:
    matched = getattr(chunk, "matched_child_content", None) or chunk.content
    return (
        f"[Context {index}]\n"
        f"chunk_id: {chunk.chunk_id}\n"
        f"game: {chunk.game}\n"
        f"target: {chunk.target}\n"
        f"section: {chunk.section}\n"
        f"change_type: {chunk.change_type}\n"
        f"patch: {chunk.patch_version}, {chunk.patch_date}\n"
        f"source_url: {chunk.source_url}\n"
        f"content:\n{matched}"
    )


def _response_text(response: Any) -> str:
    output_text = getattr(response, "output_text", None)
    if output_text:
        return str(output_text).strip()

    parts: list[str] = []
    for item in getattr(response, "output", []) or []:
        for content in getattr(item, "content", []) or []:
            text = getattr(content, "text", None)
            if text:
                parts.append(str(text))
    if parts:
        return "\n".join(parts).strip()
    return str(response).strip()
