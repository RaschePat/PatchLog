from __future__ import annotations

from collections.abc import Iterable
from typing import Any


class BGEM3EmbeddingFunction:
    """Chroma-compatible dense embedding wrapper for BAAI/bge-m3."""

    def __init__(
        self,
        *,
        model_name: str = "BAAI/bge-m3",
        batch_size: int = 12,
        max_length: int = 2048,
        use_fp16: bool | None = None,
        model: Any | None = None,
    ) -> None:
        self.model_name = model_name
        self.batch_size = batch_size
        self.max_length = max_length
        self.use_fp16 = use_fp16
        self._model = model

    @staticmethod
    def name() -> str:
        return "patchlog_bge_m3"

    @staticmethod
    def is_legacy() -> bool:
        return False

    def get_config(self) -> dict[str, Any]:
        return {
            "model_name": self.model_name,
            "batch_size": self.batch_size,
            "max_length": self.max_length,
            "use_fp16": self.use_fp16,
        }

    def __call__(self, input: list[str]) -> list[list[float]]:  # Chroma protocol.
        return self.embed_texts(input)

    def embed_documents(self, input: Iterable[str]) -> list[list[float]]:
        return self.embed_texts(input)

    def embed_query(self, input: list[str]) -> list[list[float]]:
        return self.embed_texts(input)

    @staticmethod
    def supported_spaces() -> list[str]:
        return ["cosine"]

    @staticmethod
    def default_space() -> str:
        return "cosine"

    @classmethod
    def build_from_config(cls, config: dict[str, Any]) -> "BGEM3EmbeddingFunction":
        return cls(
            model_name=str(config.get("model_name", "BAAI/bge-m3")),
            batch_size=int(config.get("batch_size", 12)),
            max_length=int(config.get("max_length", 2048)),
            use_fp16=config.get("use_fp16"),
        )

    def validate_config_update(
        self,
        old_config: dict[str, Any],
        new_config: dict[str, Any],
    ) -> None:
        if old_config.get("model_name") != new_config.get("model_name"):
            raise ValueError("BGE-M3 model name cannot be changed in-place")

    def embed_texts(self, texts: Iterable[str]) -> list[list[float]]:
        values = list(texts)
        if not values:
            return []
        output = self._load_model().encode(
            values,
            batch_size=self.batch_size,
            max_length=self.max_length,
            return_dense=True,
            return_sparse=False,
            return_colbert_vecs=False,
        )
        dense_vecs = output["dense_vecs"] if isinstance(output, dict) else output
        return [_as_float_list(vector) for vector in dense_vecs]

    def _load_model(self):
        if self._model is not None:
            return self._model
        try:
            from FlagEmbedding import BGEM3FlagModel
        except ImportError as exc:  # pragma: no cover - environment dependent.
            raise RuntimeError(
                "FlagEmbedding is required for BGE-M3 embeddings. "
                "Run `python -m pip install -r requirements.txt`."
            ) from exc

        use_fp16 = self.use_fp16
        if use_fp16 is None:
            use_fp16 = _cuda_available()
        self._model = BGEM3FlagModel(self.model_name, use_fp16=bool(use_fp16))
        return self._model


def _cuda_available() -> bool:
    try:
        import torch
    except Exception:
        return False
    try:
        return bool(torch.cuda.is_available())
    except Exception:
        return False


def _as_float_list(vector: Any) -> list[float]:
    if hasattr(vector, "tolist"):
        vector = vector.tolist()
    return [float(value) for value in vector]
