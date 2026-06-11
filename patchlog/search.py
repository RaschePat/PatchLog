from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from patchlog.store.chroma import ChromaPatchStore


def main() -> None:
    args = _parse_args()
    where: dict[str, Any] = {"game": args.game}
    if args.target:
        where["target"] = args.target
    if args.change_type:
        where["change_type"] = args.change_type

    store = ChromaPatchStore(persist_path=Path.cwd() / "data" / "chroma")
    rows = store.search(query=args.query, where=where, top_k=args.top_k)
    if not rows:
        print("No results")
        return

    for index, row in enumerate(rows, start=1):
        metadata = row["metadata"]
        print(
            f"{index}. {metadata['target']} | patch {metadata['patch_version']} "
            f"({metadata['patch_date']}) | {metadata['change_type']} | "
            f"distance={row['distance']:.4f}"
        )
        preview = " ".join(row["document"].split())[:220]
        print(f"   {preview}")
        print(f"   {metadata['source_url']}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Search indexed patch-note chunks")
    parser.add_argument("query")
    parser.add_argument("--game", choices=["lol"], default="lol")
    parser.add_argument("--target")
    parser.add_argument(
        "--change-type",
        choices=["buff", "nerf", "rework", "adjust", "bugfix", "new"],
    )
    parser.add_argument("--top-k", type=int, default=8)
    return parser.parse_args()


if __name__ == "__main__":
    main()
