from __future__ import annotations

import os


os.environ.setdefault("PATCHLOG_EMBEDDING_BACKEND", "hash")
os.environ.setdefault("PATCHLOG_LLM_BACKEND", "template")
