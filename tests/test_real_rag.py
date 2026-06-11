from __future__ import annotations

from types import SimpleNamespace

import pytest

from patchlog.chunking.semantic import CHILD_ROLE, PARENT_ROLE, expand_parent_child_chunks
from patchlog.embedding.bge_m3 import BGEM3EmbeddingFunction
from patchlog.embedding.hash import HashEmbeddingFunction
from patchlog.generation.openai import OpenAIAnswerGenerator


def test_bge_m3_embedding_wrapper_uses_dense_vectors_from_model() -> None:
    class FakeModel:
        def encode(self, texts, **kwargs):
            assert texts == ["alpha", "beta"]
            assert kwargs["return_dense"] is True
            return {"dense_vecs": [[1] * 1024, [0.5] * 1024]}

    embedder = BGEM3EmbeddingFunction(model=FakeModel())

    vectors = embedder.embed_texts(["alpha", "beta"])

    assert len(vectors) == 2
    assert len(vectors[0]) == 1024
    assert vectors[0][0] == 1.0


def test_parent_child_expansion_keeps_parent_and_adds_semantic_children() -> None:
    parent = SimpleNamespace(
        chunk_id="lol-26.12-aatrox-0",
        document=(
            "[lol] patch 26.12 - Aatrox\n\n"
            "### Aatrox\n\n"
            "Developer context paragraph.\n\n"
            "#### Q - The Darkin Blade\n\n"
            "- Damage: 70 => 75\n\n"
            "#### E - Umbral Dash\n\n"
            "- Cooldown: 10 => 9"
        ),
        metadata={
            "game": "lol",
            "patch_version": "26.12",
            "patch_date": "2026-06-09",
            "section": "champion",
            "target": "Aatrox",
            "change_type": "buff",
            "source_url": "https://example.com",
            "title": "Patch 26.12",
        },
    )

    chunks = expand_parent_child_chunks([parent])

    assert chunks[0].metadata["chunk_role"] == PARENT_ROLE
    assert chunks[0].metadata["parent_chunk_id"] == parent.chunk_id
    child_chunks = [chunk for chunk in chunks if chunk.metadata["chunk_role"] == CHILD_ROLE]
    assert child_chunks
    assert {chunk.metadata["parent_chunk_id"] for chunk in child_chunks} == {parent.chunk_id}
    assert all("Aatrox" in chunk.document or "patch 26.12" in chunk.document for chunk in child_chunks)


def test_chroma_store_uses_backend_specific_collection_names(tmp_path) -> None:
    pytest.importorskip("chromadb")
    from patchlog.store.chroma import ChromaPatchStore

    hash_store = ChromaPatchStore(
        persist_path=tmp_path / "chroma",
        embedding_backend="hash",
        embedding_function=HashEmbeddingFunction(dimensions=32),
    )
    bge_store = ChromaPatchStore(
        persist_path=tmp_path / "chroma",
        embedding_backend="bge-m3",
        embedding_function=HashEmbeddingFunction(dimensions=32),
    )

    assert hash_store.collection_name == "patch_notes_hash"
    assert bge_store.collection_name == "patch_notes_bge_m3"


def test_chroma_search_resolves_child_hits_to_parent_rows(tmp_path) -> None:
    pytest.importorskip("chromadb")
    from patchlog.store.chroma import ChromaPatchStore

    store = ChromaPatchStore(
        persist_path=tmp_path / "chroma",
        embedding_backend="hash",
        embedding_function=HashEmbeddingFunction(dimensions=64),
    )
    store.upsert_chunks(
        [
            SimpleNamespace(
                chunk_id="lol-26.12-aatrox-0",
                document="[lol] patch 26.12 - Aatrox\n\n### Aatrox\n\n- Blade damage increased.",
                metadata={
                    "game": "lol",
                    "patch_version": "26.12",
                    "patch_date": "2026-06-09",
                    "section": "champion",
                    "target": "Aatrox",
                    "change_type": "buff",
                    "source_url": "https://example.com",
                    "title": "Patch 26.12",
                },
            )
        ]
    )

    rows = store.search(query="blade damage", where={"game": "lol", "target": "Aatrox"}, top_k=3)

    assert rows
    assert rows[0]["chunk_id"] == "lol-26.12-aatrox-0"
    assert rows[0]["metadata"]["chunk_role"] == PARENT_ROLE
    assert rows[0]["matched_child_id"].startswith("lol-26.12-aatrox-0::child-")
    assert "Blade damage" in rows[0]["matched_child_document"]


def test_chat_uses_openai_generator_when_configured(tmp_path) -> None:
    pytest.importorskip("chromadb")
    from patchlog.retrieval.orchestrator import ChatOrchestrator
    from patchlog.store.chroma import ChromaPatchStore

    class FakeResponses:
        def create(self, **kwargs):
            assert kwargs["model"] == "test-model"
            assert "Aatrox" in kwargs["input"][1]["content"]
            return SimpleNamespace(output_text="Aatrox answer [패치 26.12, 2026-06-09]")

    fake_client = SimpleNamespace(responses=FakeResponses())
    store = ChromaPatchStore(
        persist_path=tmp_path / "chroma",
        embedding_backend="hash",
        embedding_function=HashEmbeddingFunction(dimensions=64),
    )
    store.upsert_chunks(
        [
            SimpleNamespace(
                chunk_id="lol-26.12-aatrox-0",
                document="[lol] patch 26.12 - Aatrox\n\n### Aatrox\n\n- Blade damage increased.",
                metadata={
                    "game": "lol",
                    "patch_version": "26.12",
                    "patch_date": "2026-06-09",
                    "section": "champion",
                    "target": "Aatrox",
                    "change_type": "buff",
                    "source_url": "https://example.com",
                    "title": "Patch 26.12",
                },
            )
        ]
    )

    result = ChatOrchestrator(
        store=store,
        llm_backend="openai",
        answer_generator=OpenAIAnswerGenerator(model="test-model", client=fake_client),
    ).chat(game="lol", message="Aatrox changes", debug=True)

    assert result.answer == "Aatrox answer [패치 26.12, 2026-06-09]"
    assert result.debug_trace is not None
    assert result.debug_trace["llm_backend"] == "openai"
    assert result.debug_trace["generation"] == "openai_answer_from_retrieved_chunks"


def test_openai_backend_reports_missing_api_key(tmp_path, monkeypatch) -> None:
    pytest.importorskip("chromadb")
    from patchlog.retrieval.orchestrator import ChatOrchestrator
    from patchlog.store.chroma import ChromaPatchStore

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    store = ChromaPatchStore(
        persist_path=tmp_path / "chroma",
        embedding_backend="hash",
        embedding_function=HashEmbeddingFunction(dimensions=64),
    )
    store.upsert_chunks(
        [
            SimpleNamespace(
                chunk_id="lol-26.12-aatrox-0",
                document="[lol] patch 26.12 - Aatrox\n\n### Aatrox\n\n- Blade damage increased.",
                metadata={
                    "game": "lol",
                    "patch_version": "26.12",
                    "patch_date": "2026-06-09",
                    "section": "champion",
                    "target": "Aatrox",
                    "change_type": "buff",
                    "source_url": "https://example.com",
                    "title": "Patch 26.12",
                },
            )
        ]
    )

    result = ChatOrchestrator(store=store, llm_backend="openai").chat(
        game="lol",
        message="Aatrox changes",
        debug=True,
    )

    assert "OPENAI_API_KEY is required" in result.answer
    assert result.debug_trace is not None
    assert result.debug_trace["generation"] == "llm_configuration_error"
