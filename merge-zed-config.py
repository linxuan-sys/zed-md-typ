#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_json(path: Path) -> Any:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def merge_tasks(target: Any, snippet: Any) -> Any:
    if target is None:
        target = {"tasks": []}
    if not isinstance(target, dict):
        raise ValueError("tasks.json must be a JSON object")

    target_tasks = target.setdefault("tasks", [])
    if not isinstance(target_tasks, list):
        raise ValueError("tasks.json field 'tasks' must be a list")

    new_tasks = snippet.get("tasks", []) if isinstance(snippet, dict) else []
    existing_labels = {task.get("label") for task in target_tasks if isinstance(task, dict)}
    for task in new_tasks:
        if isinstance(task, dict) and task.get("label") not in existing_labels:
            target_tasks.append(task)
            existing_labels.add(task.get("label"))
    return target


def merge_keymap(target: Any, snippet: Any) -> Any:
    if target is None:
        target = []
    if not isinstance(target, list):
        raise ValueError("keymap.json must be a JSON array")

    if not isinstance(snippet, list):
        return target

    seen = {
        json.dumps(item, sort_keys=True, ensure_ascii=False)
        for item in target
        if isinstance(item, dict)
    }
    for item in snippet:
        if not isinstance(item, dict):
            continue
        key = json.dumps(item, sort_keys=True, ensure_ascii=False)
        if key not in seen:
            target.append(item)
            seen.add(key)
    return target


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Merge Zed JSON config snippets")
    parser.add_argument("--type", choices=["tasks", "keymap"], required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--snippet", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    target_path = Path(args.target).expanduser()
    snippet_path = Path(args.snippet).expanduser()

    target = load_json(target_path)
    snippet = load_json(snippet_path)
    if snippet is None:
        raise FileNotFoundError(f"Snippet not found: {snippet_path}")

    if args.type == "tasks":
        merged = merge_tasks(target, snippet)
    else:
        merged = merge_keymap(target, snippet)

    target_path.parent.mkdir(parents=True, exist_ok=True)
    dump_json(target_path, merged)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
