from __future__ import annotations

from pathlib import Path
from typing import Any

from patchlog.embedding.hash import HashEmbeddingFunction


COLLECTION_NAME = "patch_notes"


class ChromaPatchStore:
    def __init__(
        self,
        *,
        persist_path: Path,
        embedding_function: HashEmbeddingFunction | None = None,
    ) -> None:
        try:
            import chromadb
        except ImportError as exc:  # pragma: no cover - environment dependent.
            raise RuntimeError(
                "chromadb is required for indexing. Run `python -m pip install -r requirements.txt`."
            ) from exc

        self.embedding_function = embedding_function or HashEmbeddingFunction()
        self.client = chromadb.PersistentClient(path=str(persist_path))
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
            embedding_function=self.embedding_function,
        )

    def upsert_chunks(self, chunks) -> None:
        if not chunks:
            return
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
        result = self.collection.query(
            query_texts=[query],
            n_results=top_k,
            where=_normalize_where(where),
            include=["documents", "metadatas", "distances"],
        )
        rows: list[dict[str, Any]] = []
        ids = result.get("ids", [[]])[0]
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]
        for chunk_id, document, metadata, distance in zip(ids, documents, metadatas, distances):
            rows.append(
                {
                    "chunk_id": chunk_id,
                    "document": document,
                    "metadata": metadata,
                    "distance": distance,
                }
            )
        return rows

    def count(self) -> int:
        return self.collection.count()

    def delete_game(self, *, game: str) -> None:
        self.collection.delete(where={"game": game})

    def list_targets(self, *, game: str) -> list[str]:
        result = self.collection.get(where={"game": game}, include=["metadatas"])
        targets = {
            metadata.get("target")
            for metadata in result.get("metadatas", [])
            if metadata and metadata.get("target")
        }
        return sorted(targets, key=lambda target: (-len(target), target))

    def list_chunks(self, *, game: str) -> list[dict[str, Any]]:
        result = self.collection.get(where={"game": game}, include=["documents", "metadatas"])
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


def _normalize_where(where: dict[str, Any] | None) -> dict[str, Any] | None:
    if not where or len(where) <= 1:
        return where
    return {"$and": [{key: value} for key, value in where.items()]}
