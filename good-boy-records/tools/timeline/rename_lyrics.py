#!/usr/bin/env python3
"""Rename gbr.lyrics.json to <variant-folder>.lyrics.json without rewriting JSON."""
from __future__ import annotations
import argparse
from common import resolve_showcase

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--showcase")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    showcase = resolve_showcase(args.showcase)
    renamed = removed = conflicts = 0
    for source in sorted(showcase.rglob("gbr.lyrics.json")):
        if not source.is_file():
            continue
        target = source.with_name(source.parent.name + ".lyrics.json")
        src_rel, dst_rel = source.relative_to(showcase), target.relative_to(showcase)
        if target.exists():
            if source.read_bytes() == target.read_bytes():
                print(f"duplicate {src_rel} -> remove; canonical exists as {dst_rel}")
                if not args.dry_run:
                    source.unlink()
                removed += 1
            else:
                print(f"CONFLICT {src_rel}: target differs: {dst_rel}")
                conflicts += 1
            continue
        print(f"rename {src_rel} -> {dst_rel}")
        if not args.dry_run:
            source.replace(target)
        renamed += 1
    print(f"Renamed: {renamed}; identical aliases removed: {removed}; conflicts: {conflicts}")
    return 1 if conflicts else 0

if __name__ == "__main__":
    raise SystemExit(main())
