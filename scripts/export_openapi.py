"""Export the FastAPI OpenAPI document deterministically."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from alon_ai.api.app import create_app


REPOSITORY_ROOT = Path(__file__).resolve().parent.parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output = (Path.cwd() / args.output).resolve()

    try:
        output.relative_to(REPOSITORY_ROOT)
    except ValueError as error:
        raise SystemExit("--output must be inside the repository") from error

    output.parent.mkdir(parents=True, exist_ok=True)
    document = json.dumps(create_app().openapi(), indent=2, sort_keys=True)
    output.write_text(f"{document}\n", encoding="utf-8")


if __name__ == "__main__":
    main()
