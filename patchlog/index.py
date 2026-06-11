from __future__ import annotations

import argparse
from pathlib import Path

from patchlog.chunking.lol import chunk_lol_processed_file
from patchlog.chunking.overwatch import chunk_overwatch_processed_file
from patchlog.chunking.valorant import chunk_valorant_processed_file
from patchlog.parsing.assets import extract_lol_entity_assets
from patchlog.store.chroma import ChromaPatchStore


SUPPORTED_GAMES = ("lol", "overwatch", "valorant")


def main() -> None:
    args = _parse_args()

    root = Path.cwd()
    processed_dir = root / "data" / "processed" / args.game
    store = ChromaPatchStore(persist_path=root / "data" / "chroma")

    chunks = []
    for meta_path in sorted(processed_dir.glob("*.meta.json")):
        markdown_path = meta_path.with_suffix("").with_suffix(".md")
        if not markdown_path.exists():
            print(f"skip {meta_path.name}: markdown file missing")
            continue
        chunks.extend(_chunk_processed_file(args.game, root, markdown_path, meta_path))

    if args.limit:
        chunks = chunks[: args.limit]

    store.delete_game(game=args.game)
    store.upsert_chunks(chunks)
    print(f"indexed {len(chunks)} chunks into data/chroma")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Index processed patch-note chunks")
    parser.add_argument("--game", choices=SUPPORTED_GAMES, required=True)
    parser.add_argument("--limit", type=int)
    return parser.parse_args()


def _chunk_processed_file(game: str, root: Path, markdown_path: Path, meta_path: Path):
    if game == "lol":
        raw_path = root / "data" / "raw" / "lol" / f"{markdown_path.stem}.html"
        asset_map = None
        if raw_path.exists():
            asset_map = extract_lol_entity_assets(raw_path.read_text(encoding="utf-8"))
        return chunk_lol_processed_file(markdown_path, meta_path, asset_map=asset_map)
    if game == "valorant":
        return chunk_valorant_processed_file(markdown_path, meta_path)
    if game == "overwatch":
        return chunk_overwatch_processed_file(markdown_path, meta_path)
    raise ValueError(f"Unsupported game: {game}")


if __name__ == "__main__":
    main()
