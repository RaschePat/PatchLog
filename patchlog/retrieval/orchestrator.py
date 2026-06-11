from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from patchlog.config import GAME_LABELS, VALID_GAMES, settings
from patchlog.dashboard import build_patch_dashboard, summarize_document
from patchlog.generation.openai import LLMConfigurationError, OpenAIAnswerGenerator
from patchlog.models import ChatMessage, ChatResult, Game, PatchChunk
from patchlog.retrieval.self_query import analyze_query, has_unknown_explicit_target, is_patch_followup
from patchlog.store.chroma import ChromaPatchStore
from patchlog.store.in_memory import InMemoryPatchStore


@dataclass(frozen=True)
class RetrievedPatchChunk:
    chunk_id: str
    game: str
    patch_version: str
    patch_date: str
    target: str
    change_type: str
    source_url: str
    content: str
    section: str = "champion"
    distance: float | None = None
    parent_chunk_id: str | None = None
    matched_child_id: str | None = None
    matched_child_content: str | None = None

    def source_dict(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "game": self.game,
            "patch_version": self.patch_version,
            "patch_date": self.patch_date,
            "target": self.target,
            "change_type": self.change_type,
            "source_url": self.source_url,
            "section": self.section,
            "distance": self.distance,
            "content": self.content,
            "parent_chunk_id": self.parent_chunk_id,
            "matched_child_id": self.matched_child_id,
        }


class ChatOrchestrator:
    def __init__(
        self,
        store: InMemoryPatchStore | ChromaPatchStore | None = None,
        *,
        llm_backend: str | None = None,
        answer_generator: OpenAIAnswerGenerator | None = None,
    ) -> None:
        self.store = store or InMemoryPatchStore()
        self.llm_backend = (llm_backend or settings.llm_backend).strip().lower()
        self.answer_generator = answer_generator or OpenAIAnswerGenerator(model=settings.llm_model)

    def chat(
        self,
        *,
        game: Game,
        message: str,
        chat_history: list[ChatMessage] | None = None,
        top_k: int = 8,
        debug: bool = False,
    ) -> ChatResult:
        if game not in VALID_GAMES:
            raise ValueError(f"Unsupported game: {game}")

        history = chat_history or []
        known_targets = _known_targets(self.store, game)
        analysis = analyze_query(message, game, history, known_targets=known_targets)
        if has_unknown_explicit_target(message, game, known_targets=known_targets):
            debug_trace = _debug_trace(self, analysis.query, {"game": game}, [], debug)
            return ChatResult(
                answer=f"수집된 {GAME_LABELS[game]} 패치노트에서 해당 대상을 찾지 못했습니다.",
                sources=[],
                navigation_target=None,
                debug_trace=debug_trace,
            )
        if not analysis.filter and not _is_latest_patch_intent(message) and not _is_patch_domain_query(
            message,
            known_targets=known_targets,
        ):
            debug_trace = _debug_trace(self, analysis.query, {"game": game}, [], debug)
            return ChatResult(
                answer=_off_topic_answer(game),
                sources=[],
                navigation_target=None,
                debug_trace=debug_trace,
            )
        if _is_latest_patch_intent(message) and "target" not in analysis.filter:
            latest_result = self._latest_patch_chat(game=game, debug=debug)
            if latest_result is not None:
                return latest_result

        final_filter: dict[str, Any] = {"game": game, **analysis.filter}
        chunks = _search_store(self.store, analysis.query, final_filter, top_k)
        chunks = _rank_chunks(chunks, final_filter)
        chunks = chunks[:3]

        if not chunks:
            debug_trace = _debug_trace(self, analysis.query, final_filter, [], debug)
            return ChatResult(
                answer=f"수집된 {GAME_LABELS[game]} 패치노트에서 찾지 못했습니다.",
                sources=[],
                navigation_target=None,
                debug_trace=debug_trace,
            )

        sources = [chunk.source_dict() for chunk in chunks]
        try:
            answer = self._generate_answer(
                game=game,
                message=message,
                chunks=chunks,
                final_filter=final_filter,
            )
            generation = f"{self.llm_backend}_answer_from_retrieved_chunks"
        except LLMConfigurationError as exc:
            answer = str(exc)
            generation = "llm_configuration_error"
        navigation_target = _navigation_target(chunks[0])
        debug_trace = _debug_trace(self, analysis.query, final_filter, sources, debug, generation=generation)
        return ChatResult(
            answer=answer,
            sources=sources,
            navigation_target=navigation_target,
            debug_trace=debug_trace,
        )

    def search(
        self,
        *,
        game: Game,
        query: str,
        target: str | None = None,
        change_type: str | None = None,
        section: str | None = None,
        patch_version: str | None = None,
        top_k: int = 8,
    ) -> list[dict[str, Any]]:
        if game not in VALID_GAMES:
            raise ValueError(f"Unsupported game: {game}")

        final_filter: dict[str, Any] = {"game": game}
        if target:
            final_filter["target"] = target
        if change_type:
            final_filter["change_type"] = change_type
        if section:
            final_filter["section"] = section
        if patch_version:
            final_filter["patch_version"] = patch_version
        chunks = _search_store(self.store, query, final_filter, top_k)
        return [chunk.source_dict() for chunk in chunks]

    def patches(self, *, game: Game) -> list[dict[str, Any]]:
        if game not in VALID_GAMES:
            raise ValueError(f"Unsupported game: {game}")
        if isinstance(self.store, ChromaPatchStore):
            return build_patch_dashboard(self.store.list_chunks(game=game))
        return []

    def _generate_answer(
        self,
        *,
        game: Game,
        message: str,
        chunks: list[RetrievedPatchChunk],
        final_filter: dict[str, Any],
    ) -> str:
        if self.llm_backend == "template":
            return _build_answer(chunks, final_filter)
        if self.llm_backend != "openai":
            raise ValueError("Unsupported LLM backend. Use 'openai' or 'template'.")
        return self.answer_generator.generate(
            game=game,
            message=message,
            chunks=chunks,
            final_filter=final_filter,
        )

    def _latest_patch_chat(self, *, game: Game, debug: bool) -> ChatResult | None:
        patches = self.patches(game=game)
        if not patches:
            return None
        latest = patches[0]
        changes = latest["changes"][:1]
        sources = [
            {
                **change,
                "content": change["summary"],
                "distance": None,
            }
            for change in changes
        ]
        navigation_target = None
        if sources:
            first = sources[0]
            navigation_target = {
                "game": first["game"],
                "patch_version": first["patch_version"],
                "patch_date": first["patch_date"],
                "target": first["target"],
                "chunk_id": first["chunk_id"],
                "source_url": first["source_url"],
            }
        debug_trace = None
        if debug:
            debug_trace = {
                "query": "latest_patch",
                "final_filter": {"game": game, "patch_version": latest["patch_version"]},
                "retrieved_chunks": sources,
                "retrieved_child_ids": [],
                "resolved_parent_ids": [source.get("chunk_id") for source in sources if source.get("chunk_id")],
                "embedding_backend": getattr(self.store, "embedding_backend", "in_memory"),
                "llm_backend": self.llm_backend,
                "generation": "latest_patch_dashboard_summary",
            }
        return ChatResult(
            answer=_build_latest_patch_answer(latest),
            sources=sources,
            navigation_target=navigation_target,
            debug_trace=debug_trace,
        )


def create_api_orchestrator(root: Path | None = None) -> ChatOrchestrator:
    root = root or Path.cwd()
    chroma_path = root / "data" / "chroma"
    if (chroma_path / "chroma.sqlite3").exists():
        store = ChromaPatchStore(persist_path=chroma_path, embedding_backend=settings.embedding_backend)
        if store.count() > 0:
            return ChatOrchestrator(store=store)
    return ChatOrchestrator()


def _search_store(
    store: InMemoryPatchStore | ChromaPatchStore,
    query: str,
    final_filter: dict[str, Any],
    top_k: int,
) -> list[RetrievedPatchChunk]:
    if isinstance(store, ChromaPatchStore):
        rows = store.search(query=query, where=final_filter, top_k=top_k)
        return [_from_chroma_row(row) for row in rows]

    chunks = store.search(query, final_filter, top_k)
    return [_from_patch_chunk(chunk) for chunk in chunks]


def _rank_chunks(chunks: list[RetrievedPatchChunk], final_filter: dict[str, Any]) -> list[RetrievedPatchChunk]:
    if final_filter.get("target"):
        return sorted(
            chunks,
            key=lambda chunk: (chunk.patch_date, _version_sort_key(chunk.patch_version), -(chunk.distance or 0.0)),
            reverse=True,
        )
    return chunks


def _version_sort_key(version: str) -> tuple[int, ...]:
    import re

    return tuple(int(part) for part in re.findall(r"\d+", version))


def _from_chroma_row(row: dict[str, Any]) -> RetrievedPatchChunk:
    metadata = row["metadata"]
    return RetrievedPatchChunk(
        chunk_id=row["chunk_id"],
        game=metadata["game"],
        patch_version=metadata["patch_version"],
        patch_date=metadata["patch_date"],
        target=metadata["target"],
        change_type=metadata["change_type"],
        source_url=metadata["source_url"],
        content=row["document"],
        section=metadata.get("section", "champion"),
        distance=row.get("distance"),
        parent_chunk_id=metadata.get("parent_chunk_id"),
        matched_child_id=row.get("matched_child_id"),
        matched_child_content=row.get("matched_child_document"),
    )


def _from_patch_chunk(chunk: PatchChunk) -> RetrievedPatchChunk:
    return RetrievedPatchChunk(
        chunk_id=chunk.chunk_id,
        game=chunk.game,
        patch_version=chunk.patch_version,
        patch_date=chunk.patch_date,
        target=chunk.target,
        change_type=chunk.change_type,
        source_url=chunk.source_url,
        content=chunk.content,
        section=chunk.section,
    )


def _known_targets(
    store: InMemoryPatchStore | ChromaPatchStore,
    game: Game,
) -> list[str] | None:
    if isinstance(store, ChromaPatchStore):
        return store.list_targets(game=game)
    return None


def _build_answer(chunks: list[RetrievedPatchChunk], final_filter: dict[str, Any]) -> str:
    targets = {chunk.target for chunk in chunks}
    change_label = _change_type_label(final_filter.get("change_type"))
    if len(targets) == 1 and final_filter.get("target"):
        return _build_single_target_answer(chunks, change_label, final_filter)
    return _build_list_answer(chunks, change_label, final_filter)


def _build_latest_patch_answer(patch: dict[str, Any]) -> str:
    lines = [
        f"가장 최신 패치는 {patch['title']}입니다. [패치 {patch['patch_version']}, {patch['patch_date']}]",
    ]
    changes = patch.get("changes", [])[:3]
    if changes:
        lines.extend(["", "핵심 변경:"])
        for change in changes:
            summary = _compact_inline_summary(str(change.get("summary", "")), limit=120)
            lines.append(f"- {change.get('target', '변경')}: {summary}")
    return "\n".join(lines)


def _build_single_target_answer(
    chunks: list[RetrievedPatchChunk],
    change_label: str,
    final_filter: dict[str, Any],
) -> str:
    latest = chunks[0]
    marker = _subject_marker(latest.target)
    scope = _scope_phrase(final_filter)
    lines = [
        f"{latest.target}{marker} {scope or f'{latest.patch_version} 패치'}에서 {change_label} 내용이 확인됩니다.",
        "",
        "핵심 변경:",
    ]
    for detail in _summary_lines(latest, max_lines=3):
        lines.append(_bullet_line(detail))
    lines.extend(["", f"출처: [패치 {latest.patch_version}, {latest.patch_date}]"])

    if len(chunks) > 1:
        lines.extend(["", "관련 이전 변경:"])
        for chunk in chunks[1:3]:
            lines.append(
                f"- {chunk.patch_version}: {_inline_summary(chunk)} "
                f"[패치 {chunk.patch_version}, {chunk.patch_date}]"
            )
    return "\n".join(lines)


def _bullet_line(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("•"):
        return stripped
    return f"- {stripped}"


def _build_list_answer(
    chunks: list[RetrievedPatchChunk],
    change_label: str,
    final_filter: dict[str, Any],
) -> str:
    scope = _scope_phrase(final_filter)
    lines = [_list_intro(scope, change_label, final_filter), ""]
    for chunk in chunks:
        lines.append(
            f"- {chunk.target}: {_inline_summary(chunk)} "
            f"[패치 {chunk.patch_version}, {chunk.patch_date}]"
        )
    return "\n".join(lines)


def _list_intro(scope: str, change_label: str, final_filter: dict[str, Any]) -> str:
    prefix = f"{scope}에서 " if scope else ""
    if final_filter.get("change_type"):
        return f"{prefix}{change_label} 변경으로 확인된 항목은 다음과 같습니다."
    return f"{prefix}확인된 변경 항목은 다음과 같습니다."


def _navigation_target(chunk: RetrievedPatchChunk) -> dict[str, Any]:
    return {
        "game": chunk.game,
        "patch_version": chunk.patch_version,
        "patch_date": chunk.patch_date,
        "target": chunk.target,
        "chunk_id": chunk.chunk_id,
        "source_url": chunk.source_url,
    }


def _preview_content(content: str, target: str, limit: int = 220) -> str:
    import re

    focused = summarize_document(content, target, limit=limit)
    if focused:
        return focused

    text = " ".join(content.split())
    text = re.sub(r"^\[[^\]]+\]\s+패치\s+.+?\s+-\s+", "", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = text.replace(f"### [{target}]", target)
    text = text.replace(f"### {target}", target)
    text = text.replace("####", "")
    text = text.replace("###", "")
    text = text.replace("---", " ")
    text = text.replace("**", "")
    text = text.replace("> ", "")
    text = re.sub(r"\s+", " ", text).strip(" -")
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."


def _summary_lines(chunk: RetrievedPatchChunk, *, max_lines: int) -> list[str]:
    preview = _preview_content(chunk.content, chunk.target, limit=260)
    lines = [line.strip(" -") for line in preview.splitlines() if line.strip(" -")]
    return lines[:max_lines] or [preview]


def _inline_summary(chunk: RetrievedPatchChunk) -> str:
    lines = _summary_lines(chunk, max_lines=2)
    return _compact_inline_summary(" / ".join(lines), limit=150)


def _compact_inline_summary(text: str, *, limit: int) -> str:
    text = text.replace("• ", "")
    text = " / ".join(part.strip() for part in text.splitlines() if part.strip())
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."


def _change_type_label(change_type: str | None) -> str:
    return {
        "nerf": "하향",
        "buff": "상향",
        "adjust": "조정",
        "bugfix": "수정",
        "rework": "개편",
        "new": "신규 변경",
    }.get(change_type or "", "변경")


def _section_label(section: str | None) -> str | None:
    return {
        "champion": "챔피언",
        "agent": "요원",
        "hero": "영웅",
        "item": "아이템",
        "weapon": "무기",
        "rune": "룬",
        "map": "맵",
        "system": "시스템",
    }.get(section or "")


def _domain_examples(game: Game) -> str:
    return {
        "lol": "챔피언, 아이템, 룬 변경사항",
        "valorant": "요원, 무기, 맵 변경사항",
        "overwatch": "영웅, 전장, 시스템 변경사항",
    }.get(game, "변경사항")


def _off_topic_answer(game: Game) -> str:
    return (
        f"{GAME_LABELS[game]} 패치노트와 관련된 질문만 답변할 수 있습니다. "
        f"{_domain_examples(game)}이나 특정 패치 버전을 물어봐 주세요."
    )


def _scope_phrase(final_filter: dict[str, Any]) -> str:
    parts: list[str] = []
    if final_filter.get("patch_version"):
        parts.append(f"{final_filter['patch_version']} 패치")
    section_label = _section_label(final_filter.get("section"))
    if section_label:
        parts.append(section_label)
    return " ".join(parts)


def _subject_marker(text: str) -> str:
    last = text.strip()[-1:]
    if not last:
        return "는"
    code = ord(last)
    if 0xAC00 <= code <= 0xD7A3 and (code - 0xAC00) % 28:
        return "은"
    return "는"


def _debug_trace(
    orchestrator: ChatOrchestrator,
    query: str,
    final_filter: dict[str, Any],
    sources: list[dict[str, Any]],
    debug: bool,
    *,
    generation: str = "template_answer_from_retrieved_chunks",
) -> dict[str, Any] | None:
    if not debug:
        return None
    embedding_backend = getattr(orchestrator.store, "embedding_backend", "in_memory")
    return {
        "query": query,
        "final_filter": final_filter,
        "retrieved_chunks": sources,
        "retrieved_child_ids": [source.get("matched_child_id") for source in sources if source.get("matched_child_id")],
        "resolved_parent_ids": [source.get("chunk_id") for source in sources if source.get("chunk_id")],
        "embedding_backend": embedding_backend,
        "llm_backend": orchestrator.llm_backend,
        "generation": generation,
    }


def _is_latest_patch_intent(message: str) -> bool:
    compact = "".join(message.split())
    return any(
        keyword in compact
        for keyword in ("가장최신", "최신패치", "최신의패치", "이번패치", "최근패치노트")
    )


def _is_patch_domain_query(message: str, *, known_targets: list[str] | None = None) -> bool:
    compact_message = "".join(message.split()).lower()
    if is_patch_followup(message):
        return True
    return any("".join(target.split()).lower() in compact_message for target in known_targets or [])
