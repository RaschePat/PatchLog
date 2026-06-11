from __future__ import annotations

import argparse
from pathlib import Path

from patchlog.collectors.lol import LoLCollector
from patchlog.collectors.overwatch import OverwatchCollector
from patchlog.collectors.valorant import ValorantCollector


COLLECTORS = {
    "lol": LoLCollector,
    "overwatch": OverwatchCollector,
    "valorant": ValorantCollector,
}


def main() -> None:
    args = _parse_args()

    collector = COLLECTORS[args.game]()
    written = collector.collect(
        output_root=Path.cwd(),
        limit=args.limit,
        since=args.since,
        force=args.force,
    )
    print(f"wrote {len(written)} files")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect patch notes")
    parser.add_argument("--game", choices=sorted(COLLECTORS), required=True)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--since")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    if args.limit < 1:
        parser.error("--limit must be >= 1")
    return args


if __name__ == "__main__":
    main()
