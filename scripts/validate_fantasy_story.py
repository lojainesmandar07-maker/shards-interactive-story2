#!/usr/bin/env python3
"""Validate fantasy story graph integrity.

Checks:
- No broken next_part_id links
- No cycles/loops
- No unreachable parts from start_part_id
- No non-ending part without choices
- Unique choice IDs per file
"""

from __future__ import annotations

import json
from pathlib import Path
import sys


PARTS_DIR = Path("content/worlds/fantasy/parts")


class ValidationError(Exception):
    pass


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def validate_file(path: Path) -> None:
    data = load_json(path)
    metadata = data["metadata"]
    start_part_id = metadata["start_part_id"]
    parts = data["parts"]

    by_id = {part["id"]: part for part in parts}
    if len(by_id) != len(parts):
        raise ValidationError(f"{path.name}: duplicate part IDs found")

    if start_part_id not in by_id:
        raise ValidationError(f"{path.name}: start_part_id '{start_part_id}' missing")

    graph: dict[str, list[str]] = {}
    seen_choice_ids: set[str] = set()

    for part in parts:
        part_id = part["id"]
        choices = part.get("choices", [])

        if not choices and "ending" not in part:
            raise ValidationError(
                f"{path.name}: non-ending part '{part_id}' has no choices"
            )

        next_ids: list[str] = []
        for choice in choices:
            choice_id = choice["id"]
            if choice_id in seen_choice_ids:
                raise ValidationError(f"{path.name}: duplicate choice ID '{choice_id}'")
            seen_choice_ids.add(choice_id)

            next_part_id = choice["next_part_id"]
            if next_part_id not in by_id:
                raise ValidationError(
                    f"{path.name}: broken link {part_id}/{choice_id} -> {next_part_id}"
                )
            next_ids.append(next_part_id)

        graph[part_id] = next_ids

    WHITE, GRAY, BLACK = 0, 1, 2
    colors = {node: WHITE for node in graph}
    stack: list[str] = []

    def dfs_cycle(node: str) -> None:
        colors[node] = GRAY
        stack.append(node)
        for nxt in graph[node]:
            color = colors[nxt]
            if color == WHITE:
                dfs_cycle(nxt)
            elif color == GRAY:
                cycle_path = stack[stack.index(nxt) :] + [nxt]
                pretty = " -> ".join(cycle_path)
                raise ValidationError(f"{path.name}: cycle detected ({pretty})")
        stack.pop()
        colors[node] = BLACK

    dfs_cycle(start_part_id)

    reachable: set[str] = set()

    def walk(node: str) -> None:
        if node in reachable:
            return
        reachable.add(node)
        for nxt in graph[node]:
            walk(nxt)

    walk(start_part_id)
    unreachable = sorted(set(graph) - reachable)
    if unreachable:
        raise ValidationError(
            f"{path.name}: unreachable part IDs: {', '.join(unreachable)}"
        )


def main() -> int:
    files = sorted(PARTS_DIR.glob("fantasy_*.json"))
    if not files:
        print("No fantasy story files found.", file=sys.stderr)
        return 1

    for file in files:
        validate_file(file)

    print(f"Validated {len(files)} fantasy story files successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
