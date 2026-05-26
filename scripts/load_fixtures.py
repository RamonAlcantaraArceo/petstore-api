"""Load a named fixture dataset into the in-memory or PostgreSQL store.

Usage
-----
Run without arguments to list available datasets::

    uv run python scripts/load_fixtures.py

Load a specific dataset (defaults to memory mode)::

    uv run python scripts/load_fixtures.py --dataset basic
    uv run python scripts/load_fixtures.py --dataset mixed_v1
    uv run python scripts/load_fixtures.py --dataset mixed_v2

Load into a local PostgreSQL instance::

    STORAGE_MODE=local DATABASE_URL=postgresql://... \\
        uv run python scripts/load_fixtures.py --dataset mixed_v1

The script can also be driven entirely by environment variables::

    SEED_DATASET=basic uv run python scripts/load_fixtures.py
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.config import Settings
from app.fixtures.datasets import DATASETS
from app.fixtures.loader import seed_from_settings


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Seed the Petstore API with a named fixture dataset.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=_dataset_summary(),
    )
    parser.add_argument(
        "--dataset",
        metavar="NAME",
        default=os.environ.get("SEED_DATASET", ""),
        help=(
            "Name of the fixture dataset to load "
            "(default: $SEED_DATASET env var or empty → list available datasets)."
        ),
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Print all available dataset names and descriptions, then exit.",
    )
    return parser


def _dataset_summary() -> str:
    lines = ["Available datasets:", ""]
    for name, ds in sorted(DATASETS.items()):
        lines.append(f"  {name:<12} {ds.description}")
    return "\n".join(lines)


async def main() -> None:
    """Entry point: parse arguments and seed the configured backend."""
    parser = _build_parser()
    args = parser.parse_args()

    if args.list:
        print(_dataset_summary())
        return

    if not args.dataset:
        print("No dataset specified.  Pass --dataset NAME or set SEED_DATASET.\n")
        print(_dataset_summary())
        sys.exit(1)

    # Override SEED_DATASET so that seed_from_settings picks it up.
    os.environ["SEED_DATASET"] = args.dataset

    storage_mode = os.environ.get("STORAGE_MODE", "memory")
    if storage_mode != "memory":
        from app.db.session import ensure_db_schema, init_db

        settings_for_db = Settings()
        init_db(settings_for_db)
        await ensure_db_schema()

    settings = Settings()
    await seed_from_settings(settings)
    print(f"✓ Dataset '{args.dataset}' loaded into {storage_mode!r} storage.")


if __name__ == "__main__":
    asyncio.run(main())
