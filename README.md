# PatchLog

PatchLog is a game patch-note RAG dashboard and chatbot for League of Legends,
Valorant, and Overwatch. It collects Korean official patch notes, builds
game-scoped patch cards, retrieves relevant changes with semantic search, and
generates grounded answers with citations.

## Features

- Game-specific dashboard for LoL, Valorant, and Overwatch
- Separate chat history and retrieval scope per game
- Local semantic retrieval with `BAAI/bge-m3`
- Parent-child chunking: dashboard cards stay as parent chunks, retrieval uses
  smaller semantic child chunks
- OpenAI Responses API answer generation with patch citations
- Template/hash fallback modes for fast local tests

## Quick Start

Install dependencies:

```powershell
pip install -r requirements.txt
```

Set your OpenAI API key for generated answers:

```powershell
$env:OPENAI_API_KEY="your_api_key"
```

Collect recent patch notes:

```powershell
python -m patchlog.collect --game lol --limit 10
python -m patchlog.collect --game valorant --limit 10
python -m patchlog.collect --game overwatch --limit 10
```

Build the default BGE-M3 Chroma index:

```powershell
python -m patchlog.index --game lol
python -m patchlog.index --game valorant
python -m patchlog.index --game overwatch
```

The first BGE-M3 run downloads `BAAI/bge-m3` from Hugging Face. For a fast
fallback index, use:

```powershell
python -m patchlog.index --game lol --embedding hash
```

Run the API and Streamlit app in separate terminals:

```powershell
python -m uvicorn patchlog.api.main:app --reload
python -m streamlit run app/streamlit_app.py
```

Open the dashboard at `http://localhost:8501`.

## Configuration

Environment variables:

- `PATCHLOG_EMBEDDING_BACKEND=bge-m3 | hash`
  - Default: `bge-m3`
  - Chroma collections are separated as `patch_notes_bge_m3` and
    `patch_notes_hash`
- `PATCHLOG_LLM_BACKEND=openai | template`
  - Default: `openai`
  - `template` is intended for tests and offline smoke checks
- `PATCHLOG_LLM_MODEL`
  - Default: `gpt-5.5`
- `OPENAI_API_KEY`
  - Required when `PATCHLOG_LLM_BACKEND=openai`

## Data Flow

Collectors write UTF-8 files to:

- `data/raw/{game}/{patch_version}.html`
- `data/processed/{game}/{patch_version}.md`
- `data/processed/{game}/{patch_version}.meta.json`

The indexer reads `data/processed`, creates parent card chunks plus semantic
child chunks, and writes a generated local Chroma database to `data/chroma`.
The Chroma directory is ignored by git and can be rebuilt at any time.

Supported sources:

- LoL: `https://www.leagueoflegends.com/ko-kr/news/tags/patch-notes/`
- Valorant: `https://playvalorant.com/ko-kr/news/tags/patch-notes/`
- Overwatch: `https://overwatch.blizzard.com/ko-kr/news/patch-notes/`

## API

Useful endpoints:

- `GET /health`
- `GET /patches?game=lol`
- `POST /search`
- `POST /chat`

Example `/chat` request:

```json
{
  "game": "lol",
  "message": "신 짜오 하향 알려줘",
  "chat_history": [],
  "top_k": 3,
  "debug": true
}
```

The response keeps the stable UI wire shape:

- `answer`
- `sources`
- `navigation_target`
- `debug_trace`

When debug is enabled, `debug_trace` includes the embedding backend, LLM
backend, retrieved child chunk ids, and resolved parent ids.

## Testing

Tests force lightweight local fallbacks through `tests/conftest.py`:

- `PATCHLOG_EMBEDDING_BACKEND=hash`
- `PATCHLOG_LLM_BACKEND=template`

Run:

```powershell
python -m pytest
```

## Game-Scoped Chat

The selected game is always the authoritative retrieval scope. The chatbot does
not infer or switch games from the question text alone. This prevents same-name
targets from crossing games, such as Ashe in LoL and Ashe in Overwatch.

If a target does not exist in the selected game, PatchLog returns a not-found
answer instead of leaking results from another game.
