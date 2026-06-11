from __future__ import annotations

import re
from types import SimpleNamespace
from typing import Any


PARENT_ROLE = "parent"
CHILD_ROLE = "child"
DEFAULT_MAX_CHARS = 800
DEFAULT_OVERLAP_CHARS = 150


def expand_parent_child_chunks(chunks: list[Any]) -> list[Any]:
    expanded: list[Any] = []
    for chunk in chunks:
        parent = _parent_chunk(chunk)
        expanded.append(parent)
        expanded.extend(_child_chunks(parent))
    return expanded


def _parent_chunk(chunk: Any) -> Any:
    metadata = dict(chunk.metadata)
    metadata.setdefault("chunk_role", PARENT_ROLE)
    metadata.setdefault("parent_chunk_id", chunk.chunk_id)
    return SimpleNamespace(
        chunk_id=chunk.chunk_id,
        document=chunk.document,
        metadata=metadata,
    )


def _child_chunks(parent: Any) -> list[Any]:
    child_texts = semantic_child_texts(parent.document)
    children: list[Any] = []
    for index, text in enumerate(child_texts):
        metadata = dict(parent.metadata)
        metadata["chunk_role"] = CHILD_ROLE
        metadata["parent_chunk_id"] = parent.chunk_id
        metadata["child_index"] = index
        children.append(
            SimpleNamespace(
                chunk_id=f"{parent.chunk_id}::child-{index}",
                document=text,
                metadata=metadata,
            )
        )
    return children


def semantic_child_texts(
    document: str,
    *,
    max_chars: int = DEFAULT_MAX_CHARS,
    overlap_chars: int = DEFAULT_OVERLAP_CHARS,
) -> list[str]:
    header = _document_header(document)
    segments = _logical_segments(document)
    if not segments:
        return [document.strip()]

    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for segment in segments:
        if len(segment) > max_chars:
            if current:
                chunks.append(_with_header(header, "\n".join(current)))
                current = []
                current_len = 0
            chunks.extend(_sliding_windows(segment, header=header, max_chars=max_chars, overlap_chars=overlap_chars))
            continue

        projected = current_len + len(segment) + (2 if current else 0)
        if current and projected > max_chars:
            chunks.append(_with_header(header, "\n".join(current)))
            current = [segment]
            current_len = len(segment)
        else:
            current.append(segment)
            current_len = projected

    if current:
        chunks.append(_with_header(header, "\n".join(current)))
    return [chunk for chunk in chunks if chunk.strip()]


def _logical_segments(document: str) -> list[str]:
    lines = [line.rstrip() for line in document.splitlines()]
    segments: list[str] = []
    current: list[str] = []

    def flush() -> None:
        nonlocal current
        text = "\n".join(current).strip()
        if text and not _is_internal_prefix(text):
            segments.append(text)
        current = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            flush()
            continue
        if _starts_new_segment(stripped) and current:
            flush()
        current.append(line)
    flush()
    return segments


def _starts_new_segment(line: str) -> bool:
    if line.startswith(("- ", "* ", "### ", "#### ")):
        return True
    if re.match(r"^[A-Z][0-9]?\s+-\s+", line):
        return True
    return len(line) <= 40 and not line.endswith(".") and not line.startswith("[")


def _sliding_windows(segment: str, *, header: str, max_chars: int, overlap_chars: int) -> list[str]:
    windows: list[str] = []
    start = 0
    while start < len(segment):
        end = min(len(segment), start + max_chars)
        windows.append(_with_header(header, segment[start:end].strip()))
        if end == len(segment):
            break
        start = max(0, end - overlap_chars)
    return windows


def _document_header(document: str) -> str:
    first = document.splitlines()[0].strip() if document.splitlines() else ""
    return first if first.startswith("[") else ""


def _with_header(header: str, body: str) -> str:
    body = body.strip()
    if header and header not in body:
        return f"{header}\n\n{body}"
    return body


def _is_internal_prefix(text: str) -> bool:
    return text.startswith("[") and "\n" not in text
