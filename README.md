# PatchLog

Game patch-note reader and chatbot for League of Legends, Valorant, and
Overwatch. PatchLog collects Korean official patch notes, chunks balance changes
by target, indexes them locally, and shows them in a Streamlit dashboard with a
game-scoped AI assistant.

## Features

- Game-specific patch dashboard for LoL, Valorant, and Overwatch
- Separate chat history and retrieval scope per game
- Latest-patch intent handling for questions like "가장 최신 패치노트 보여줘"
- Target-aware search for champion, agent, hero, item, rune, weapon, map, and
  system changes
- Patch cards with icons, concise summaries, source links, and highlighted
  navigation from chat answers

## Quick Start

Install dependencies:

```powershell
pip install -r requirements.txt
```

Run tests:

```powershell
python -m pytest
```

Collect recent patch notes:

```powershell
python -m patchlog.collect --game lol --limit 10
python -m patchlog.collect --game valorant --limit 10
python -m patchlog.collect --game overwatch --limit 10
```

Build the local Chroma index:

```powershell
python -m patchlog.index --game lol
python -m patchlog.index --game valorant
python -m patchlog.index --game overwatch
```

Run the API and Streamlit app in separate terminals:

```powershell
python -m uvicorn patchlog.api.main:app --reload
python -m streamlit run app/streamlit_app.py
```

Open the dashboard at `http://localhost:8501`.

## Data Flow

Collectors write UTF-8 files to:

- `data/raw/{game}/{patch_version}.html`
- `data/processed/{game}/{patch_version}.md`
- `data/processed/{game}/{patch_version}.meta.json`

The indexer reads `data/processed` and writes a generated local Chroma database
to `data/chroma`. The Chroma directory is ignored by git because it can be
rebuilt at any time with `python -m patchlog.index`.

Supported sources:

- LoL: `https://www.leagueoflegends.com/ko-kr/news/tags/patch-notes/`
- Valorant: `https://playvalorant.com/ko-kr/news/tags/patch-notes/`
- Overwatch: `https://overwatch.blizzard.com/ko-kr/news/patch-notes/`

## API

Start the API:

```powershell
python -m uvicorn patchlog.api.main:app --reload
```

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
  "debug": false
}
```

## Game-Scoped Chat

The selected game is always the authoritative retrieval scope. The chatbot does
not infer or switch games from the question text alone. This prevents same-name
targets from crossing games, such as Ashe in LoL and Ashe in Overwatch.

If a target does not exist in the selected game, PatchLog returns a not-found
answer instead of leaking results from another game.
