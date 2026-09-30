#!/usr/bin/env python3
"""Rename fixed GBR analysis/playback sidecars to human-readable variant names."""
from __future__ import annotations

import argparse
from pathlib import Path

from common import resolve_showcase

LEGACY = {
    "gbr.audio.json": ".audio.json",
    "gbr.playback.json": ".playback.json",
}


def migrate_one(source: Path, suffix: str, dry_run: bool) -> tuple[str, str]:
    target = source.parent / f"{source.parent.name}{suffix}"
    if source == target:
        return "SKIP", str(source)

    if target.exists():
        try:
            same = source.read_bytes() == target.read_bytes()
        except OSError:
            same = False
        if same:
            if not dry_run:
                source.unlink()
            return "DUPLICATE", f"{source} -> {target}"
        return "CONFLICT", f"{source} -> {target}"

    if not dry_run:
        source.replace(target)
    return "RENAME", f"{source} -> {target}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--showcase")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    showcase = resolve_showcase(args.showcase)
    conflicts = 0
    renamed = duplicates = 0

    print("GBR SIDECAR RENAME")
    print(f"Showcase: {showcase}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'APPLY'}")

    for legacy_name, suffix in LEGACY.items():
        for source in sorted(showcase.rglob(legacy_name)):
            action, detail = migrate_one(source, suffix, args.dry_run)
            print(f"{action:9} {detail}")
            if action == "CONFLICT":
                conflicts += 1
            elif action == "RENAME":
                renamed += 1
            elif action == "DUPLICATE":
                duplicates += 1

    print(f"\nRenamed: {renamed}; duplicate legacy files removed: {duplicates}; conflicts: {conflicts}")
    return 1 if conflicts else 0


if __name__ == "__main__":
    raise SystemExit(main())
