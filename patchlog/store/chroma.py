from __future__ import annotations

from pathlib import Path
from typing import Any

from patchlog.chunking.semantic import CHILD_ROLE, PARENT_ROLE, expand_parent_child_chunks
from patchlog.embedding.factory import (
    collection_name_for_backend,
    create_embedding_function,
    normalize_embedding_backend,
)


LEGACY_COLLECTION_NAME = "patch_notes"


class ChromaPatchStore:
    def __init__(
        self,
        *,
        persist_path: Path,
        embedding_backend: str | None = None,
        embedding_function: Any | None = None,
        collection_name: str | None = None,
    ) -> None:
        try:
            import chromadb
        except ImportError as exc:  # pragma: no cover - environment dependent.
            raise RuntimeError(
                "chromadb is required for indexing. Run `python -m pip install -r requirements.txt`."
            ) from exc

        self.embedding_backend = normalize_embedding_backend(embedding_backend)
        self.collection_name = collection_name or collection_name_for_backend(self.embedding_backend)
        self.embedding_function = embedding_function or create_embedding_function(self.embedding_backend)
        self.client = chromadb.PersistentClient(path=str(persist_path))
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
            embedding_function=self.embedding_function,
        )

    def upsert_chunks(self, chunks) -> None:
        if not chunks:
            return
        chunks = expand_parent_child_chunks(list(chunks))
        self.collection.upsert(
            ids=[chunk.chunk_id for chunk in chunks],
            documents=[chunk.document for chunk in chunks],
            metadatas=[chunk.metadata for chunk in chunks],
        )

    def search(
        self,
        *,
        query: str,
        where: dict[str, Any] | None = None,
        top_k: int = 8,
    ) -> list[dict[str, Any]]:
        child_where = {"chunk_role": CHILD_ROLE, **(where or {})}
        result = self.collection.query(
            query_texts=[query],
            n_results=top_k,
            where=_normalize_where(child_where),
            include=["documents", "metadatas", "distances"],
        )
        child_rows: list[dict[str, Any]] = []
        ids = result.get("ids", [[]])[0]
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]
        for chunk_id, document, metadata, distance in zip(ids, documents, metadatas, distances):
            child_rows.append(
                {
                    "chunk_id": chunk_id,
                    "document": document,
                    "metadata": metadata,
                    "distance": distance,
                }
            )
        return self._resolve_parent_rows(child_rows)

    def count(self) -> int:
        return self.collection.count()

    def delete_game(self, *, game: str) -> None:
        self.collection.delete(where={"game": game})

    def list_targets(self, *, game: str) -> list[str]:
        result = self.collection.get(
            where=_normalize_where({"game": game, "chunk_role": PARENT_ROLE}),
            include=["metadatas"],
        )
        targets = {
            metadata.get("target")
            for metadata in result.get("metadatas", [])
            if metadata and metadata.get("target")
        }
        return sorted(targets, key=lambda target: (-len(target), target))

    def list_chunks(self, *, game: str) -> list[dict[str, Any]]:
        result = self.collection.get(
            where=_normalize_where({"game": game, "chunk_role": PARENT_ROLE}),
            include=["documents", "metadatas"],
        )
        rows: list[dict[str, Any]] = []
        for chunk_id, document, metadata in zip(
            result.get("ids", []),
            result.get("documents", []),
            result.get("metadatas", []),
        ):
            rows.append(
                {
                    "chunk_id": chunk_id,
                    "document": document,
                    "metadata": metadata,
                    "distance": None,
                }
            )
        return rows

    def _resolve_parent_rows(self, child_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not child_rows:
            return []

        best_by_parent: dict[str, dict[str, Any]] = {}
        parent_ids: list[str] = []
        for row in child_rows:
            metadata = row["metadata"]
            parent_id = metadata.get("parent_chunk_id") or row["chunk_id"]
            if parent_id not in best_by_parent:
                best_by_parent[parent_id] = row
                parent_ids.append(parent_id)

        parent_result = self.collection.get(ids=parent_ids, include=["documents", "metadatas"])
        parent_by_id = {
            chunk_id: {"document": document, "metadata": metadata}
            for chunk_id, document, metadata in zip(
                parent_result.get("ids", []),
                parent_result.get("documents", []),
                parent_result.get("metadatas", []),
            )
        }

        rows: list[dict[str, Any]] = []
        for parent_id in parent_ids:
            child = best_by_parent[parent_id]
            parent = parent_by_id.get(parent_id)
            if not parent:
                continue
            rows.append(
                {
                    "chunk_id": parent_id,
                    "document": parent["document"],
                    "metadata": parent["metadata"],
                    "distance": child.get("distance"),
                    "matched_child_id": child["chunk_id"],
                    "matched_child_document": child["document"],
                    "matched_child_metadata": child["metadata"],
                }
            )
        return rows


def _normalize_where(where: dict[str, Any] | None) -> dict[str, Any] | None:
    if not where or len(where) <= 1:
        return where
    return {"$and": [{key: value} for key, value in where.items()]}
